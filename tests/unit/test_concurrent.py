import pytest

from Concurrent import Concurrent


def test_add_pair_stores_unordered_pair_as_frozenset():
    concurrent = Concurrent()

    concurrent.add_pair("A", "B")

    assert frozenset({"A", "B"}) in concurrent


def test_add_rejects_non_frozenset_elements():
    concurrent = Concurrent()

    with pytest.raises(ValueError):
        concurrent.add(("A", "B"))


def test_to_tuples_returns_both_orders_for_two_distinct_items():
    concurrent = Concurrent()
    concurrent.add_pair("A", "B")

    assert set(concurrent.to_tuples()) == {
        ("A", "B"),
        ("B", "A"),
    }


def test_to_tuples_returns_self_tuple_for_self_concurrency():
    concurrent = Concurrent()
    concurrent.add_pair("A", "A")

    assert set(concurrent.to_tuples()) == {
        ("A", "A"),
    }


def test_to_tuples_returns_all_permutations_for_pairs():
    concurrent = Concurrent()
    concurrent.add_pair("A", "B")
    concurrent.add_pair("C", "D")

    assert set(concurrent.to_tuples()) == {
        ("A", "B"),
        ("B", "A"),
        ("C", "D"),
        ("D", "C"),
    }


def test_union_returns_concurrent_instance():
    left = Concurrent()
    left.add_pair("A", "B")

    right = Concurrent()
    right.add_pair("C", "D")

    result = left.union(right)

    assert isinstance(result, Concurrent)
    assert result == {
        frozenset({"A", "B"}),
        frozenset({"C", "D"}),
    }


def test_difference_returns_concurrent_instance():
    concurrent = Concurrent()
    concurrent.add_pair("A", "B")
    concurrent.add_pair("C", "D")

    other = Concurrent()
    other.add_pair("A", "B")

    result = concurrent.difference(other)

    assert isinstance(result, Concurrent)
    assert result == {
        frozenset({"C", "D"}),
    }


def test_constructor_can_wrap_existing_set_and_remains_concurrent():
    concurrent = Concurrent({frozenset({"A", "B"})})

    assert isinstance(concurrent, Concurrent)
    assert set(concurrent.to_tuples()) == {
        ("A", "B"),
        ("B", "A"),
    }
