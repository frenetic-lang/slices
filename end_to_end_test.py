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
# /slices/end_to_end_test.py                                                   #
# Test slice compiler correctness with the SAT solver                          #
################################################################################

from examples import topology_gen, policy_gen
import compile, sat, nxtopo, slicing
import networkx as nx
import netcore as nc
import unittest

def linear(*linear_nodes):
    """Linear graph on four nodes, slices overlap on middle 2 nodes."""
    topo = nxtopo.from_graph(nx.path_graph(4))
    topo.finalize()

    topos = [topo.subgraph(nodes) for nodes in linear_nodes]
    policies = [policy_gen.flood(t) for t in topos]
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
    import copy
    old_topo = copy.deepcopy(topo)

    topos = [topo.subgraph(nodes) for nodes in k10_nodes]
    edge_policies = [{} for t in topos]
    slices = [slicing.ident_map_slice(t, pol)
              for t, pol in zip(topos, edge_policies)]
    combined = zip(slices, [policy_gen.flood(t) for t in topos])
    return (topo, combined)

class TestSlicing(unittest.TestCase):
    def testBasicOverlap(self):
        topo, policies = linear((0, 1, 2), (1, 2, 3))
        result = sat.isolated(topo, policies[0], policies[1])
        self.assertFalse(result)

    def testBasicIso(self):
        topo, policies = linear((0, 1), (2, 3))
        result = sat.isolated(topo, policies[0], policies[1])
        self.assertTrue(result)
        topo, policies = linear((0, 1, 2), (2, 3))
        result = sat.isolated(topo, policies[0], policies[1])
        self.assertTrue(result)

    @unittest.skip("expensive")
    def testCompleteGraphPhysSep(self):
        topo, combined = k10()
        policies = [p for _, p in combined]

        for i in range(0, len(policies)):
            for j in range(len(policies)):
                print "testing %s with %s." % (k10_nodes[i], k10_nodes[j])
                result = sat.isolated(topo, policies[i], policies[j])
                if len(set(k10_nodes[i]).intersection(k10_nodes[j])) > 1:
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

    @unittest.skip("expensive")
    def testCompleteGraphCompile(self):
        topo, combined = k10()
        policies = [p for _, p in combined]

        compiled = compile.compile_slices(combined)
        for i in range(len(compiled)):
            for j in range(len(compiled)):
                print "testing compiled %s with %s." % (k10_nodes[i], k10_nodes[j])
                result = sat.isolated(topo, compiled[i], compiled[j])
                if i == j:
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
