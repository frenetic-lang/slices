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
# /updates/vlan_test.py                                                        #
# Tests for vlan.py, which assigns vlan tags to slices                         #
################################################################################

import examples.amaz as az
import vlan
import unittest
import util

topo, slices = az.get_slices()

def qualified_edge(topology, (s1, s2)):
    """Convert (s1, s2) edge into ((s1, p1), (s2, p2))."""
    p1 = topology.node[s1]['ports'][s2]
    p2 = topology.node[s2]['ports'][s1]
    return ((s1, p1), (s2, p2))

class TestVlanAssignment(unittest.TestCase):
    def test_basic(self):
        slices = range(0,10)
        assigned = vlan.sequential(slices)
        # Verify via pigeonhole principle - if there are as many slices as
        # vlans, no vlan is used with two slices
        self.assertEqual(len(slices), len(set(assigned.keys())))

    def test_get_links_internal(self):
        links = util.links(topo, 1)
        switches = [(s1, s2) for (s1, p1), (s2, p2) in links]

        # Verify all the expected switch links
        self.assertItemsEqual([(1,3), (1,4), (1,5)], switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in links:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_get_links_external(self):
        links = util.links(topo, 3)
        switches = [(s1, s2) for (s1, p1), (s2, p2) in links]

        # Verify all the expected switch links
        self.assertItemsEqual([(3,1), (3,2)], switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in links:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_edges_of_topo(self):
        edges = vlan.edges_of_topo(topo)

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

    def test_edge_in(self):
        all_edges = set([(1, 3), (1, 4), (1, 5),
                         (2, 3), (2, 4), (2, 5),
                         (3, 1), (3, 2), (3, 7),
                         (4, 1), (4, 2), (4, 8),
                         (5, 1), (5, 2), (5, 9)])
        edges0 = set([qualified_edge(topo, e)
                      for e in [(1, 3), (1, 4), (3, 1), (4, 1)]])
        edges1 = set([qualified_edge(topo, e)
                      for e in [(1, 3), (1, 5), (3, 1), (5, 1)]])
        edges2 = set([qualified_edge(topo, e)
                      for e in [(2, 4), (2, 5), (4, 2), (5, 2)]])

        for e in edges0:
            self.assertTrue(vlan.edge_in(e, slices[0]))
        for e in all_edges - edges0:
            self.assertFalse(vlan.edge_in(e, slices[0]))

        for e in edges1:
            self.assertTrue(vlan.edge_in(e, slices[1]))
        for e in all_edges - edges1:
            self.assertFalse(vlan.edge_in(e, slices[1]))

        for e in edges2:
            self.assertTrue(vlan.edge_in(e, slices[2]))
        for e in all_edges - edges2:
            self.assertFalse(vlan.edge_in(e, slices[2]))

    def test_map_edges(self):
        s = slices[0]
        l_edges = vlan.edges_of_topo(s.l_topo)
        p_edges = vlan.edges_of_topo(topo)
        mapped = vlan.map_edges(l_edges, s.node_map, s.port_map)
        switches = [(s1, s2) for (s1, p1), (s2, p2) in mapped]

        # Verify all the expected switch links
        self.assertItemsEqual([(1, 3), (1, 4), (3, 1), (4, 1)], switches)
        # Verify that all the port labels are what they are in the topology
        for ((s1, p1), (s2, p2)) in mapped:
            self.assertEqual((s2, p2), topo.node[s1]['port'][p1])

    def test_share_edge(self):
        self.assertTrue( vlan.share_edge(slices[0], slices[1]))
        self.assertFalse(vlan.share_edge(slices[0], slices[2]))
        self.assertFalse(vlan.share_edge(slices[1], slices[2]))

    def test_optimal(self):
        colors = vlan.slice_optimal(slices)

        # Only 0 and 1 share an edge, so they should be different colors
        self.assertNotEqual(colors[slices[0]], colors[slices[1]])
        # 2 is disconnected, so this is 2-colorable
        self.assertEqual(2, len(set(colors.values())))

if __name__ == '__main__':
    unittest.main()
