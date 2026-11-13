from enum import Enum
from io import BytesIO

import pandas as pd
import pytest

import cco_service
from Concurrent import Concurrent
from cco_service import CCOService


class Mode(str, Enum):
    alpha = "alpha"
    lifecycle = "lifecycle"


class Scope(str, Enum):
    logwise = "logwise"
    tracewise = "tracewise"


def make_state_ready(service, mode="alpha", scope="logwise"):
    state = service.get_state(mode, scope)
    state.update(
        {
            "filog_base": pd.DataFrame(
                {
                    "case:concept:name": ["case1", "case1"],
                    "concept:name": ["A", "B"],
                    "po_successors": ["old", "old"],
                    "case:po_name": [99, 99],
                }
            ),
            "filog_wlc": pd.DataFrame({"dummy": [1]}),
            "vars": {("A", "B"): 1},
            "vars_wlc": {("A", "B"): 1},
            "caseid_dict": {("A", "B"): ["case1"]},
            "filog_detection": None,
            "keyword_c": "_complete",
            "keyword_s": "_start",
            "concurrencies": None,
            "po_log": "old-po-log",
            "povariants": ["old-po"],
        }
    )
    return state


def make_concurrent(*pairs):
    concurrent = Concurrent()
    for pair in pairs:
        concurrent.add_pair(*pair)
    return concurrent


def test_initial_state_contains_expected_mode_scope_combinations():
    service = CCOService()

    assert set(service.state.keys()) == {
        ("alpha", "logwise"),
        ("alpha", "tracewise"),
        ("lifecycle", "logwise"),
        ("lifecycle", "tracewise"),
    }

    for state in service.state.values():
        assert state["filog_base"] is None
        assert state["concurrencies"] is None
        assert state["po_log"] is None
        assert state["povariants"] is None


def test_state_key_accepts_enum_values():
    service = CCOService()

    assert service._state_key(Mode.alpha, Scope.logwise) == ("alpha", "logwise")


def test_get_state_creates_state_for_unknown_combination():
    service = CCOService()

    state = service.get_state("custom_mode", "custom_scope")

    assert ("custom_mode", "custom_scope") in service.state
    assert state["filog_base"] is None


def test_require_prepared_state_raises_before_prepare_log():
    service = CCOService()

    with pytest.raises(ValueError, match="prepare_log"):
        service._require_prepared_state("alpha", "logwise")


def test_prepare_log_reads_reduces_and_stores_state(monkeypatch):
    service = CCOService()

    filog_towrite = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1"],
            "concept:name": ["A", "B"],
        }
    )
    filog_wlc = pd.DataFrame({"wlc": [1]})
    vars_wlc = {("A", "B"): 1}
    caseid_dict = {("A", "B"): ["case1"]}

    reduced_log = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1"],
            "concept:name": ["A", "B"],
        }
    )

    calls = {}

    def fake_read_log(infile, mode, scope):
        calls["read_log"] = (infile, mode, scope)
        return filog_towrite, filog_wlc, vars_wlc, caseid_dict, "kc", "ks"

    def fake_get_variants(log, activity_key):
        calls["get_variants"] = (log, activity_key)
        return {("A", "B"): 1}

    def fake_reduce(log, mode, scope, vars, passed_vars_wlc, passed_caseid_dict):
        calls["reduce"] = (log, mode, scope, vars, passed_vars_wlc, passed_caseid_dict)
        return reduced_log, {"reduced": ["case1"]}

    monkeypatch.setattr(cco_service, "read_log", fake_read_log)
    monkeypatch.setattr(cco_service.pm4py, "get_variants", fake_get_variants)
    monkeypatch.setattr(cco_service, "reduce_log_seq_variants", fake_reduce)

    result = service.prepare_log("input.xes", "alpha", "logwise")
    state = service.get_state("alpha", "logwise")

    assert result is reduced_log
    assert calls["read_log"] == ("input.xes", "alpha", "logwise")
    assert calls["get_variants"] == (filog_towrite, "concept:name")
    assert calls["reduce"][0] is filog_towrite
    assert state["filog_base"] is reduced_log
    assert state["semantics"] is None
    assert state["filog_wlc"] is filog_wlc
    assert state["vars"] == {("A", "B"): 1}
    assert state["vars_wlc"] == vars_wlc
    assert state["caseid_dict"] == {"reduced": ["case1"]}
    assert state["keyword_c"] == "kc"
    assert state["keyword_s"] == "ks"
    assert state["concurrencies"] is None
    assert state["po_log"] is None
    assert state["povariants"] is None


