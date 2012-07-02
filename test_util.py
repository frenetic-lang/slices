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
# /slices/test_util.py                                                         #
# Utilities for testing netcore and slices                                     #
################################################################################
import networkx as nx
import nxtopo
import slicing
import netcore as nc
from examples import policy_gen

def linear(*linear_nodes):
    """Linear graph on four nodes, slices from input."""
    topo = nxtopo.from_graph(nx.path_graph(4))
    topo.finalize()

    topos = [topo.subgraph(nodes) for nodes in linear_nodes]
    policies = [policy_gen.flood(t) for t in topos]
    return topo, policies

def linear_hosts(*linear_nodes):
    """Returns topo, [(slice, policy)]"""
    topo = nxtopo.from_graph(nx.path_graph(4))
    nodes = [set(ns) for ns in linear_nodes]
    for n in topo.nodes():
        h1 = 100 + n*10 + 1
        h2 = 100 + n*10 + 2
        topo.add_host(h1)
        topo.add_host(h2)
        topo.add_link(n, h1)
        topo.add_link(n, h2)
        for ns in nodes:
            if n in ns:
                ns.update([h1, h2])
    topo.finalize()

    edge_policies = []
    for ns in linear_nodes:
        predicates = {}
        for n in ns:
            h1 = 100 + n*10 + 1
            h2 = 100 + n*10 + 2
            h1_port = topo.node[h1]['port'][0]
            h2_port = topo.node[h2]['port'][0]
            predicates[h1_port] = nc.Top()
            predicates[h2_port] = nc.Top()
        edge_policies.append(predicates)

    topos = [topo.subgraph(ns) for ns in nodes]
    slices = [slicing.ident_map_slice(t, pol)
              for t, pol in zip(topos, edge_policies)]
    combined = zip(slices, [policy_gen.flood(t) for t in topos])
    return (topo, combined)

def linear_all_ports(*linear_nodes):
    """Linear graph on four nodes with reflexive forwarding."""
    topo = nxtopo.from_graph(nx.path_graph(4))
    topo.finalize()

    topos = [topo.subgraph(nodes) for nodes in linear_nodes]
    policies = [policy_gen.flood(t, all_ports=True) for t in topos]
    return topo, policies

k10_nodes = [
               (0, 1, 2, 3, 4),
               (1, 2, 3, 4, 5),
               (2, 3, 4, 5, 6),
               (3, 4, 5, 6, 7),
               (4, 5, 6, 7, 8),
               (5, 6, 7, 8, 9),
               (6, 7, 8, 9, 0),
               (7, 8, 9, 0, 1),
               (8, 9, 0, 1, 2),
               (9, 0, 1, 2, 3),
              ]

def k10():
    """K10 complete graph."""
    topo = nxtopo.from_graph(nx.complete_graph(10))
    topo.finalize()

    topos = [topo.subgraph(nodes) for nodes in k10_nodes]
    edge_policies = [{} for t in topos]
    slices = [slicing.ident_map_slice(t, pol)
              for t, pol in zip(topos, edge_policies)]
    combined = zip(slices, [policy_gen.flood(t) for t in topos])
    return (topo, combined)

k4_nodes = [
            (0, 1, 2),
            (1, 2, 3),
            (2, 3, 0),
            (3, 0, 1),
           ]

def k4():
    """K4 complete graph."""
    topo = nxtopo.from_graph(nx.complete_graph(4))
    topo.finalize()

    topos = [topo.subgraph(nodes) for nodes in k4_nodes]
    edge_policies = [{} for t in topos]
    slices = [slicing.ident_map_slice(t, pol)
              for t, pol in zip(topos, edge_policies)]
    combined = zip(slices, [policy_gen.flood(t) for t in topos])
    return (topo, combined)

def k4hosts():
    """K4 complete graph with two hosts on each node."""
    topo = nxtopo.from_graph(nx.complete_graph(4))
    nodes = [set(ns) for ns in k4_nodes]
    for n in topo.nodes():
        h1 = 100 + n*10 + 1
        h2 = 100 + n*10 + 2
        topo.add_host(h1)
        topo.add_host(h2)
        topo.add_link(n, h1)
        topo.add_link(n, h2)
        for ns in nodes:
            if n in ns:
                ns.update([h1, h2])
    topo.finalize()

    edge_policies = []
    for ns in k4_nodes:
        predicates = {}
        for n in ns:
            h1 = 100 + n*10 + 1
            h2 = 100 + n*10 + 2
            h1_port = topo.node[h1]['port'][0]
            h2_port = topo.node[h2]['port'][0]
            predicates[h1_port] = nc.Top()
            predicates[h2_port] = nc.Top()
        edge_policies.append(predicates)

    topos = [topo.subgraph(ns) for ns in nodes]

    slices = [slicing.ident_map_slice(t, pol)
              for t, pol in zip(topos, edge_policies)]
    combined = zip(slices, [policy_gen.flood(t) for t in topos])
    return (topo, combined)

if __name__ == '__main__':
    unittest.main()
