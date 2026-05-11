import pandas as pd
import pytest

import cco_preparators


def make_basic_log():
    return pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1", "case2", "case2"],
            "concept:name": ["A", "B", "A", "C"],
        }
    )


def make_lifecycle_log():
    return pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1", "case1", "case1"],
            "concept:name": ["A", "B", "B", "A"],
            "lifecycle:transition": ["START", "START", "COMPLETE", "COMPLETE"],
        }
    )


def fake_split_by_process_variant(log, activity_key="concept:name"):
    result = []
    for case_id, trace in log.groupby("case:concept:name", sort=False):
        variant = tuple(trace[activity_key])
        result.append((variant, trace))
    return result


def fake_get_variants(log, activity_key="concept:name"):
    variants = {}
    for _, trace in log.groupby("case:concept:name", sort=False):
        variant = tuple(trace[activity_key])
        variants[variant] = variants.get(variant, 0) + 1
    return variants


def fake_filter_event_attribute_values(log, key, values, level, retain):
    return log[log[key].isin(values)].copy()


def test_preprocess_lifecycle_filters_start_and_complete_and_adds_identifier(monkeypatch):
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "filter_event_attribute_values",
        fake_filter_event_attribute_values,
    )

    log = make_lifecycle_log()

    filog_wlc, keyword_c, keyword_s = cco_preparators.preprocess_lifecycle(log)

    assert keyword_c == "_COMPLETE"
    assert keyword_s == "_START"
    assert list(filog_wlc["new:activity:identifier"]) == [
        "A_START",
        "B_START",
        "B_COMPLETE",
        "A_COMPLETE",
    ]


def test_preprocess_lifecycle_detects_lowercase_keywords(monkeypatch):
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "filter_event_attribute_values",
        fake_filter_event_attribute_values,
    )

    log = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1"],
            "concept:name": ["A", "A"],
            "lifecycle:transition": ["start", "complete"],
        }
    )

    _, keyword_c, keyword_s = cco_preparators.preprocess_lifecycle(log)

    assert keyword_c == "_complete"
    assert keyword_s == "_start"


def test_preprocess_lifecycle_detects_titlecase_keywords(monkeypatch):
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "filter_event_attribute_values",
        fake_filter_event_attribute_values,
    )

    log = pd.DataFrame(
        {
            "case:concept:name": ["case1", "case1"],
            "concept:name": ["A", "A"],
            "lifecycle:transition": ["Start", "Complete"],
        }
    )

    _, keyword_c, keyword_s = cco_preparators.preprocess_lifecycle(log)

    assert keyword_c == "_Complete"
    assert keyword_s == "_Start"


def test_read_log_alpha_without_lifecycle_prepares_identity_index(monkeypatch):
    log = make_basic_log()

    monkeypatch.setattr(cco_preparators.pm4py, "read_xes", lambda _: log)
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "split_by_process_variant",
        fake_split_by_process_variant,
    )
    monkeypatch.setattr(cco_preparators.pm4py, "get_variants", fake_get_variants)

    filog_towrite, filog_wlc, vars_wlc, caseid_dict, keyword_c, keyword_s = (
        cco_preparators.read_log("dummy.xes", mode="alpha", scope="logwise")
    )

    assert filog_towrite.index.name == "identity:id"
    assert list(filog_towrite.index) == [0, 1, 2, 3]
    assert filog_wlc is filog_towrite
    assert vars_wlc == {
        ("A", "B"): 1,
        ("A", "C"): 1,
    }
    assert caseid_dict == {
        ("A", "B"): ["case1"],
        ("A", "C"): ["case2"],
    }
    assert keyword_c == "default_c"
    assert keyword_s == "default_s"


def test_read_log_lifecycle_without_lifecycle_column_raises(monkeypatch):
    monkeypatch.setattr(cco_preparators.pm4py, "read_xes", lambda _: make_basic_log())

    with pytest.raises(ValueError, match="missing lifecycle information"):
        cco_preparators.read_log(
            "dummy.xes",
            mode="lifecycle",
            scope="logwise",
        )


def test_read_log_lifecycle_logwise_filters_complete_for_output_and_keeps_wlc_variants(monkeypatch):
    log = make_lifecycle_log()

    monkeypatch.setattr(cco_preparators.pm4py, "read_xes", lambda _: log)
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "filter_event_attribute_values",
        fake_filter_event_attribute_values,
    )
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "split_by_process_variant",
        fake_split_by_process_variant,
    )
    monkeypatch.setattr(cco_preparators.pm4py, "get_variants", fake_get_variants)

    filog_towrite, filog_wlc, vars_wlc, caseid_dict, keyword_c, keyword_s = (
        cco_preparators.read_log("dummy.xes", mode="lifecycle", scope="logwise")
    )

    assert list(filog_towrite["lifecycle:transition"]) == ["COMPLETE", "COMPLETE"]
    assert "new:activity:identifier" in filog_wlc.columns
    assert vars_wlc == {
        ("A_START", "B_START", "B_COMPLETE", "A_COMPLETE"): 1,
    }
    assert caseid_dict == {
        ("B", "A"): ["case1"],
    }
    assert keyword_c == "_COMPLETE"
    assert keyword_s == "_START"