def test_prepare_log_writes_upload_to_tempfile_and_removes_it(monkeypatch):
    service = CCOService()
    removed = []

    monkeypatch.setattr(
        cco_service,
        "read_log",
        lambda infile, mode, scope: (
            pd.DataFrame({"case:concept:name": ["case1"], "concept:name": ["A"]}),
            pd.DataFrame(),
            {("A",): 1},
            {("A",): ["case1"]},
            "kc",
            "ks",
        ),
    )
    monkeypatch.setattr(
        cco_service.pm4py,
        "get_variants",
        lambda log, activity_key: {("A",): 1},
    )
    monkeypatch.setattr(
        cco_service,
        "reduce_log_seq_variants",
        lambda log, mode, scope, vars, vars_wlc, caseid_dict: (log, caseid_dict),
    )
    monkeypatch.setattr(cco_service.os, "remove", lambda path: removed.append(path))

    uploaded = BytesIO(b"<log />")

    service.prepare_log(uploaded, "alpha", "logwise")

    assert len(removed) == 1
    assert removed[0].endswith(".xes")


def test_prepare_log_stores_semantics(monkeypatch):
    service = CCOService()
    log = pd.DataFrame(
        {
            "case:concept:name": ["case1"],
            "concept:name": ["A"],
        }
    )

    monkeypatch.setattr(
        cco_service,
        "read_log",
        lambda *args: (log, log, {}, {("A",): ["case1"]}, "kc", "ks"),
    )
    monkeypatch.setattr(
        cco_service.pm4py,
        "get_variants",
        lambda log, activity_key: {("A",): 1},
    )
    monkeypatch.setattr(
        cco_service,
        "reduce_log_seq_variants",
        lambda log, *args: (log, {("A",): ["case1"]}),
    )

    service.prepare_log("input.xes", "alpha", "logwise", "certain")

    assert service.get_state("alpha", "logwise")["semantics"] == "certain"


def test_set_semantics_updates_prepared_state_without_resetting_results():
    service = CCOService()
    state = make_state_ready(service, mode="same_hour", scope="tracewise")
    state["po_log"] = "existing-po-log"

    result = service.set_semantics("same_hour", "tracewise", "uncertain")

    assert result == "uncertain"
    assert state["semantics"] == "uncertain"
    assert state["po_log"] == "existing-po-log"


@pytest.mark.parametrize(
    "mode",
    ["same_hour", "same_minute", "same_second", "same_timestamp"],
)
def test_prepare_log_timestamp_tracewise_keeps_all_original_cases(monkeypatch, mode):
    service = CCOService()
    source_log = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1", "case2", "case2"],
            "concept:name": ["A", "B", "A", "B"],
            "time:timestamp": pd.to_datetime(
                [
                    "2026-10-23T14:01:00Z",
                    "2026-10-23T14:10:00Z",
                    "2026-10-23T15:01:00Z",
                    "2026-10-23T15:10:00Z",
                ],
                utc=True,
            ),
        }
    )
    monkeypatch.setattr(
        cco_service,
        "read_log",
        lambda *args: (source_log, source_log, {}, {("A", "B"): ["case1", "case2"]}, "kc", "ks"),
    )
    monkeypatch.setattr(
        cco_service.pm4py,
        "get_variants",
        lambda log, activity_key: {("A", "B"): 2},
    )
    monkeypatch.setattr(
        cco_service,
        "reduce_log_seq_variants",
        lambda *args: pytest.fail("timestamp modes must not reduce sequential variants"),
    )

    result = service.prepare_log("input.xes", mode, "tracewise")
    state = service.get_state(mode, "tracewise")

    assert result["case:concept:name"].tolist() == ["case1", "case1", "case2", "case2"]
    assert result["case:multiplicity"].tolist() == [1, 1, 1, 1]
    assert state["caseid_dict"] == {("A", "B"): ["case1", "case2"]}


