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
# /slices/verification_test.py                                                 #
# Test verification correctness                                                #
################################################################################
"""Test verification correctness."""

from examples import topology_gen, policy_gen
import edge_compile as ec
import networkx as nx
import netcore as nc
import unittest
import verification

from test_util import linear, linear_all_ports, k10_nodes, k10, k4_nodes, k4

class ValidationTest(unittest.TestCase):
    def setUp(self):
        self.k10topo, self.k10combined = k10()
        self.k10policies = [p for _, p in self.k10combined]
        self.k10slices = [s for s, _ in self.k10combined]

        self.k4topo, self.k4combined = k4()
        self.k4policies = [p for _, p in self.k4combined]
        self.k4slices = [s for s, _ in self.k4combined]

    def test_slice_iso(self):
        self.switch_phys_sep(k10_nodes, self.k10slices)
        self.switch_node_sep(k10_nodes, self.k10slices)

    def switch_phys_sep(self, nodes, slices):
        for i in range(0, len(slices)):
            for j in range(len(slices)):
                result = verification.slice_switch_iso(slices[i], slices[j])
                if len(set(nodes[i]).intersection(nodes[j])) > 0:
                    self.assertTrue(result)
                else:
                    self.assertFalse(result)

    def switch_node_sep(self, nodes, slices):
        for i in range(0, len(slices)):
            for j in range(len(slices)):
                result = verification.slice_node_iso(slices[i], slices[j])
                if len(set(nodes[i]).intersection(nodes[j])) > 0:
                    self.assertTrue(result)
                else:
                    self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
