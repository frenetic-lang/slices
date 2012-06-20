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
# /slices/edge_compile_test.py                                                 #
# Tests for edge_compile.py, which implements the slice compiler               #
################################################################################

import compile_test as ct
import examples.triangle as tri
import edge_compile as ec
import unittest

topo, slices = tri.get_slices()

class TestEdgeCompile(unittest.TestCase):
    def test_edge_of_port(self):
        s1 = 'PI1'
        s2 = 'PI2'
        p1 = topo.node[s1]['ports'][s2]
        p2 = topo.node[s2]['ports'][s1]

        out = ec.edge_of_port(topo, (s1, p1))

        self.assertEqual(((s1, p1), (s2, p2)), out)

        s1 = 'PE1'
        s2 = 'GH1'
        p1 = topo.node[s1]['ports'][s2]
        p2 = topo.node[s2]['ports'][s1]

        out = ec.edge_of_port(topo, (s1, p1))

        self.assertEqual(((s1, p1), (s2, p2)), out)

    def test_symmetric_edge(self):
        sources = range(0,99)
        sinks = range(100, 199)
        edges = zip(sources, sinks)
        vlans = range(200,299)
        d = dict(zip(edges, vlans))
        # Test already-symmetric case
        d[(1000, 1000)] = 1000
        symm = ec.symmetric_edge(d)
        self.assertIsNot(d, symm)
        items = sorted(symm.items())
        for (s1, s2), vlan in d.items():
            self.assertIn(((s1, s2), vlan), items)
            self.assertIn(((s2, s1), vlan), items)

    def test_get_slice_lookup(self):
        edges = range(0,100)
        slices = range(70, 170)
        tags = range(150, 250)
        d = {}
        for e in edges:
            d[e] = {}
            for s, t in zip(slices, tags):
                d[e][s] = t
        out = ec.get_slice_lookup(d)

        self.assertIsNot(d, out)
        for e, slices in d.items():
            for s, t in slices.items():
                self.assertEqual(t, out[s][e])

if __name__ == '__main__':
    unittest.main()