@pytest.mark.parametrize(
    "mode",
    ["same_hour", "same_minute", "same_second", "same_timestamp"],
)
def test_prepare_log_timestamp_logwise_keeps_original_cases_for_detection(
    monkeypatch,
    mode,
):
    service = CCOService()
    source_log = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1", "case2", "case2"],
            "concept:name": ["A", "B", "A", "B"],
            "time:timestamp": pd.to_datetime(
                [
                    "2026-10-23T14:01:00Z",
                    "2026-10-23T14:59:00Z",
                    "2026-10-23T15:01:00Z",
                    "2026-10-23T15:59:00Z",
                ],
                utc=True,
            ),
        }
    )
    reduced_log = source_log.iloc[:2].copy()
    reduced_caseid_dict = {("A", "B"): ["case1"]}

    monkeypatch.setattr(
        cco_service,
        "read_log",
        lambda *args: (
            source_log,
            source_log,
            {},
            {("A", "B"): ["case1", "case2"]},
            "kc",
            "ks",
        ),
    )
    monkeypatch.setattr(
        cco_service.pm4py,
        "get_variants",
        lambda log, activity_key: {("A", "B"): 2},
    )
    monkeypatch.setattr(
        cco_service,
        "reduce_log_seq_variants",
        lambda *args: (reduced_log, reduced_caseid_dict),
    )

    result = service.prepare_log("input.xes", mode, "logwise")
    state = service.get_state(mode, "logwise")

    assert result is reduced_log
    assert state["filog_base"] is reduced_log
    assert state["filog_detection"] is source_log
    assert state["caseid_dict"] is reduced_caseid_dict


@pytest.mark.parametrize(
    "mode",
    ["same_hour", "same_minute", "same_second", "same_timestamp"],
)
def test_detect_concurrencies_timestamp_mode_stores_supports(monkeypatch, mode):
    service = CCOService()
    state = make_state_ready(service, mode=mode, scope="logwise")
    detection_log = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1"],
            "concept:name": ["A", "B"],
            "time:timestamp": pd.to_datetime(
                ["2026-10-23T14:01:00Z", "2026-10-23T14:59:00Z"],
                utc=True,
            ),
        }
    )
    state["filog_detection"] = detection_log
    detected = make_concurrent(("A", "B"))
    supports = {frozenset({"A", "B"}): 1}

    def fake_detect(received_mode, vars, vars_wlc, keyword_c, keyword_s, filog):
        assert received_mode == mode
        assert filog is detection_log
        return detected, supports

    monkeypatch.setattr(
        cco_service,
        "detect_logwise_concurrency_with_supports",
        fake_detect,
    )

    result = service.detect_concurrencies(mode, "logwise")

    assert result is detected
    assert state["concurrencies"] is detected
    assert state["concurrency_supports"] is supports
    assert state["concurrency_direction_counts"] is None


def test_detect_concurrencies_only_allows_logwise():
    service = CCOService()
    make_state_ready(service, mode="alpha", scope="tracewise")

    with pytest.raises(ValueError, match="Tracewise concurrencies"):
        service.detect_concurrencies("alpha", "tracewise")


def test_detect_concurrencies_stores_result_and_resets_po_results(monkeypatch):
    service = CCOService()
    state = make_state_ready(service)

    detected = make_concurrent(("A", "B"))

    def fake_detect(mode, vars, vars_wlc, keyword_c, keyword_s):
        assert mode == "alpha"
        assert vars == {("A", "B"): 1}
        assert vars_wlc == {("A", "B"): 1}
        assert keyword_c == "_complete"
        assert keyword_s == "_start"
        return detected

    monkeypatch.setattr(cco_service, "detect_logwise_concurrency", fake_detect)

    result = service.detect_concurrencies("alpha", "logwise")

    assert result is detected
    assert state["concurrencies"] is detected
    assert state["po_log"] is None
    assert state["povariants"] is None


def test_set_concurrencies_only_allows_logwise():
    service = CCOService()
    make_state_ready(service, mode="alpha", scope="tracewise")

    with pytest.raises(ValueError, match="only supported for logwise"):
        service.set_concurrencies("alpha", "tracewise", make_concurrent(("A", "B")))


def test_set_concurrencies_stores_result_and_resets_po_results():
    service = CCOService()
    state = make_state_ready(service)

    edited = make_concurrent(("A", "B"))

    result = service.set_concurrencies("alpha", "logwise", edited)

    assert result is edited
    assert state["concurrencies"] is edited
    assert state["po_log"] is None
    assert state["povariants"] is None


