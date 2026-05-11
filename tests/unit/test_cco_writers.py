import pandas as pd

import cco_writers


def test_generate_pm4py_list_converts_iterable_to_pm4py_list_dict():
    result = cco_writers.generate_pm4py_list(["a", "b", "c"])

    assert result == {
        "value": None,
        "children": [
            ("0", "a"),
            ("1", "b"),
            ("2", "c"),
        ],
    }


def test_generate_pm4py_list_accepts_numpy_like_iterables():
    result = cco_writers.generate_pm4py_list([10, 11])

    assert result == {
        "value": None,
        "children": [
            ("0", 10),
            ("1", 11),
        ],
    }


def test_keep_one_representative_and_multiplicity_keeps_first_case_and_discards_rest():
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1", "c2", "c2", "c3"],
            "concept:name": ["A", "B", "A", "B", "C"],
        }
    )
    caseids = ["c1", "c2"]

    result = cco_writers.keepOneRepresentativeAndMultiplicity(
        log,
        caseids,
        m=7,
    )

    assert set(result["case:concept:name"]) == {"c1", "c3"}
    assert result.loc[result["case:concept:name"] == "c1", "case:multiplicity"].unique().tolist() == [7]
    assert caseids == ["c2"]


def test_keep_one_representative_sets_zero_multiplicity_to_one():
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1"],
            "concept:name": ["A", "B"],
        }
    )

    result = cco_writers.keepOneRepresentativeAndMultiplicity(
        log,
        ["c1"],
        m=0,
    )

    assert result["case:multiplicity"].unique().tolist() == [1]


def test_ordered_activities_returns_activities_sorted_by_timestamp():
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1", "c2"],
            "concept:name": ["B", "A", "C"],
            "time:timestamp": pd.to_datetime(
                ["2024-01-01 10:01", "2024-01-01 10:00", "2024-01-01 10:02"]
            ),
        }
    )

    assert cco_writers.ordered_activities("c1", log) == ("A", "B")


def test_write_po_info_adds_po_columns_when_missing():
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1", "c1"],
            "concept:name": ["A", "B", "C"],
        },
        index=[10, 11, 12],
    )

    result = cco_writers.writePOinfo(
        log,
        caseids_variant=["c1"],
        succ={0: [1, 2], 1: [2], 2: []},
        po_name=5,
    )

    assert "po_successors" in result.columns
    assert "case:po_name" in result.columns
    assert result.loc[10, "case:po_name"] == 5
    assert result.loc[11, "case:po_name"] == 5
    assert result.loc[12, "case:po_name"] == 5
    assert result.loc[10, "po_successors"] == {
        "value": None,
        "children": [
            ("0", 11),
            ("1", 12),
        ],
    }
    assert result.loc[11, "po_successors"] == {
        "value": None,
        "children": [
            ("0", 12),
        ],
    }
    assert result.loc[12, "po_successors"] == {
        "value": None,
        "children": [],
    }


def test_write_po_info_writes_multiple_cases_with_case_specific_offsets():
    log = pd.DataFrame(
        {
            "case:concept:name": ["c1", "c1", "c2", "c2"],
            "concept:name": ["A", "B", "A", "B"],
        },
        index=[0, 1, 10, 11],
    )

    result = cco_writers.writePOinfo(
        log,
        caseids_variant=["c1", "c2"],
        succ={0: [1], 1: []},
        po_name=3,
    )

    assert result.loc[0, "po_successors"] == {
        "value": None,
        "children": [("0", 1)],
    }
    assert result.loc[1, "po_successors"] == {
        "value": None,
        "children": [],
    }
    assert result.loc[10, "po_successors"] == {
        "value": None,
        "children": [("0", 11)],
    }
    assert result.loc[11, "po_successors"] == {
        "value": None,
        "children": [],
    }
    assert result["case:po_name"].dropna().unique().tolist() == [3]


def test_write_xes_and_drop_nans_uses_pm4py_converter_and_writer(monkeypatch):
    calls = {}

    class FakeVariants:
        TO_EVENT_LOG = "to_event_log"

    class FakeConverter:
        Variants = FakeVariants

        @staticmethod
        def apply(df, variant, parameters):
            calls["converter_df"] = df
            calls["variant"] = variant
            calls["parameters"] = parameters
            return "converted-log"

    def fake_write_xes(log, output_file):
        calls["written_log"] = log
        calls["output_file"] = output_file

    monkeypatch.setattr(cco_writers, "log_converter", FakeConverter)
    monkeypatch.setattr(cco_writers.pm4py, "write_xes", fake_write_xes)

    df = pd.DataFrame({"a": [1]})

    cco_writers.write_xes_and_drop_NaNs(df, "out.xes")

    assert calls["converter_df"] is df
    assert calls["variant"] == "to_event_log"
    assert calls["parameters"] == {"stream_postprocessing": True}
    assert calls["written_log"] == "converted-log"
    assert calls["output_file"] == "out.xes"
