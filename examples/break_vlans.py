"""Generate a topology that requires n vlans per-slice.

It is possible to construct a topology that requires n vlan tags if you can only
assign one per slice, but only requires two if you assign on a
per-edge-per-slice basis.

The algorithm:

Construct n slices.  Each slice i has n-1 nodes that it "owns":

n[i][0], ..., n[i][i-1], n[i][i+1], ..., n[i][n-1]

one for each of the other slices.

Construct an edge between n[i][j] and n[j][i] for each pair i, j where i != j.

Also add to each slice i all nodes n[j][i] for j != i.  Call these "foreign"
nodes.

This means that each edge n[i][j] - n[j][i] is shared by exactly two slices, and
that every slice shares exactly one edge with every other slice.  Thus, no slice
can share a color with any other slice, so we can arbitrary increase the
required number of tags needed if we only assign them to each slice.

However, if we can assign tags independently to each edge, then we only need two
on each edge, and we can re-use them, so two tags are sufficient to
differentiate the entire graph.

It doesn't matter how we connect the nodes in each slice, so here we don't
connect them at all.
"""
import nxtopo
from slicing import Slice
import util

def id_of_node(slice_num, node_num):
    return "_".join(['s', str(slice_num), str(node_num)])
def node_of_id(node_id):
    (s, slice_num, node_num) = node_id.split('_')
    return (slice_num, node_num)

def get_slices(n=256):
    p_topo = nxtopo.NXTopo()
    nodes = {}

    # add all the "owned" nodes
    for i in range(n):
        nodes[i] = set()
        for j in range(n):
            if i == j:
                next
            else:
                nodes[i].add(j)
                p_topo.add_switch(id_of_node(i, j))

    # add all the edges
    for i in range(n):
        for j in nodes[i]:
            p_topo.add_link(id_of_node(i, j), id_of_node(j, i))

    p_topo.finalize()

    # Construct the slices
    slices = set()
    for i in range(n):
        slice_nodes = set()
        # owned nodes
        slice_nodes.update([id_of_node(i, j) for j in nodes[i]])
        # foreign nodes
        slice_nodes.update([id_of_node(j, i) for j in nodes[i]])

        l_topo = p_topo.subgraph(slice_nodes)
        switch_map = util.id_map(slice_nodes)
        port_map = util.id_map(util.ports_of_topo(l_topo))
        predicate = util.build_external_predicate(l_topo)
        slices.add(Slice(l_topo, p_topo, switch_map, port_map, predicate))

    return p_topo, slices
