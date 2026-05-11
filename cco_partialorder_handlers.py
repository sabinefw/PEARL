import networkx as nx
import networkx.algorithms.isomorphism as iso

from Concurrent import Concurrent


def convert_seq_to_digraph(var):
    """converts sequential trace to nxDiGraph with positions and activity name labels"""

    seq = nx.DiGraph()
    nlist = []
    elist = []
    for i in range(len(var)):  # make nodes
        name = {"activity": var[i]}
        nlist.append((i, name))
    for i in range(len(var) - 1):  # total order
        elist.append((i, i + 1))
    seq.add_nodes_from(nlist)
    seq.add_edges_from(elist)
    return seq


def createPObyactivities_NxDiGraph(var, concurrent: Concurrent):
    """Transforms 'sequential' nxDiGraph to partially ordered nxDiGraph using name (label) based concurrency information."""

    potracesuccessor = {}
    porel = []

    seq = convert_seq_to_digraph(var)
    tc = nx.transitive_closure_dag(seq)

    rlist = []

    for c1, c2 in concurrent.to_tuples():
        nodes1 = [x for x, y in tc.nodes(data=True) if y["activity"] == c1]
        nodes2 = [x for x, y in tc.nodes(data=True) if y["activity"] == c2]
        for n1 in nodes1:
            for n2 in nodes2:
                rlist.append((n1, n2))
                rlist.append((n2, n1))

    tc.remove_edges_from(rlist)

    po = nx.transitive_reduction(tc)
    po.add_nodes_from(tc.nodes(data=True))

    for node in po.nodes:
        potracesuccessor[node] = list(po.successors(node))

    for u, v in po.edges:
        porel.append((po.nodes[u]["activity"], po.nodes[v]["activity"]))

    #print(var)
    #print(potracesuccessor)
    #print(porel)

    return potracesuccessor, porel, po


def createPObypositions_NxDiGraph(var, pos_concurrent: Concurrent, equivalents):
    """Transforms 'sequential' nxDiGraph to partially ordered nxDiGraph using position (activity instance/event) based concurrency information,
    considering equivalent (start/complete) events."""

    potracenachfolger = {}
    porel = []

    seq = convert_seq_to_digraph(var)
    tc = nx.transitive_closure_dag(seq)
    tc.remove_edges_from(pos_concurrent.to_tuples())

    for k in equivalents:  # remove "duplicate" nodes and arcs
        tc.remove_node(k)

    po = nx.transitive_reduction(tc)
    po.add_nodes_from(tc.nodes(data=True))

    for node in po.nodes:
        potracenachfolger[node] = list(po.successors(node))

    for u, v in po.edges:
        porel.append((po.nodes[u]["activity"], po.nodes[v]["activity"]))

    #print(var)
    #print(potracenachfolger)
    #print(porel)

    return potracenachfolger, porel, po


def is_iso(p1, p2):
    nm = iso.categorical_node_match("activity", "")
    return nx.is_isomorphic(p1, p2, nm)


def check_for_po_isomorphs(partialorder, po_id, pograph, povariants):
    """Checks partially ordered nxDiGraph variants for isomorphy."""

    timeout = False

    if len(povariants) == 0:
        pograph.graph["id"] = po_id
        po_id += 1
        povariants.extend([pograph])

    for one_po_variant in povariants:
        result = nx.vf2pp_is_isomorphic(one_po_variant, pograph, node_label="activity")
        if result:
            poname_towrite = one_po_variant.graph["id"]
            break

    else:
        pograph.graph["id"] = po_id
        poname_towrite = po_id
        po_id += 1
        povariants.extend([pograph])

    return poname_towrite, po_id, timeout
