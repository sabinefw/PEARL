import pandas as pd
import pytest

from Concurrent import Concurrent
import cco_transformer


class FakeGraph:
    def __init__(self):
        self.graph = {}


def make_concurrent(*pairs):
    concurrent = Concurrent()
    for pair in pairs:
        concurrent.add_pair(*pair)
    return concurrent


def test_detect_logwise_concurrency_alpha_uses_shared_successorlist():
    variants = {
        ("A", "B"): 1,
        ("B", "A"): 1,
    }

    concurrent = cco_transformer.detect_logwise_concurrency(
        mode="alpha",
        vars=variants,
        vars_wlc={},
        keyword_c="unused",
        keyword_s="unused",
    )

    assert frozenset({"A", "B"}) in concurrent


def test_detect_logwise_concurrency_lifecycle_unions_finder_results(monkeypatch):
    calls = []

    class FakeLifecycleConcurrencyFinder:
        def __init__(self, variant, keyword_c, keyword_s):
            calls.append((variant, keyword_c, keyword_s))
            self.variant = variant

        def find(self):
            if self.variant == ("A_START", "B_COMPLETE"):
                return {"concurrencies": make_concurrent(("A", "B"))}
            return {"concurrencies": make_concurrent(("C", "D"))}

    monkeypatch.setattr(
        cco_transformer.cco_concurrency_finders,
        "LifecycleConcurrencyFinder",
        FakeLifecycleConcurrencyFinder,
    )

    concurrent = cco_transformer.detect_logwise_concurrency(
        mode="lifecycle",
        vars={},
        vars_wlc={
            ("A_START", "B_COMPLETE"): 1,
            ("C_START", "D_COMPLETE"): 1,
        },
        keyword_c="_COMPLETE",
        keyword_s="_START",
    )

    assert calls == [
        (("A_START", "B_COMPLETE"), "_COMPLETE", "_START"),
        (("C_START", "D_COMPLETE"), "_COMPLETE", "_START"),
    ]
    assert concurrent == {
        frozenset({"A", "B"}),
        frozenset({"C", "D"}),
    }


def test_detect_logwise_concurrency_rejects_unknown_mode():
    with pytest.raises(NotImplementedError):
        cco_transformer.detect_logwise_concurrency(
            mode="unknown",
            vars={},
            vars_wlc={},
            keyword_c="",
            keyword_s="",
        )


def test_generate_logwise_po_traces_writes_po_info_when_not_stats_only(monkeypatch):
    calls = []

    def fake_create(var, concurrent):
        calls.append(("create", var, concurrent))
        return {0: [1], 1: []}, [("A", "B")], FakeGraph()

    def fake_check(partialorder, po_id, pograph, povariants):
        pograph.graph["id"] = po_id
        povariants.append(pograph)
        return po_id, po_id + 1, False

    def fake_write(log, caseids, successors, po_name):
        calls.append(("write", list(caseids), successors, po_name))
        log = log.copy()
        log["written"] = True
        return log

    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "createPObyactivities_NxDiGraph",
        fake_create,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "check_for_po_isomorphs",
        fake_check,
    )
    monkeypatch.setattr(cco_transformer.cco_writers, "writePOinfo", fake_write)

    log = pd.DataFrame({"case:concept:name": ["case1", "case1"]})
    variants = {("A", "B"): 1}
    caseid_dict = {("A", "B"): ["case1"]}
    concurrent = make_concurrent(("A", "B"))

    filog_out, povariants = cco_transformer.generate_logwise_po_traces(
        concurrent,
        log,
        variants,
        stats_only=False,
        caseid_dict=caseid_dict,
    )

    assert filog_out["written"].tolist() == [True, True]
    assert len(povariants) == 1
    assert calls[0] == ("create", ("A", "B"), concurrent)
    assert calls[1] == ("write", ["case1"], {0: [1], 1: []}, 1)


def test_generate_logwise_po_traces_skips_write_when_stats_only(monkeypatch):
    write_called = False

    def fake_create(var, concurrent):
        return {0: []}, [], FakeGraph()

    def fake_check(partialorder, po_id, pograph, povariants):
        povariants.append(pograph)
        return po_id, po_id + 1, False

    def fake_write(*args, **kwargs):
        nonlocal write_called
        write_called = True

    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "createPObyactivities_NxDiGraph",
        fake_create,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "check_for_po_isomorphs",
        fake_check,
    )
    monkeypatch.setattr(cco_transformer.cco_writers, "writePOinfo", fake_write)

    log = pd.DataFrame({"case:concept:name": ["case1"]})

    filog_out, povariants = cco_transformer.generate_logwise_po_traces(
        make_concurrent(),
        log,
        {("A",): 1},
        stats_only=True,
        caseid_dict={("A",): ["case1"]},
    )

    assert filog_out is log
    assert len(povariants) == 1
    assert write_called is False


