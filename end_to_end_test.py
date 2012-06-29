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

To print out finer-grained progress information on tests, set VERBOSE_TESTS.
"""

from examples import topology_gen, policy_gen
import sat, nxtopo, slicing
import compile as cp
import edge_compile as ec
import networkx as nx
import netcore as nc
import os
import unittest
from test_util import linear, linear_all_ports, k10_nodes, k10, k4_nodes, k4

verbose = 'VERBOSE_TESTS' in os.environ

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
        self.assertIsNone(sat.not_empty(policies[0]))
        self.assertIsNone(sat.not_empty(policies[1]))
        topo, policies = linear((0, 1, 2), (1, 2, 3))
        self.assertIsNotNone(sat.not_empty(policies[0]))
        self.assertIsNotNone(sat.not_empty(policies[1]))
        topo, policies = linear_all_ports((0, 1), (2, 3))
        self.assertIsNotNone(sat.not_empty(policies[0]))
        self.assertIsNotNone(sat.not_empty(policies[1]))

class TestCompile(unittest.TestCase):
    def testBasicCompile(self):
        topo, policies = linear((0, 1, 2, 3), (0, 1, 2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = cp.compile_slices(combined)
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))

        self.assertTrue(sat.compiled_correctly(policies[0], compiled[0]))
        self.assertTrue(sat.compiled_correctly(policies[1], compiled[1]))

class TestEdgeCompile(unittest.TestCase):
    def testBasicCompile(self):
        topo, policies = linear((0, 1, 2, 3), (0, 1, 2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertTrue(sat.compiled_correctly(policies[0], compiled[0]))
        self.assertTrue(sat.compiled_correctly(policies[1], compiled[1]))

        topo, policies = linear((0, 1, 2), (1, 2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertFalse(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertTrue(sat.compiled_correctly(policies[0], compiled[0]))
        self.assertTrue(sat.compiled_correctly(policies[1], compiled[1]))

        topo, policies = linear((0, 1), (2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertTrue(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertTrue(sat.compiled_correctly(policies[0], compiled[0]))
        self.assertTrue(sat.compiled_correctly(policies[1], compiled[1]))

        topo, policies = linear_all_ports((0, 1), (2, 3))
        slices = [slicing.ident_map_slice(topo, {}) for p in policies]
        combined = zip(slices, policies)
        compiled = ec.compile_slices(topo, combined)
        self.assertTrue(sat.isolated(topo, policies[0], policies[1]))
        self.assertTrue(sat.isolated(topo, compiled[0], compiled[1]))
        self.assertTrue(sat.compiled_correctly(policies[0], compiled[0]))
        self.assertTrue(sat.compiled_correctly(policies[1], compiled[1]))

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
                if verbose:
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
                if verbose:
                    print "testing %s with %s." % (nodes[i], nodes[j])
                result = sat.isolated(topo, policies[i], policies[j])
                if len(set(nodes[i]).intersection(nodes[j])) > 1:
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

    def sliceCompile(self, nodes, topo, combined):
        compiled = cp.compile_slices(combined)

        for i in range(len(compiled)):
            self.assertTrue(sat.compiled_correctly(combined[i][1],
                                                   compiled[i]))
            for j in range(len(compiled)):
                if verbose:
                    print "testing compiled %s with %s."\
                          % (nodes[i], nodes[j])
                result = sat.isolated(topo, compiled[i], compiled[j])
                if i == j:
                    self.assertFalse(result)
                else:
                    cc = sat.compiled_correctly(combined[i][1], compiled[j])
                    self.assertIsNotNone(cc)
                    self.assertTrue(result)

    def edgeCompile(self, nodes, topo, combined):
        compiled = ec.compile_slices(topo, combined, verbose=verbose)

        for i in range(len(compiled)):
            try:
                self.assertTrue(sat.compiled_correctly(combined[i][1],
                                                       compiled[i]))
            except AssertionError:
                import IPython.Shell; IPython.Shell.IPShellEmbed(argv=[])()
            self.assertFalse(sat.isolated(topo, compiled[i], compiled[i]))
            for j in range(len(compiled)):
                if verbose:
                    print "testing edge compiled %s with %s."\
                          % (nodes[i], nodes[j])
                if i != j:
#                   r = sat.compiled_correctly(combined[i][1],
#                                              compiled[j])
#                   if r:
#                       import IPython.Shell; IPython.Shell.IPShellEmbed(argv=[])()
#                   self.assertFalse(r)
                    self.assertTrue(sat.isolated(topo, compiled[i],
                                                 compiled[j]))

if __name__ == '__main__':
    unittest.main()
