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
# /slices/examples/policy_gen.py                                               #
# Tools to generate policies                                                   #
################################################################################
"""Tools to generate policies"""

from netcore import nary_policy_union, then
from netcore import Header, forward, inport, Top, Action
import networkx as nx

def flood(topo, all_ports=False):
    """Construct a policy that floods packets out each port on each switch.

    if all_ports is set, even forward back out the port it came in.
    """
    switches = topo.switches()
    policies = []
    for switch in switches:
        ports = set(topo.node[switch]['port'].keys())
        for port in ports:
            # Make a copy of ports without this one
            if all_ports:
                other_ports = ports
            else:
                other_ports = ports.difference([port])
            for other_port in other_ports:
                pol = inport(switch, port) |then| forward(switch, other_port)
                policies.append(pol)
    return nary_policy_union(policies).reduce()

def observe_all(label):
    """Construct a policy that observes all packets and emits label."""
    return Top() |then| Action(None, obs=set(label))

next_label = 0
def flood_observe(topo, label=None, all_ports=False):
    """Construct a policy that floods packets and observes at the leaves.

    Sequentially assigns labels if none is set.  Not thread-safe.
    """
    if label is None:
        global next_label
        label = next_label
        next_label += 1
    switches = topo.switches()
    policies = []
    for switch in switches:
        ports = set(topo.node[switch]['port'].keys())
        for port in ports:
            # Make a copy of ports without this one
            if all_ports:
                other_ports = ports
            else:
                other_ports = ports.difference([port])
            for other_port in other_ports:
                pol = inport(switch, port) |then|\
                      Action(switch, ports=[other_port], obs=[label])
                policies.append(pol)
    return nary_policy_union(policies).reduce()

def all_pairs_shortest_path(topo, hosts_only=False):
    """Construct all-pairs-shortest-path routing policy.

    Constructs an all-pairs shortest path routing policy for topo, using each
    switch or host id number as the source and destination mac address.

    Only make paths to hosts if hosts_only

    RETURNS: a policy that implements all-pairs shortest path
    """
    forwarding_trees = []
    for source in (topo.hosts() if hosts_only else topo.nodes()):
        # For each node, build the shortest paths to that node
        # We 'start' at the node because networkx forces us to.
        paths = nx.shortest_path(topo, source=source)
        # Build next-hop table
        next_hops = {}
        for dest, path in paths.items():
            # path is a list, starting at source and ending at dest.
            if dest is not source and topo.node[dest]['isSwitch']:
                next_hops[dest] = path[-2]
        policies = []
        for node, next_node in next_hops.items():
            out_port = topo.node[node]['ports'][next_node]
            policies.append(Header({'switch': node})
                            |then| forward(node, out_port))
        forwarding_trees.append(nary_policy_union(policies)
                                % Header({'dstmac': source}))
    return nary_policy_union(forwarding_trees)

def multicast(topo, multicast_field='dstmac', multicast_value=0):
    """Construct a policy that multicasts packets to all nodes along the MST.

    Uses multicast_field:multicast_value to recognize multicast packets to send
    along the minimum spanning tree.
    """
    mst = nx.minimum_spanning_tree(topo)
    edges = set(mst.edges())
    for (n1, n2) in list(edges):
        edges.add((n2, n1))
    policies = []
    for node in topo.switches():
        ports = set()
        for switch, port in topo.node[node]['ports'].items():
            # If this link is in the MST
            if (node, switch) in edges:
                ports.add(port)
        for port in ports:
            others = ports.difference([port])
            policies.append(inport(node, port) |then| Action(node, others))
    return (nary_policy_union(policies)
            % Header({multicast_field: multicast_value}))