def test_export_concurrency_writes_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    concurrent = make_concurrent(("A", "B"))

    cco_transformer.export_concurrency(concurrent)

    exported = pd.read_csv(tmp_path / "concurrencies.csv")
    assert set(map(tuple, exported.to_records(index=False))) == {
        ("A", "B"),
        ("B", "A"),
    }


def test_generate_tracewise_po_traces_alpha_detects_per_variant_and_exports_when_not_stats_only(monkeypatch):
    calls = []

    def fake_find_alpha(var):
        calls.append(("find", var))
        return {}, make_concurrent((var[0], var[-1]))

    def fake_create(var, concurrent):
        calls.append(("create", var, concurrent))
        return {0: []}, [], FakeGraph()

    def fake_check(partialorder, po_id, pograph, povariants):
        pograph.graph["id"] = po_id
        povariants.append(pograph)
        return po_id, po_id + 1, False

    def fake_write(log, caseids, successors, po_name):
        calls.append(("write", list(caseids), po_name))
        return log

    def fake_export(concurrent):
        calls.append(("export", concurrent))

    monkeypatch.setattr(
        cco_transformer.cco_concurrency_finders,
        "findAlphaConcurrency",
        fake_find_alpha,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "createPObyactivities_NxDiGraph",
        fake_create,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "check_for_po_isomorphs",
        fake_check,
    )
    monkeypatch.setattr(cco_transformer.cco_writers, "writePOinfo", fake_write)
    monkeypatch.setattr(cco_transformer, "export_concurrency", fake_export)

    log = pd.DataFrame({"case:concept:name": ["case1", "case2"]})
    variants = {
        ("A", "B"): 1,
        ("C", "D"): 1,
    }
    caseid_dict = {
        ("A", "B"): ["case1"],
        ("C", "D"): ["case2"],
    }

    filog_out, povariants = cco_transformer.generate_tracewise_po_traces(
        log,
        mode="alpha",
        vars=variants,
        vars_wlc={},
        stats_only=False,
        caseid_dict=caseid_dict,
        keyword_c="unused",
        keyword_s="unused",
    )

    assert filog_out is log
    assert len(povariants) == 2
    assert ("find", ("A", "B")) in calls
    assert ("find", ("C", "D")) in calls
    assert any(call[0] == "export" for call in calls)


def test_generate_tracewise_po_traces_alpha_does_not_export_when_stats_only(monkeypatch):
    export_called = False

    def fake_find_alpha(var):
        return {}, make_concurrent(("A", "B"))

    def fake_create(var, concurrent):
        return {0: []}, [], FakeGraph()

    def fake_check(partialorder, po_id, pograph, povariants):
        povariants.append(pograph)
        return po_id, po_id + 1, False

    def fake_export(concurrent):
        nonlocal export_called
        export_called = True

    monkeypatch.setattr(
        cco_transformer.cco_concurrency_finders,
        "findAlphaConcurrency",
        fake_find_alpha,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "createPObyactivities_NxDiGraph",
        fake_create,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "check_for_po_isomorphs",
        fake_check,
    )
    monkeypatch.setattr(cco_transformer, "export_concurrency", fake_export)

    cco_transformer.generate_tracewise_po_traces(
        pd.DataFrame({"case:concept:name": ["case1"]}),
        mode="alpha",
        vars={("A", "B"): 1},
        vars_wlc={},
        stats_only=True,
        caseid_dict={("A", "B"): ["case1"]},
        keyword_c="unused",
        keyword_s="unused",
    )

    assert export_called is False


def test_generate_tracewise_po_traces_lifecycle_uses_position_based_po(monkeypatch):
    calls = []

    class FakeLifecycleConcurrencyFinder:
        def __init__(self, variant, keyword_c, keyword_s):
            calls.append(("finder", variant, keyword_c, keyword_s))

        def find(self):
            return {
                "concurrencies": make_concurrent(("A", "B")),
                "positional_concurrencies": make_concurrent((3, 1)),
                "positional_equivalences": {0: 3},
            }

    def fake_create_by_positions(var, pos_concurrent, equivalents):
        calls.append(("create_positions", var, pos_concurrent, equivalents))
        return {1: [], 3: []}, [], FakeGraph()

    def fake_check(partialorder, po_id, pograph, povariants):
        povariants.append(pograph)
        return po_id, po_id + 1, False

    def fake_write(log, caseids, successors, po_name):
        calls.append(("write", list(caseids), successors, po_name))
        return log

    monkeypatch.setattr(
        cco_transformer.cco_concurrency_finders,
        "LifecycleConcurrencyFinder",
        FakeLifecycleConcurrencyFinder,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "createPObypositions_NxDiGraph",
        fake_create_by_positions,
    )
    monkeypatch.setattr(
        cco_transformer.cco_partialorder_handlers,
        "check_for_po_isomorphs",
        fake_check,
    )
    monkeypatch.setattr(cco_transformer.cco_writers, "writePOinfo", fake_write)
    monkeypatch.setattr(cco_transformer, "export_concurrency", lambda concurrent: None)

    variant = ("A_START", "B_START", "B_COMPLETE", "A_COMPLETE")
    log = pd.DataFrame({"case:concept:name": ["case1"]})

    filog_out, povariants = cco_transformer.generate_tracewise_po_traces(
        log,
        mode="lifecycle",
        vars={},
        vars_wlc={variant: 1},
        stats_only=False,
        caseid_dict={variant: ["case1"]},
        keyword_c="_COMPLETE",
        keyword_s="_START",
    )

    assert filog_out is log
    assert len(povariants) == 1
    assert ("finder", variant, "_COMPLETE", "_START") in calls
    assert any(call[0] == "create_positions" for call in calls)
    assert any(call[0] == "write" for call in calls)


