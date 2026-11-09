import os
import tempfile

import pm4py
import pandas as pd

from cco_preparators import (
    read_log,
    reduce_log_seq_variants,
    reduce_log_po_variants,
)
from cco_transformer import (
    detect_logwise_concurrency,
    detect_logwise_concurrency_with_supports,
    generate_logwise_po_traces,
    generate_tracewise_po_traces,
)
from cco_writers import write_xes_and_drop_NaNs


class CCOService:
    """Stateful service wrapper for the Streamlit workflow.

    The service keeps a separate workflow state for each mode/scope combination,
    so the frontend can switch between configurations without losing already
    prepared logs, detected concurrencies, or generated PO traces.
    """

    def __init__(self):
        self.state = {
            ("alpha", "logwise"): self._empty_state(),
            ("alpha", "tracewise"): self._empty_state(),
            ("lifecycle", "logwise"): self._empty_state(),
            ("lifecycle", "tracewise"): self._empty_state(),
        }

    def _empty_state(self):
        return {
            "filog_base": None,
            "filog_detection": None,
            "filog_wlc": None,
            "vars": None,
            "vars_wlc": None,
            "caseid_dict": None,
            "keyword_c": None,
            "keyword_s": None,
            "concurrencies": None,
            "concurrency_supports": None,
            "concurrency_direction_counts": None,
            "po_log": None,
            "povariants": None,
        }

    def _value(self, value):
        return value.value if hasattr(value, "value") else value

    def _state_key(self, mode, scope):
        return (self._value(mode), self._value(scope))

    def _get_state(self, mode, scope):
        key = self._state_key(mode, scope)
        if key not in self.state:
            self.state[key] = self._empty_state()
        return self.state[key]

    def _require_prepared_state(self, mode, scope):
        state = self._get_state(mode, scope)
        if state["filog_base"] is None:
            raise ValueError(
                "Log muss zuerst vorbereitet werden: prepare_log muss aufgerufen werden."
            )
        return state

    def _reset_results(self, state):
        state["po_log"] = None
        state["povariants"] = None

    def _strip_lifecycle_suffix(self, activity, keyword_c, keyword_s):
        if not isinstance(activity, str):
            return activity

        for keyword in (keyword_c, keyword_s):
            if keyword and activity.endswith(keyword):
                return activity.removesuffix(keyword)

        return activity

    def _strip_lifecycle_labels_from_povariants(self, povariants, keyword_c, keyword_s):
        for po in povariants:
            for _, node_data in po.nodes(data=True):
                if "activity" in node_data:
                    node_data["activity"] = self._strip_lifecycle_suffix(
                        node_data["activity"],
                        keyword_c,
                        keyword_s,
                    )
        return povariants

    def _attach_po_multiplicities(self, filog, povariants):
        required_columns = {
            "case:po_name",
            "case:concept:name",
            "case:multiplicity",
        }
        if filog is None or not required_columns.issubset(filog.columns):
            for po in povariants:
                po.graph["multiplicity"] = 0
            return povariants

        case_level = filog[
            ["case:po_name", "case:concept:name", "case:multiplicity"]
        ].drop_duplicates()
        multiplicities = (
            case_level.groupby("case:po_name")["case:multiplicity"].sum().to_dict()
        )

        for po in povariants:
            po.graph["multiplicity"] = int(multiplicities.get(po.graph.get("id"), 0))

        return povariants

    def _compute_alpha_concurrency_supports(self, variants, concurrencies):
        if not variants or concurrencies is None:
            return {}, {}

        concurrent_pairs = set(concurrencies)
        direction_counts = {}

        for variant, multiplicity in variants.items():
            weight = int(multiplicity) if multiplicity else 1
            for activity_a, activity_b in zip(variant, variant[1:]):
                pair = frozenset((activity_a, activity_b))
                if activity_a == activity_b or pair not in concurrent_pairs:
                    continue

                direction = (activity_a, activity_b)
                direction_counts[direction] = (
                    direction_counts.get(direction, 0) + weight
                )

        supports = {}
        for pair in concurrent_pairs:
            activity_a, activity_b = sorted(pair)
            supports[pair] = min(
                direction_counts.get((activity_a, activity_b), 0),
                direction_counts.get((activity_b, activity_a), 0),
            )

        return supports, direction_counts

    def _attach_tracewise_alpha_metadata(self, filog, povariants, variants, caseid_dict):
        if (
            filog is None
            or "case:po_name" not in filog.columns
            or "case:concept:name" not in filog.columns
        ):
            return povariants

        from Concurrent import Concurrent
        import cco_concurrency_finders

        po_by_id = {po.graph.get("id"): po for po in povariants}
        for po in povariants:
            po.graph["concurrencies"] = Concurrent()
            po.graph["source_variants"] = []

        for variant in variants.keys():
            caseids = caseid_dict.get(variant, [])
            if not caseids:
                continue

            trace = filog[filog["case:concept:name"] == caseids[0]]
            if trace.empty:
                continue

            po_names = trace["case:po_name"].dropna().unique()
            if len(po_names) == 0:
                continue

            po = po_by_id.get(po_names[0])
            if po is None:
                continue

            _, concurrencies = cco_concurrency_finders.findAlphaConcurrency(variant)
            po.graph["concurrencies"] = po.graph["concurrencies"].union(concurrencies)
            po.graph["source_variants"].append(tuple(variant))

        return povariants

    def _attach_tracewise_lifecycle_metadata(
        self,
        filog,
        povariants,
        variants_wlc,
        caseid_dict,
        keyword_c,
        keyword_s,
    ):
        if (
            filog is None
            or "case:po_name" not in filog.columns
            or "case:concept:name" not in filog.columns
        ):
            return povariants

        from Concurrent import Concurrent
        import cco_concurrency_finders

        po_by_id = {po.graph.get("id"): po for po in povariants}
        for po in povariants:
            po.graph["concurrencies"] = Concurrent()
            po.graph["source_variants"] = []

        for variant in variants_wlc.keys():
            caseids = caseid_dict.get(variant, [])
            if not caseids:
                continue

            trace = filog[filog["case:concept:name"] == caseids[0]]
            if trace.empty:
                continue

            po_names = trace["case:po_name"].dropna().unique()
            if len(po_names) == 0:
                continue

            po = po_by_id.get(po_names[0])
            if po is None:
                continue

            finder = cco_concurrency_finders.LifecycleConcurrencyFinder(
                variant,
                keyword_c,
                keyword_s,
            )
            concurrencies = finder.find()["concurrencies"]
            po.graph["concurrencies"] = po.graph["concurrencies"].union(
                concurrencies
            )
            po.graph["source_variants"].append(tuple(variant))

        return povariants

    def _write_upload_to_tempfile(self, infile):
        if not hasattr(infile, "read"):
            return infile, None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp_file:
            tmp_file.write(infile.read())
            return tmp_file.name, tmp_file.name

    def prepare_log(self, infile, mode, scope):
        """Read and prepare the uploaded XES log for one mode/scope combination.

        The frontend currently uses `keep = one_per_po_variant`, so the log is
        reduced to one representative per sequential variant immediately after
        reading. Final reduction to one representative per PO variant is delayed
        until export.
        """

        mode_value = self._value(mode)
        scope_value = self._value(scope)
        timestamp_modes = {
            "same_hour",
            "same_minute",
            "same_second",
            "same_timestamp",
        }
        infile_path, tmp_file_path = self._write_upload_to_tempfile(infile)

        try:
            (
                filog_towrite,
                filog_wlc,
                vars_wlc,
                caseid_dict,
                keyword_c,
                keyword_s,
            ) = read_log(infile_path, mode, scope)

            vars = pm4py.get_variants(filog_towrite, activity_key="concept:name")

            if mode_value in timestamp_modes and scope_value == "logwise":
                filog_detection = filog_towrite
            else:
                filog_detection = None

            if mode_value in timestamp_modes and scope_value == "tracewise":
                # Timestamp concurrency needs every original case. Each case
                # contributes one to its eventual PO-variant multiplicity.
                filog_base = filog_towrite.copy()
                filog_base["case:multiplicity"] = 1
            else:
                filog_base, caseid_dict = reduce_log_seq_variants(
                    filog_towrite,
                    mode,
                    scope,
                    vars,
                    vars_wlc,
                    caseid_dict,
                )

            state = self._get_state(mode, scope)
            state.update(
                {
                    "filog_base": filog_base,
                    "filog_detection": filog_detection,
                    "filog_wlc": filog_wlc,
                    "vars": vars,
                    "vars_wlc": vars_wlc,
                    "caseid_dict": caseid_dict,
                    "keyword_c": keyword_c,
                    "keyword_s": keyword_s,
                    "concurrencies": None,
                    "concurrency_supports": None,
                    "concurrency_direction_counts": None,
                    "po_log": None,
                    "povariants": None,
                }
            )

            return filog_base

        finally:
            if tmp_file_path is not None:
                os.remove(tmp_file_path)

    def detect_concurrencies(self, mode, scope):
        """Detect logwise concurrencies for the prepared log.

        Tracewise modes intentionally do not expose a separate detection step:
        their concurrency detection remains integrated in PO generation.
        """

        state = self._require_prepared_state(mode, scope)

        if self._value(scope) != "logwise":
            raise ValueError(
                "Tracewise concurrencies are detected during PO generation."
            )

        mode_value = self._value(mode)
        if mode_value == "lifecycle":
            concurrencies, lifecycle_supports = (
                detect_logwise_concurrency_with_supports(
                    mode,
                    state["vars"],
                    state["vars_wlc"],
                    state["keyword_c"],
                    state["keyword_s"],
                )
            )
        elif mode_value in (
            "same_hour",
            "same_minute",
            "same_second",
            "same_timestamp",
        ):
            concurrencies, timestamp_supports = (
                detect_logwise_concurrency_with_supports(
                    mode,
                    state["vars"],
                    state["vars_wlc"],
                    state["keyword_c"],
                    state["keyword_s"],
                    state["filog_detection"],
                )
            )
        else:
            concurrencies = detect_logwise_concurrency(
                mode,
                state["vars"],
                state["vars_wlc"],
                state["keyword_c"],
                state["keyword_s"],
            )

        state["concurrencies"] = concurrencies
        self._reset_results(state)
        if mode_value == "alpha":
            (
                state["concurrency_supports"],
                state["concurrency_direction_counts"],
            ) = self._compute_alpha_concurrency_supports(
                state["vars"],
                concurrencies,
            )
        elif mode_value == "lifecycle":
            state["concurrency_supports"] = lifecycle_supports
            state["concurrency_direction_counts"] = None
        elif mode_value in (
            "same_hour",
            "same_minute",
            "same_second",
            "same_timestamp",
        ):
            state["concurrency_supports"] = timestamp_supports
            state["concurrency_direction_counts"] = None
        else:
            state["concurrency_supports"] = None
            state["concurrency_direction_counts"] = None

        return concurrencies

    def set_concurrencies(self, mode, scope, concurrencies):
        """Store frontend-edited concurrencies and invalidate generated PO traces."""

        state = self._require_prepared_state(mode, scope)

        if self._value(scope) != "logwise":
            raise ValueError(
                "Edited concurrencies are only supported for logwise modes."
            )

        state["concurrencies"] = concurrencies
        self._reset_results(state)

        return concurrencies

    def compute_po_traces(self, mode, scope, stats_only=False, concurrencies=None):
        """Generate PO traces from the current prepared state.

        For logwise modes, concurrencies must already exist in state or be passed
        explicitly. For tracewise modes, concurrency detection remains integrated.
        """

        state = self._require_prepared_state(mode, scope)

        working_log = state["filog_base"].drop(
            columns=["po_successors", "case:po_name"],
            errors="ignore",
        )

        scope_value = self._value(scope)

        if scope_value == "logwise":
            selected_concurrencies = (
                concurrencies if concurrencies is not None else state["concurrencies"]
            )
            if selected_concurrencies is None:
                raise ValueError(
                    "Logwise concurrencies muessen zuerst berechnet oder uebergeben werden."
                )

            state["concurrencies"] = selected_concurrencies
            filog_out, povariants = generate_logwise_po_traces(
                selected_concurrencies,
                working_log,
                state["vars"],
                stats_only,
                state["caseid_dict"],
            )
        elif scope_value == "tracewise":
            filog_out, povariants = generate_tracewise_po_traces(
                working_log,
                mode,
                state["vars"],
                state["vars_wlc"],
                stats_only,
                state["caseid_dict"],
                state["keyword_c"],
                state["keyword_s"],
            )
            if self._value(mode) == "alpha":
                povariants = self._attach_tracewise_alpha_metadata(
                    filog_out,
                    povariants,
                    state["vars"],
                    state["caseid_dict"],
                )
            elif self._value(mode) == "lifecycle":
                povariants = self._attach_tracewise_lifecycle_metadata(
                    filog_out,
                    povariants,
                    state["vars_wlc"],
                    state["caseid_dict"],
                    state["keyword_c"],
                    state["keyword_s"],
                )
                povariants = self._strip_lifecycle_labels_from_povariants(
                    povariants,
                    state["keyword_c"],
                    state["keyword_s"],
                )

        else:
            raise ValueError(f"Unknown scope: {scope}")

        povariants = self._attach_po_multiplicities(filog_out, povariants)
        state["po_log"] = filog_out
        state["povariants"] = povariants

        return filog_out, povariants

    def get_state(self, mode, scope):
        """Return the stored state for frontend inspection."""

        return self._get_state(mode, scope)

    def _postprocess_log_for_xes_export(self, filog, mode=None, scope=None):
        filog_to_export = filog.copy()

        if self._value(mode) == "lifecycle" and self._value(scope) == "tracewise":
            filog_to_export = filog_to_export.drop(
                columns="new:activity:identifier",
                errors="ignore",
            )

        filog_to_export.reset_index(inplace=True)
        filog_to_export["is_part_of_po"] = pd.Series(dtype=bool)
        filog_to_export["is_part_of_po"] = filog_to_export["po_successors"].notna()
        filog_to_export["po_successors"] = filog_to_export["po_successors"].apply(
            lambda x: {"value": None, "children": []} if pd.isna(x) else x
        )

        return filog_to_export

    def write_xes(self, filog, filepath, mode=None, scope=None, po_variant_ids=None):
        """Write a generated PO log to XES.

        The final reduction to one representative per PO variant happens here,
        so interactive PO generation can be repeated without export-specific
        reduction changing the currently displayed PO result. When PO variant
        IDs are provided, only those variants are included in the export.
        """

        filog_to_export = filog.copy()
        if po_variant_ids is not None:
            filog_to_export = filog_to_export[
                filog_to_export["case:po_name"].isin(po_variant_ids)
            ].copy()

        filog_to_export = reduce_log_po_variants(filog_to_export)
        filog_to_export = self._postprocess_log_for_xes_export(
            filog_to_export,
            mode,
            scope,
        )
        write_xes_and_drop_NaNs(filog_to_export, filepath)
