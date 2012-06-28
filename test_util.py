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
from examples import policy_gen

def linear(*linear_nodes):
    """Linear graph on four nodes, slices overlap on middle 2 nodes."""
    topo = nxtopo.from_graph(nx.path_graph(4))
    topo.finalize()

    topos = [topo.subgraph(nodes) for nodes in linear_nodes]
    policies = [policy_gen.flood(t) for t in topos]
    return topo, policies

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

if __name__ == '__main__':
    unittest.main()