def test_compute_po_traces_logwise_requires_concurrencies():
    service = CCOService()
    make_state_ready(service)

    with pytest.raises(ValueError, match="Logwise concurrencies"):
        service.compute_po_traces("alpha", "logwise")


def test_compute_po_traces_logwise_uses_stored_concurrencies_and_drops_old_po_columns(monkeypatch):
    service = CCOService()
    state = make_state_ready(service)
    stored_concurrencies = make_concurrent(("A", "B"))
    state["concurrencies"] = stored_concurrencies

    generated_log = pd.DataFrame({"case:concept:name": ["case1"]})
    generated_povariants = ["po1"]

    def fake_generate(concurrent, working_log, vars, stats_only, caseid_dict):
        assert concurrent is stored_concurrencies
        assert "po_successors" not in working_log.columns
        assert "case:po_name" not in working_log.columns
        assert vars == {("A", "B"): 1}
        assert stats_only is False
        assert caseid_dict == {("A", "B"): ["case1"]}
        return generated_log, generated_povariants

    monkeypatch.setattr(cco_service, "generate_logwise_po_traces", fake_generate)

    filog_out, povariants = service.compute_po_traces(
        "alpha",
        "logwise",
        stats_only=False,
    )

    assert filog_out is generated_log
    assert povariants is generated_povariants
    assert state["po_log"] is generated_log
    assert state["povariants"] is generated_povariants


def test_compute_po_traces_logwise_uses_passed_concurrencies_over_state(monkeypatch):
    service = CCOService()
    state = make_state_ready(service)
    state["concurrencies"] = make_concurrent(("old", "old"))
    passed = make_concurrent(("A", "B"))

    def fake_generate(concurrent, working_log, vars, stats_only, caseid_dict):
        assert concurrent is passed
        return working_log, ["po"]

    monkeypatch.setattr(cco_service, "generate_logwise_po_traces", fake_generate)

    service.compute_po_traces(
        "alpha",
        "logwise",
        concurrencies=passed,
    )

    assert state["concurrencies"] is passed


def test_compute_po_traces_tracewise_dispatches_to_tracewise_generator(monkeypatch):
    service = CCOService()
    state = make_state_ready(service, mode="alpha", scope="tracewise")

    generated_log = pd.DataFrame({"case:concept:name": ["case1"]})
    generated_povariants = ["trace-po"]

    def fake_generate(
        working_log,
        mode,
        vars,
        vars_wlc,
        stats_only,
        caseid_dict,
        keyword_c,
        keyword_s,
    ):
        assert "po_successors" not in working_log.columns
        assert "case:po_name" not in working_log.columns
        assert mode == "alpha"
        assert vars == {("A", "B"): 1}
        assert vars_wlc == {("A", "B"): 1}
        assert stats_only is True
        assert caseid_dict == {("A", "B"): ["case1"]}
        assert keyword_c == "_complete"
        assert keyword_s == "_start"
        return generated_log, generated_povariants

    monkeypatch.setattr(cco_service, "generate_tracewise_po_traces", fake_generate)

    filog_out, povariants = service.compute_po_traces(
        "alpha",
        "tracewise",
        stats_only=True,
    )

    assert filog_out is generated_log
    assert povariants is generated_povariants
    assert state["po_log"] is generated_log
    assert state["povariants"] is generated_povariants


def test_compute_po_traces_same_hour_uses_existing_tracewise_generator(monkeypatch):
    service = CCOService()
    state = make_state_ready(service, mode="same_hour", scope="tracewise")
    generated_log = pd.DataFrame(
        {
            "case:concept:name": ["case1"],
            "case:po_name": [1],
            "case:multiplicity": [1],
        }
    )

    def fake_generate(
        working_log,
        mode,
        vars,
        vars_wlc,
        stats_only,
        caseid_dict,
        keyword_c,
        keyword_s,
    ):
        assert "po_successors" not in working_log.columns
        assert "case:po_name" not in working_log.columns
        assert mode == "same_hour"
        assert stats_only is True
        return generated_log, []

    monkeypatch.setattr(
        cco_service,
        "generate_tracewise_po_traces",
        fake_generate,
    )

    filog_out, povariants = service.compute_po_traces(
        "same_hour",
        "tracewise",
        stats_only=True,
    )

    assert filog_out is generated_log
    assert povariants == []
    assert state["po_log"] is generated_log
    assert state["povariants"] == []


