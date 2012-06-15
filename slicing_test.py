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
# /updates/Slice.py                                                            #
# Tests for Slice, the data structure to represent virtual network slices      #
################################################################################

import slicing
import unittest
import nxtopo
import netcore
import examples.mil as mil
import examples.day as day
import examples.amaz as amaz
import examples.simple as simple

class TestSlice(unittest.TestCase):
    def test_is_injective(self):
        self.assertTrue(slicing.is_injective({}))
        self.assertTrue(slicing.is_injective({1:1, 2:2, 3:3, 4:4}))
        self.assertTrue(slicing.is_injective({1:4, 2:5, 3:2, 4:7}))

    def test_not_is_injective(self):
        self.assertFalse(slicing.is_injective({1:1, 2:1}))
        self.assertFalse(slicing.is_injective({1:1, 2:2, 3:3, 4:4, 5:3}))
        self.assertFalse(slicing.is_injective({1:1, 2:2, 3:3, 4:2, 5:3}))
        self.assertFalse(slicing.is_injective({1:1, 2:2, 3:3, 4:3, 5:3}))

    def test_assert_is_injective(self):
        slicing.assert_is_injective({})
        slicing.assert_is_injective({1:1, 2:2, 3:3, 4:4})
        slicing.assert_is_injective({1:4, 2:5, 3:2, 4:7})

    def test_assert_not_is_injective(self):
        self.assertRaises(AssertionError, 
                          slicing.assert_is_injective,{1:1, 2:1})
        self.assertRaises(AssertionError, 
                          slicing.assert_is_injective,{1:1, 2:2, 3:3, 4:4, 5:3})
        self.assertRaises(AssertionError, 
                          slicing.assert_is_injective,{1:1, 2:2, 3:3, 4:2, 5:3})
        self.assertRaises(AssertionError, 
                          slicing.assert_is_injective,{1:1, 2:2, 3:3, 4:3, 5:3})
        
    def test_policy_is_total(self):
        topo = total_policy_topo()
        pred = netcore.Header('srcport', 80)
        # Edge ports:
        # (1, 3)
        # (1, 4)
        # (2, 3)
        # (3, 3)
        pol = {(1,3):pred,(1,4):pred,(2,3):pred,(3,3):pred}

        self.assertTrue(slicing.policy_is_total(pol,topo))
  
    def test_assert_policy_is_total(self):
        topo = total_policy_topo()
        pred = netcore.Header('srcport', 80)
        # Edge ports:
        # (1, 3)
        # (1, 4)
        # (2, 3)
        # (3, 3)
        pol = {(1,3):pred,(1,4):pred,(2,3):pred,(3,3):pred}
        slicing.assert_policy_is_total(pol ,topo)

    def test_policy_is_total(self):
        topo = total_policy_topo()
        pred = netcore.Header('srcport', 80)
        # Edge ports:
        # (1, 3)
        # (1, 4)
        # (2, 3)
        # (3, 3)

        pol = {}
        self.assertFalse(slicing.policy_is_total(pol, topo))

        pol = {(1,3):pred}
        self.assertFalse(slicing.policy_is_total(pol, topo))

        pol = {(2,3):pred,(3,3):pred}
        self.assertFalse(slicing.policy_is_total(pol, topo))

        pol = {(1,3):pred,(1,4):pred,(2,3):None,(3,3):pred}
        self.assertFalse(slicing.policy_is_total(pol, topo))


    def test_assert_not_policy_is_total(self):
        topo = total_policy_topo()
        pred = netcore.Header('srcport', 80)
        # Edge ports:
        # (1, 3)
        # (1, 4)
        # (2, 3)
        # (3, 3)

        pol = {}
        self.assertRaises(AssertionError,
                          slicing.assert_policy_is_total, pol, topo)
        pol = {(1,3):pred}
        self.assertRaises(AssertionError,
                          slicing.assert_policy_is_total, pol, topo)
        pol = {(2,3):pred,(3,3):pred}
        self.assertRaises(AssertionError,
                          slicing.assert_policy_is_total, pol, topo)
        pol = {(1,3):pred,(1,4):pred,(2,3):None,(3,3):pred}
        self.assertRaises(AssertionError,
                          slicing.assert_policy_is_total, pol, topo)

    def test_assert_set_equals(self):
        slicing.assert_set_equals(set([]),set([]))
        slicing.assert_set_equals(set([1, 2, 3]),set([1, 2, 3]))
        slicing.assert_set_equals(set([1]),set([1]))

    def test_assert_not_set_equals(self):
        def helper(lst1, lst2):
            self.assertRaises(AssertionError, 
                              slicing.assert_set_equals, set(lst1), set(lst2))
            self.assertRaises(AssertionError, 
                              slicing.assert_set_equals, set(lst2), set(lst1))
        # test fucntioning    
        helper([],[1])
        helper([0],[1])
        helper([0,2,3],[0,2])
        helper([0,2,3],[0,2,4])
        helper([1,2],[1])
        helper([0,3,4],[1,2,5])

        # test type safety
        self.assertRaises(AssertionError, 
                          slicing.assert_set_equals, [1], [1])
        self.assertRaises(AssertionError, 
                          slicing.assert_set_equals, set([1]), [1])
        self.assertRaises(AssertionError, 
                          slicing.assert_set_equals, [1], set([1]))
        
    def test_examples(self):
        # Maintains examples
        self.assertEquals(3, len(mil.get_slices()))
        self.assertEquals(3, len(amaz.get_slices()[1]))
        self.assertEquals(1, len(simple.get_slices()))
        self.assertEquals(3, len(day.get_slices()))

def total_policy_topo():
    topo = nxtopo.NXTopo()
    for i in range(1,4):
        topo.add_switch(i)
        topo.add_host(i + 10)
        topo.add_link(i, i + 10)
        for j in range(1,i):
            topo.add_link(i,j)
    topo.add_host(10)
    topo.add_link(1,10)
    topo.finalize()
    
    return topo
      
if __name__ == '__main__':
    unittest.main()
