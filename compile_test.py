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
# /updates/compile_test.py                                                     #
# Tests for compile.py, which implements the slice compiler                    #
################################################################################
import compile as cp
import examples.amaz as az
import copy
import netcore as nc
from netcore import Action, inport, Header, then
import slicing
import unittest

topo, slices = az.get_slices()

a1 = Action(1, [1, 2, 3], {'srcmac':1})
a2 = Action(2, [2, 3], {'dstmac':2})
a3 = Action(3, [3], {'ethtype':3})
a4 = Action(3, [4, 5, 6], {'srcip':4})
a5 = Action(3, [3, 5, 6, 7], {'vlan':5})

p1 = inport(1, 0)
p2 = inport(2, 1) + inport(2, 3)
p3 = inport(3, 3) & Header('srcmac', 1)
p4 = p3 - Header('dstmac', 2)

l1 = p1 |then| a1
l2 = p2 |then| a2
l3 = p3 |then| a3
l4 = p4 |then| a4
l5 = (p1 & p4) |then| a5

big_policy = ((l3 + l4 + l5) % p2) + l2 + l1

def actions_of_policy(policy):
    if isinstance(policy, nc.PrimitivePolicy):
        return policy.actions
    elif isinstance(policy, nc.PolicyUnion):
        return actions_of_policy(policy.left) + actions_of_policy(policy.right)
    else: # isinstance(policy, nc.PolicyRestriction)
        return actions_of_policy(policy.policy)

def action_to_microactions(action):
    switch = action.switch
    modify = action.modify
    return [Action(switch, [p], copy.copy(modify)) for p in action.ports]

def flatten(l):
    """An opaque way to flatten a list."""
    return [item for sublist in l for item in sublist]

class TestVlanAssignment(unittest.TestCase):
    def test_basic(self):
        slices = range(0,10)
        assigned = cp.sequential(slices)
        # Verify via pigeonhole principle - if there are as many slices as
        # vlans, no vlan is used with two slices
        self.assertEqual(len(slices), len(set(assigned.keys())))

    def test_get_links_internal(self):
        links = cp.links(topo, 1)
        switches = [(s1, s2) for (s1, p1), (s2, p2) in links]

        # Verify all the expected switch links
        self.assertItemsEqual([(1,3), (1,4), (1,5)], switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in links:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_get_links_external(self):
        links = cp.links(topo, 3)
        switches = [(s1, s2) for (s1, p1), (s2, p2) in links]

        # Verify all the expected switch links
        self.assertItemsEqual([(3,1), (3,2)], switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in links:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_edges_of_topo(self):
        edges = cp.edges_of_topo(topo)

        # Verify all the expected switch links
        switches = [(s1, s2) for (s1, p1), (s2, p2) in edges]
        self.assertItemsEqual([(1, 3), (1, 4), (1, 5),
                               (2, 3), (2, 4), (2, 5),
                               (3, 1), (3, 2),
                               (4, 1), (4, 2),
                               (5, 1), (5, 2)],
                              switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in edges:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_map_edges(self):
        s = slices[0]
        l_edges = cp.edges_of_topo(s.l_topo)
        p_edges = cp.edges_of_topo(topo)
        mapped = cp.map_edges(l_edges, s.node_map, s.port_map)
        switches = [(s1, s2) for (s1, p1), (s2, p2) in mapped]

        # Verify all the expected switch links
        self.assertItemsEqual([(1, 3), (1, 4), (3, 1), (4, 1)], switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in mapped:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_share_edge(self):
        self.assertTrue( cp.share_edge(slices[0], slices[1]))
        self.assertFalse(cp.share_edge(slices[0], slices[2]))
        self.assertFalse(cp.share_edge(slices[1], slices[2]))

    def test_optimal(self):
        colors = cp.slice_optimal(slices)

        # Only 0 and 1 share an edge, so they should be different colors
        self.assertNotEqual(colors[slices[0]], colors[slices[1]])
        # 2 is disconnected, so this is 2-colorable
        self.assertEqual(2, len(set(colors.values())))

class TestCompile(unittest.TestCase):
    def test_modify_vlan(self):
        modified = cp.modify_vlan(big_policy, -1)
        for action in actions_of_policy(modified):
            self.assertDictContainsSubset({'vlan': -1}, action.modify)

    def test_strip_vlan(self):
        # Test by expanding to actions that only handle one port at a time, and
        # verifying from there.
        micro = flatten([action_to_microactions(a)
                         for a in actions_of_policy(big_policy)])
        for action in micro:
            if action.switch == 3 and action.ports == [3]:
                action.modify['vlan'] = 0
        modified = cp.strip_vlan(big_policy, (3, 3))

        modified_micro = flatten([action_to_microactions(a)
                                  for a in actions_of_policy(modified)])
#       print "\n".join([str(x) for x in micro])
#       print ""
#       print "\n".join([str(x) for x in modified_micro])

        self.assertItemsEqual(micro, modified_micro)

if __name__ == '__main__':
    unittest.main()