def test_compute_po_traces_lifecycle_tracewise_strips_lifecycle_suffixes_from_povariants(monkeypatch):
    service = CCOService()
    state = make_state_ready(service, mode="lifecycle", scope="tracewise")
    state["keyword_c"] = "_COMPLETE"
    state["keyword_s"] = "_START"

    class FakePO:
        def __init__(self):
            self._nodes = {
                0: {"activity": "A_COMPLETE"},
                1: {"activity": "B_START"},
                2: {"activity": "C"},
            }

        @property
        def nodes(self):
            class NodeView:
                def __init__(self, nodes):
                    self._nodes = nodes

                def __call__(self, data=False):
                    if data:
                        return self._nodes.items()
                    return self._nodes.keys()

            return NodeView(self._nodes)

    po = FakePO()

    monkeypatch.setattr(
        cco_service,
        "generate_tracewise_po_traces",
        lambda *args, **kwargs: (pd.DataFrame({"case:concept:name": ["case1"]}), [po]),
    )

    _, povariants = service.compute_po_traces(
        "lifecycle",
        "tracewise",
        stats_only=False,
    )

    assert povariants[0]._nodes[0]["activity"] == "A"
    assert povariants[0]._nodes[1]["activity"] == "B"
    assert povariants[0]._nodes[2]["activity"] == "C"


def test_compute_po_traces_rejects_unknown_scope_after_preparation():
    service = CCOService()
    make_state_ready(service, mode="alpha", scope="custom")

    with pytest.raises(ValueError, match="Unknown scope"):
        service.compute_po_traces("alpha", "custom")


def test_postprocess_log_for_xes_export_sets_po_flags_and_replaces_empty_successors():
    service = CCOService()
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1"],
            "po_successors": [
                {"value": None, "children": [("0", 11)]},
                pd.NA,
            ],
        },
        index=pd.Index([10, 11], name="identity:id"),
    )

    result = service._postprocess_log_for_xes_export(log)

    assert "identity:id" in result.columns
    assert result["identity:id"].tolist() == [10, 11]
    assert result["is_part_of_po"].tolist() == [True, False]
    assert result.loc[0, "po_successors"] == {
        "value": None,
        "children": [("0", 11)],
    }
    assert result.loc[1, "po_successors"] == {"value": None, "children": []}


def test_postprocess_log_for_xes_export_drops_lifecycle_identifier_for_lifecycle_tracewise():
    service = CCOService()
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1"],
            "new:activity:identifier": ["A_START"],
            "po_successors": [{"value": None, "children": []}],
        }
    )

    result = service._postprocess_log_for_xes_export(
        log,
        mode="lifecycle",
        scope="tracewise",
    )

    assert "new:activity:identifier" not in result.columns


def test_postprocess_log_for_xes_export_keeps_lifecycle_identifier_for_other_scopes():
    service = CCOService()
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1"],
            "new:activity:identifier": ["A_START"],
            "po_successors": [{"value": None, "children": []}],
        }
    )

    result = service._postprocess_log_for_xes_export(
        log,
        mode="lifecycle",
        scope="logwise",
    )

    assert "new:activity:identifier" in result.columns


def test_write_xes_reduces_postprocesses_and_writes(monkeypatch):
    service = CCOService()
    calls = {}

    original_log = pd.DataFrame({"case:concept:name": ["case1"]})
    reduced_log = pd.DataFrame(
        {
            "case:concept:name": ["case1"],
            "new:activity:identifier": ["A_START"],
            "po_successors": [pd.NA],
        },
        index=pd.Index([42], name="identity:id"),
    )

    def fake_reduce(filog):
        calls["reduce_arg"] = filog
        return reduced_log

    def fake_write(filog, filepath):
        calls["write_arg"] = filog
        calls["filepath"] = filepath

    monkeypatch.setattr(cco_service, "reduce_log_po_variants", fake_reduce)
    monkeypatch.setattr(cco_service, "write_xes_and_drop_NaNs", fake_write)

    service.write_xes(
        original_log,
        "out.xes",
        mode="lifecycle",
        scope="tracewise",
    )

    written = calls["write_arg"]

    assert calls["reduce_arg"] is original_log
    assert calls["filepath"] == "out.xes"
    assert "new:activity:identifier" not in written.columns
    assert written["identity:id"].tolist() == [42]
    assert written["is_part_of_po"].tolist() == [False]
    assert written.loc[0, "po_successors"] == {"value": None, "children": []}
