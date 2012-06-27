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
"""Test slice compiler with SAT solver.

There are some tests in this file that take 30 or so minutes to run.  They are
diabled unless the EXPENSIVE_TESTS enviroment variable is set.

    `export EXPENSIVE_TESTS=1`

to set it, and

    `unset EXPENSIVE_TESTS`

to unset it.
"""

from examples import topology_gen, policy_gen
import sat, nxtopo, slicing
import compile as cp
import edge_compile as ec
import networkx as nx
import netcore as nc
import os
import unittest

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

class TestVerify(unittest.TestCase):
    def testBasicOverlap(self):
        topo, policies = linear((0, 1, 2), (1, 2, 3))
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))

    def testBasicIso(self):
        topo, policies = linear((0, 1), (2, 3))
        self.assertTrue(sat.isolated(topo, policies[0], policies[1]))
        topo, policies = linear((0, 1, 2), (2, 3))
        self.assertTrue(sat.isolated(topo, policies[0], policies[1]))

    def testForwarding(self):
        topo, policies = linear((0, 1), (2, 3))
        self.assertIsNone(sat.forwards(policies[0]))
        self.assertIsNone(sat.forwards(policies[1]))
        topo, policies = linear((0, 1, 2), (1, 2, 3))
        self.assertIsNotNone(sat.forwards(policies[0]))
        self.assertIsNotNone(sat.forwards(policies[1]))
        topo, policies = linear_all_ports((0, 1), (2, 3))
        self.assertIsNotNone(sat.forwards(policies[0]))
        self.assertIsNotNone(sat.forwards(policies[1]))

class TestCompile(unittest.TestCase):
    def testBasicCompile(self):
        topo, policies = linear((0, 1, 2, 3), (0, 1, 2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = cp.compile_slices(combined)
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertIsNotNone(sat.forwards(policies[0]))
        self.assertIsNotNone(sat.forwards(policies[1]))
        self.assertIsNotNone(sat.forwards(compiled[0]))
        self.assertIsNotNone(sat.forwards(compiled[1]))

class TestEdgeCompile(unittest.TestCase):
    def testBasicCompile(self):
        topo, policies = linear((0, 1, 2, 3), (0, 1, 2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertIsNotNone(sat.forwards(policies[0]))
        self.assertIsNotNone(sat.forwards(policies[1]))
        self.assertIsNotNone(sat.forwards(compiled[0]))
        self.assertIsNotNone(sat.forwards(compiled[1]))

        topo, policies = linear((0, 1, 2), (1, 2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertIsNotNone(sat.forwards(policies[0]))
        self.assertIsNotNone(sat.forwards(policies[1]))
        self.assertIsNotNone(sat.forwards(compiled[0]))
        self.assertIsNotNone(sat.forwards(compiled[1]))

        topo, policies = linear((0, 1), (2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertTrue(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertIsNone(sat.forwards(policies[0]))
        self.assertIsNone(sat.forwards(policies[1]))
        self.assertIsNone(sat.forwards(compiled[0]))
        self.assertIsNone(sat.forwards(compiled[1]))

        topo, policies = linear_all_ports((0, 1), (2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertTrue(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertIsNotNone(sat.forwards(policies[0]))
        self.assertIsNotNone(sat.forwards(policies[1]))
        self.assertIsNotNone(sat.forwards(compiled[0]))
        self.assertIsNotNone(sat.forwards(compiled[1]))

class TestCompleteGraph(unittest.TestCase):
    def setUp(self):
        self.k10topo, self.k10combined = k10()
        self.k10policies = [p for _, p in self.k10combined]

        self.k4topo, self.k4combined = k4()
        self.k4policies = [p for _, p in self.k4combined]

    @unittest.skipIf('EXPENSIVE_TESTS' not in os.environ, 'expensive')
    def testExpensivePhysEquiv(self):
        self.physEquiv(k10_nodes, self.k10policies)

    def testCheapPhysEquiv(self):
        self.physEquiv(k4_nodes, self.k4policies)

    @unittest.skipIf('EXPENSIVE_TESTS' not in os.environ, 'expensive')
    def testExpensivePhysSep(self):
        self.physSep(k10_nodes, self.k10topo, self.k10policies)

    def testCheapPhysSep(self):
        self.physSep(k4_nodes, self.k4topo, self.k4policies)

    @unittest.skipIf('EXPENSIVE_TESTS' not in os.environ, 'expensive')
    def testExpensiveCompile(self):
        self.sliceCompile(k10_nodes, self.k10topo, self.k10combined)

    def testCheapCompile(self):
        self.sliceCompile(k4_nodes, self.k4topo, self.k4combined)

    @unittest.skipIf('EXPENSIVE_TESTS' not in os.environ, 'expensive')
    def testExpensiveEdgeCompile(self):
        self.edgeCompile(k10_nodes, self.k10topo, self.k10combined)

    def testCheapEdgeCompile(self):
        self.edgeCompile(k4_nodes, self.k4topo, self.k4combined)

    def physEquiv(self, nodes, policies):
        for i in range(0, len(policies)):
            for j in range(len(policies)):
                print "testing %s equiv %s." % (nodes[i], nodes[j])
                result = sat.equivalent(policies[i],
                                        nc.PolicyUnion(policies[i],
                                                       policies[j]))
                if i is not j and\
                   len(set(nodes[i]).intersection(nodes[j])) > 1:
                    self.assertIsNotNone(result)
                else:
                    self.assertIsNone(result)

    def physSep(self, nodes, topo, policies):
        for i in range(0, len(policies)):
            for j in range(len(policies)):
                print "testing %s with %s." % (nodes[i], nodes[j])
                result = sat.isolated(topo, policies[i], policies[j])
                if len(set(nodes[i]).intersection(nodes[j])) > 1:
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

    def sliceCompile(self, nodes, topo, combined):
        compiled = cp.compile_slices(combined)
        for i in range(len(compiled)):
            for j in range(len(compiled)):
                print "testing compiled %s with %s."\
                      % (nodes[i], nodes[j])
                result = sat.isolated(topo, compiled[i], compiled[j])
                if i == j:
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

    def edgeCompile(self, nodes, topo, combined):
        compiled = ec.compile_slices(topo, combined, verbose=True)

        for i in range(len(compiled)):
            for j in range(len(compiled)):
                print "testing edge compiled %s with %s."\
                      % (nodes[i], nodes[j])
                result = sat.isolated(topo, compiled[i], compiled[j])
                if i == j:
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
