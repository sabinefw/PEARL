import networkx as nx

from Concurrent import Concurrent
from cco_partialorder_handlers import (
    check_for_po_isomorphs,
    convert_seq_to_digraph,
    createPObyactivities_NxDiGraph,
    createPObypositions_NxDiGraph,
    is_iso,
)


def test_convert_seq_to_digraph_creates_total_order_with_activity_labels():
    graph = convert_seq_to_digraph(("A", "B", "C"))

    assert list(graph.nodes()) == [0, 1, 2]
    assert graph.nodes[0]["activity"] == "A"
    assert graph.nodes[1]["activity"] == "B"
    assert graph.nodes[2]["activity"] == "C"
    assert list(graph.edges()) == [(0, 1), (1, 2)]


def test_create_po_by_activities_without_concurrency_keeps_total_order():
    concurrent = Concurrent()

    successors, porel, po = createPObyactivities_NxDiGraph(
        ("A", "B", "C"),
        concurrent,
    )

    assert successors == {
        0: [1],
        1: [2],
        2: [],
    }
    assert porel == [("A", "B"), ("B", "C")]
    assert set(po.edges()) == {(0, 1), (1, 2)}


def test_create_po_by_activities_removes_order_between_concurrent_activities():
    concurrent = Concurrent()
    concurrent.add_pair("A", "B")

    successors, porel, po = createPObyactivities_NxDiGraph(
        ("A", "B", "C"),
        concurrent,
    )

    assert successors == {
        0: [2],
        1: [2],
        2: [],
    }
    assert set(porel) == {("A", "C"), ("B", "C")}
    assert set(po.edges()) == {(0, 2), (1, 2)}


def test_create_po_by_activities_removes_all_matching_label_instances():
    concurrent = Concurrent()
    concurrent.add_pair("A", "B")

    successors, porel, po = createPObyactivities_NxDiGraph(
        ("A", "B", "A"),
        concurrent,
    )

    assert successors == {
        0: [],
        1: [],
        2: [],
    }
    assert porel == []
    assert set(po.edges()) == set()


def test_create_po_by_positions_without_concurrency_keeps_total_order_except_equivalent_nodes():
    pos_concurrent = Concurrent()
    equivalents = {0: 3}

    successors, porel, po = createPObypositions_NxDiGraph(
        ("A_start", "B_start", "B_complete", "A_complete"),
        pos_concurrent,
        equivalents,
    )

    assert 0 not in po.nodes()
    assert set(po.nodes()) == {1, 2, 3}
    assert successors == {
        1: [2],
        2: [3],
        3: [],
    }
    assert porel == [
        ("B_start", "B_complete"),
        ("B_complete", "A_complete"),
    ]


def test_create_po_by_positions_removes_positional_concurrency_edges():
    pos_concurrent = Concurrent()
    pos_concurrent.add_pair(3, 1)
    pos_concurrent.add_pair(3, 2)
    equivalents = {0: 3}

    successors, porel, po = createPObypositions_NxDiGraph(
        ("A_start", "B_start", "B_complete", "A_complete"),
        pos_concurrent,
        equivalents,
    )

    assert set(po.nodes()) == {1, 2, 3}
    assert successors == {
        1: [2],
        2: [],
        3: [],
    }
    assert porel == [("B_start", "B_complete")]
    assert set(po.edges()) == {(1, 2)}


def test_is_iso_matches_same_activity_labeled_graphs_with_different_node_ids():
    left = nx.DiGraph()
    left.add_node(0, activity="A")
    left.add_node(1, activity="B")
    left.add_edge(0, 1)

    right = nx.DiGraph()
    right.add_node(10, activity="A")
    right.add_node(11, activity="B")
    right.add_edge(10, 11)

    assert is_iso(left, right)


def test_is_iso_rejects_graphs_with_different_activity_labels():
    left = nx.DiGraph()
    left.add_node(0, activity="A")

    right = nx.DiGraph()
    right.add_node(0, activity="B")

    assert not is_iso(left, right)


def test_check_for_po_isomorphs_registers_first_variant():
    _, _, po = createPObyactivities_NxDiGraph(("A", "B"), Concurrent())
    povariants = []

    poname, next_po_id, timeout = check_for_po_isomorphs(
        partialorder=[("A", "B")],
        po_id=1,
        pograph=po,
        povariants=povariants,
    )

    assert poname == 1
    assert next_po_id == 2
    assert timeout is False
    assert len(povariants) == 1
    assert povariants[0].graph["id"] == 1


def test_check_for_po_isomorphs_reuses_existing_isomorphic_variant():
    _, _, existing_po = createPObyactivities_NxDiGraph(("A", "B"), Concurrent())
    existing_po.graph["id"] = 1
    povariants = [existing_po]

    _, _, new_po = createPObyactivities_NxDiGraph(("A", "B"), Concurrent())

    poname, next_po_id, timeout = check_for_po_isomorphs(
        partialorder=[("A", "B")],
        po_id=2,
        pograph=new_po,
        povariants=povariants,
    )

    assert poname == 1
    assert next_po_id == 2
    assert timeout is False
    assert len(povariants) == 1


def test_check_for_po_isomorphs_registers_non_isomorphic_variant():
    _, _, existing_po = createPObyactivities_NxDiGraph(("A", "B"), Concurrent())
    existing_po.graph["id"] = 1
    povariants = [existing_po]

    _, _, new_po = createPObyactivities_NxDiGraph(("A", "C"), Concurrent())

    poname, next_po_id, timeout = check_for_po_isomorphs(
        partialorder=[("A", "C")],
        po_id=2,
        pograph=new_po,
        povariants=povariants,
    )

    assert poname == 2
    assert next_po_id == 3
    assert timeout is False
    assert len(povariants) == 2
    assert povariants[1].graph["id"] == 2