def test_read_log_lifecycle_tracewise_uses_lifecycle_log_for_output_and_caseids(monkeypatch):
    log = make_lifecycle_log()

    monkeypatch.setattr(cco_preparators.pm4py, "read_xes", lambda _: log)
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "filter_event_attribute_values",
        fake_filter_event_attribute_values,
    )
    monkeypatch.setattr(
        cco_preparators.pm4py,
        "split_by_process_variant",
        fake_split_by_process_variant,
    )
    monkeypatch.setattr(cco_preparators.pm4py, "get_variants", fake_get_variants)

    filog_towrite, filog_wlc, vars_wlc, caseid_dict, _, _ = (
        cco_preparators.read_log("dummy.xes", mode="lifecycle", scope="tracewise")
    )

    assert filog_towrite.index.name == "identity:id"
    assert "new:activity:identifier" in filog_towrite.columns
    assert filog_towrite.equals(filog_wlc)
    assert vars_wlc == {
        ("A_START", "B_START", "B_COMPLETE", "A_COMPLETE"): 1,
    }
    assert caseid_dict == {
        ("A_START", "B_START", "B_COMPLETE", "A_COMPLETE"): ["case1"],
    }


def test_reduce_log_seq_variants_keeps_one_case_per_variant(monkeypatch):
    calls = []

    def fake_keep_one(log, caseids, multiplicity):
        calls.append((list(caseids), multiplicity))
        representative = caseids[0]
        discard = caseids[1:]
        caseids.pop(0)
        return log[~log["case:concept:name"].isin(discard)].copy()

    monkeypatch.setattr(
        cco_preparators.cco_writers,
        "keepOneRepresentativeAndMultiplicity",
        fake_keep_one,
    )

    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1", "c2", "c2", "c3", "c3"],
            "concept:name": ["A", "B", "A", "B", "A", "C"],
        }
    )
    variants = {
        ("A", "B"): 2,
        ("A", "C"): 1,
    }
    caseid_dict = {
        ("A", "B"): ["c1", "c2"],
        ("A", "C"): ["c3"],
    }

    reduced_log, reduced_caseid_dict = cco_preparators.reduce_log_seq_variants(
        log,
        mode="alpha",
        scope="logwise",
        vars=variants,
        vars_wlc={},
        caseid_dict=caseid_dict,
    )

    assert set(reduced_log["case:concept:name"]) == {"c1", "c3"}
    assert reduced_caseid_dict == {
        ("A", "B"): ["c1"],
        ("A", "C"): ["c3"],
    }
    assert calls == [
        (["c1", "c2"], 2),
        (["c3"], 1),
    ]


def test_reduce_log_seq_variants_uses_vars_wlc_for_lifecycle_tracewise(monkeypatch):
    calls = []

    def fake_keep_one(log, caseids, multiplicity):
        calls.append((list(caseids), multiplicity))
        caseids.pop(0)
        return log

    monkeypatch.setattr(
        cco_preparators.cco_writers,
        "keepOneRepresentativeAndMultiplicity",
        fake_keep_one,
    )

    log = pd.DataFrame({"case:concept:name": ["c1"]})
    vars_wlc = {("A_START", "A_COMPLETE"): 3}
    caseid_dict = {("A_START", "A_COMPLETE"): ["c1"]}

    _, reduced_caseid_dict = cco_preparators.reduce_log_seq_variants(
        log,
        mode="lifecycle",
        scope="tracewise",
        vars={("A",): 1},
        vars_wlc=vars_wlc,
        caseid_dict=caseid_dict,
    )

    assert reduced_caseid_dict == {("A_START", "A_COMPLETE"): ["c1"]}
    assert calls == [(["c1"], 3)]


def test_reduce_log_po_variants_sums_multiplicities_per_po_variant(monkeypatch):
    calls = []

    def fake_keep_one(log, caseids, multiplicity):
        calls.append((list(caseids), multiplicity))
        representative = caseids[0]
        discard = caseids[1:]
        caseids.pop(0)
        kept = log[~log["case:concept:name"].isin(discard)].copy()
        kept.loc[kept["case:concept:name"] == representative, "case:multiplicity"] = multiplicity
        return kept

    monkeypatch.setattr(
        cco_preparators.cco_writers,
        "keepOneRepresentativeAndMultiplicity",
        fake_keep_one,
    )

    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c2", "c3"],
            "case:po_name": [1, 1, 2],
            "case:multiplicity": [2, 3, 5],
        }
    )

    reduced_log = cco_preparators.reduce_log_po_variants(log)

    assert set(reduced_log["case:concept:name"]) == {"c1", "c3"}
    assert calls == [
        (["c1", "c2"], 5),
        (["c3"], 5),
    ]
