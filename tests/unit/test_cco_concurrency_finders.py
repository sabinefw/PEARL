import pytest

from Concurrent import Concurrent
from cco_concurrency_finders import (
    LifecycleConcurrencyFinder,
    findAlphaConcurrency,
)


def test_alpha_finds_no_concurrency_for_single_ordered_variant():
    successorlist, concurrencies = findAlphaConcurrency(("A", "B", "C"))

    assert successorlist == {
        "A": ["B"],
        "B": ["C"],
    }
    assert len(concurrencies) == 0


def test_alpha_finds_concurrency_across_variants_with_shared_successorlist():
    successorlist = {}
    concurrencies = Concurrent()

    successorlist, concurrencies = findAlphaConcurrency(
        ("A", "B"),
        successorlist,
        concurrencies,
    )
    successorlist, concurrencies = findAlphaConcurrency(
        ("B", "A"),
        successorlist,
        concurrencies,
    )

    assert frozenset({"A", "B"}) in concurrencies
    assert set(concurrencies.to_tuples()) == {
        ("A", "B"),
        ("B", "A"),
    }


def test_alpha_ignores_direct_self_successor_as_concurrency():
    _, concurrencies = findAlphaConcurrency(("A", "A"))

    assert len(concurrencies) == 0


def test_alpha_reuses_successorlist_without_duplicating_successors():
    successorlist = {}

    successorlist, _ = findAlphaConcurrency(("A", "B"), successorlist)
    successorlist, _ = findAlphaConcurrency(("A", "B"), successorlist)

    assert successorlist == {"A": ["B"]}


def test_lifecycle_get_base_name_removes_configured_suffixes():
    finder = LifecycleConcurrencyFinder(
        variants=(),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    assert finder._get_base_name("A_start") == "A"
    assert finder._get_base_name("A_complete") == "A"


def test_lifecycle_get_base_name_rejects_activity_without_lifecycle_suffix():
    finder = LifecycleConcurrencyFinder(
        variants=(),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    with pytest.raises(ValueError):
        finder._get_base_name("A")


def test_lifecycle_finds_activity_level_concurrency_for_overlapping_interval():
    finder = LifecycleConcurrencyFinder(
        variants=("A_start", "B_start", "B_complete", "A_complete"),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    result = finder.find()

    assert frozenset({"A", "B"}) in result["concurrencies"]
    assert set(result["concurrencies"].to_tuples()) == {
        ("A", "B"),
        ("B", "A"),
    }


def test_lifecycle_records_start_complete_equivalences():
    finder = LifecycleConcurrencyFinder(
        variants=("A_start", "B_start", "B_complete", "A_complete"),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    result = finder.find()

    assert result["positional_equivalences"] == {
        0: 3,
        1: 2,
    }


def test_lifecycle_records_positional_concurrency_to_complete_event():
    finder = LifecycleConcurrencyFinder(
        variants=("A_start", "B_start", "B_complete", "A_complete"),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    result = finder.find()

    assert frozenset({3, 1}) in result["positional_concurrencies"]
    assert frozenset({3, 2}) in result["positional_concurrencies"]


def test_lifecycle_start_without_matching_complete_creates_no_concurrency():
    finder = LifecycleConcurrencyFinder(
        variants=("A_start", "B_start", "B_complete"),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    result = finder.find()

    assert len(result["concurrencies"]) == 0
    assert len(result["positional_concurrencies"]) == 0
    assert result["positional_equivalences"] == {
        1: 2,
    }


def test_lifecycle_without_start_events_returns_empty_result():
    finder = LifecycleConcurrencyFinder(
        variants=("A_complete", "B_complete"),
        keyword_complete="_complete",
        keyword_start="_start",
    )

    result = finder.find()

    assert len(result["concurrencies"]) == 0
    assert len(result["positional_concurrencies"]) == 0
    assert result["positional_equivalences"] == {}
