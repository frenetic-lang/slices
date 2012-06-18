#!/usr/bin/python
################################################################################
# The Frenetic Project                                                         #
# frenetic@frenetic-lang.org                                                   #
################################################################################
# Licensed to the Frenetic Project by one or more contributors. See the        #
# NOTICE file distributed with this work for additional information            #
# regarding copyright and ownership. The Frenetic Project licenses this        #
# file to you under the following license.                                     #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided the following conditions are met:       #
# - Redistributions of source code must retain the above copyright             #
#   notice, this list of conditions and the following disclaimer.              #
# - Redistributions in binary form must reproduce the above copyright          #
#   notice, this list of conditions and the following disclaimer in            #
#   the documentation or other materials provided with the distribution.       #
# - The names of the copyright holds and contributors may not be used to       #
#   endorse or promote products derived from this work without specific        #
#   prior written permission.                                                  #
#                                                                              #
# Unless required by applicable law or agreed to in writing, software          #
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT    #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the     #
# LICENSE file distributed with this work for specific language governing      #
# permissions and limitations under the License.                               #
################################################################################
# /slices/vlan.py                                                              #
# Tools to assign vlan tags to network slices                                  #
################################################################################
"""Tools to assign vlan tags to network slices."""

class VlanException(Exception):
    """Exception to represent failure to map to VLAN tags."""
    pass

def sequential(slices):
    """Assign vlans to slices assuming they all overlap, sequentially."""
    if len(slices) > 255:
        raise VlanException('More than 255 slices, cannot naively assign vlans')
    vlan = 1
    output = {}
    for slic in slices:
        output[slic] = vlan
        vlan += 1
    return output

def links(topo, sid):
    """Get a list of ((s,p), (s,p)) for all outgoing links from this switch."""
    switch = topo.node[sid]
    return [((sid, our_port), (them, their_port))
            for our_port, (them, their_port) in switch['port'].items()
            # If their_port == 0, they're an end host, not a switch.
            # We don't care about end hosts.
            if their_port != 0]

def edges_of_topo(topo, undirected=False):
    """Get all switch-switch edges in a topo, in links format."""
    # Need to dereference switch id to get full object
    lnks = []
    for switch in topo.switches():
        lnks.extend(links(topo, switch))
    if undirected:
        lnks_new = []
        for (source, sink) in lnks:
            if (sink, source) not in lnks_new:
                lnks_new.append((source, sink))
        return lnks_new
    else:
        return lnks

def map_edges(lnks, switch_map, port_map):
    """Map ((s, p), (s, p)) edges according to the two maps."""
    mapped = []
    for (s1, p1), (s2, p2) in lnks:
        # only include the port result from the port map, don't rely on the
        # switch recorded there
        mapped.append(((switch_map[s1], port_map[(s1, p1)][1]),
                       (switch_map[s2], port_map[(s2, p2)][1])))
    return mapped

# TODO(astory): deal with unidirectional ports.  This should really be done by
# just looking at incoming ports, but it gets a bit more complicated because now
# you have to assign vlans in a unified way to everything incident to that port
def edge_in(edge, slic):
    """Determine whether a slice uses a given physical edge"""
    slice_edges = set(map_edges(edges_of_topo(slic.l_topo),
                                          slic.node_map, slic.port_map))
    return edge in slice_edges

def share_edge(s1, s2):
    """Determine whether two slices share a physical edge."""
    # This is only correct if we have a guarantee that the topologies are sane,
    # and only give us real internal edges.
    s1_ls = set(map_edges(edges_of_topo(s1.l_topo), s1.node_map, s1.port_map))
    s2_ls = set(map_edges(edges_of_topo(s2.l_topo), s2.node_map, s2.port_map))
    return not s1_ls.isdisjoint(s2_ls)

def slice_optimal(slices):
    """Return the minimum per-slice vlan assignment."""
    # Import here because optimize has hard-to-install dependencies
    import optimize
    conflicts = []
    for i in range(0, len(slices)):
        for j in range(i+1, len(slices)):
            if share_edge(slices[i], slices[j]):
                conflicts.append((slices[i], slices[j]))
    solution = optimize.assign_vlans(slices, conflicts)
    if solution is not None:
        return solution
    else:
        raise VlanException('Could not assign vlan tags - too many slices')

def edge_optimal(topo, slices):
    """Return the minimum per-slice-per-edge vlan assignment."""
    edges = edges_of_topo(topo, undirected=True)
    edge_slices = {}
    for edge in edges:
        edge_slices[edge] = set()
        for slic in slices:
            if edge_in(edge, slic):
                edge_slices[edge].add(slic)
    edge_vlans = {}
    for (edge, slics) in edge_slices.items():
        edge_vlans[edge] = dict(zip(slics, range(1, len(slics) + 1)))
    return edge_vlans