def test_generate_tracewise_po_traces_rejects_unknown_mode():
    with pytest.raises(NotImplementedError):
        cco_transformer.generate_tracewise_po_traces(
            pd.DataFrame(),
            mode="unknown",
            vars={},
            vars_wlc={},
            stats_only=True,
            caseid_dict={},
            keyword_c="",
            keyword_s="",
        )


def test_transform_logwise_exports_only_when_not_stats_only(monkeypatch):
    calls = []

    def fake_detect(mode, vars, vars_wlc, keyword_c, keyword_s):
        calls.append(("detect", mode))
        return make_concurrent(("A", "B"))

    def fake_export(concurrent):
        calls.append(("export", concurrent))

    def fake_generate(concurrent, filog_towrite, vars, stats_only, caseid_dict):
        calls.append(("generate", concurrent, stats_only))
        return filog_towrite, ["po"]

    monkeypatch.setattr(cco_transformer, "detect_logwise_concurrency", fake_detect)
    monkeypatch.setattr(cco_transformer, "export_concurrency", fake_export)
    monkeypatch.setattr(cco_transformer, "generate_logwise_po_traces", fake_generate)

    log = pd.DataFrame({"case:concept:name": ["case1"]})

    result_log, povariants = cco_transformer.transform(
        log,
        mode="alpha",
        scope="logwise",
        vars={("A", "B"): 1},
        vars_wlc={},
        stats_only=False,
        caseid_dict={("A", "B"): ["case1"]},
        keyword_c="",
        keyword_s="",
    )

    assert result_log is log
    assert povariants == ["po"]
    assert calls[0] == ("detect", "alpha")
    assert calls[1][0] == "export"
    assert calls[2][0] == "generate"


def test_transform_logwise_does_not_export_when_stats_only(monkeypatch):
    calls = []

    monkeypatch.setattr(
        cco_transformer,
        "detect_logwise_concurrency",
        lambda *args: make_concurrent(("A", "B")),
    )
    monkeypatch.setattr(
        cco_transformer,
        "export_concurrency",
        lambda concurrent: calls.append(("export", concurrent)),
    )
    monkeypatch.setattr(
        cco_transformer,
        "generate_logwise_po_traces",
        lambda concurrent, filog_towrite, vars, stats_only, caseid_dict: (
            filog_towrite,
            [],
        ),
    )

    cco_transformer.transform(
        pd.DataFrame(),
        mode="alpha",
        scope="logwise",
        vars={},
        vars_wlc={},
        stats_only=True,
        caseid_dict={},
        keyword_c="",
        keyword_s="",
    )

    assert calls == []


def test_transform_tracewise_dispatches_to_tracewise_generator(monkeypatch):
    log = pd.DataFrame({"case:concept:name": ["case1"]})

    def fake_generate_tracewise(
        filog_towrite,
        mode,
        vars,
        vars_wlc,
        stats_only,
        caseid_dict,
        keyword_c,
        keyword_s,
    ):
        assert filog_towrite is log
        assert mode == "alpha"
        assert stats_only is True
        return filog_towrite, ["tracewise-po"]

    monkeypatch.setattr(
        cco_transformer,
        "generate_tracewise_po_traces",
        fake_generate_tracewise,
    )

    result_log, povariants = cco_transformer.transform(
        log,
        mode="alpha",
        scope="tracewise",
        vars={},
        vars_wlc={},
        stats_only=True,
        caseid_dict={},
        keyword_c="",
        keyword_s="",
    )

    assert result_log is log
    assert povariants == ["tracewise-po"]


def test_transform_rejects_unknown_scope():
    with pytest.raises(NotImplementedError):
        cco_transformer.transform(
            pd.DataFrame(),
            mode="alpha",
            scope="unknown",
            vars={},
            vars_wlc={},
            stats_only=True,
            caseid_dict={},
            keyword_c="",
            keyword_s="",
        )
