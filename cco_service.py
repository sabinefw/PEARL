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
            "filog_wlc": None,
            "vars": None,
            "vars_wlc": None,
            "caseid_dict": None,
            "keyword_c": None,
            "keyword_s": None,
            "concurrencies": None,
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
                    "filog_wlc": filog_wlc,
                    "vars": vars,
                    "vars_wlc": vars_wlc,
                    "caseid_dict": caseid_dict,
                    "keyword_c": keyword_c,
                    "keyword_s": keyword_s,
                    "concurrencies": None,
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

        concurrencies = detect_logwise_concurrency(
            mode,
            state["vars"],
            state["vars_wlc"],
            state["keyword_c"],
            state["keyword_s"],
        )

        state["concurrencies"] = concurrencies
        self._reset_results(state)

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
            if self._value(mode) == "lifecycle":
                povariants = self._strip_lifecycle_labels_from_povariants(
                    povariants,
                    state["keyword_c"],
                    state["keyword_s"],
                )

        else:
            raise ValueError(f"Unknown scope: {scope}")

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

    def write_xes(self, filog, filepath, mode=None, scope=None):
        """Write a generated PO log to XES.

        The final reduction to one representative per PO variant happens here,
        so interactive PO generation can be repeated without export-specific
        reduction changing the currently displayed PO result.
        """

        filog_to_export = reduce_log_po_variants(filog)
        filog_to_export = self._postprocess_log_for_xes_export(
            filog_to_export,
            mode,
            scope,
        )
        write_xes_and_drop_NaNs(filog_to_export, filepath)
