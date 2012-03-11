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
import Slice
import unittest

class TestSlice(unittest.TestCase):
    def test_is_injective(self):
        self.assertTrue(Slice.is_injective({}))
        self.assertTrue(Slice.is_injective({1:1, 2:2, 3:3, 4:4}))
        self.assertTrue(Slice.is_injective({1:4, 2:5, 3:2, 4:7}))

    def test_not_is_injective(self):
        self.assertFalse(Slice.is_injective({1:1, 2:1}))
        self.assertFalse(Slice.is_injective({1:1, 2:2, 3:3, 4:4, 5:3}))
        self.assertFalse(Slice.is_injective({1:1, 2:2, 3:3, 4:2, 5:3}))
        self.assertFalse(Slice.is_injective({1:1, 2:2, 3:3, 4:3, 5:3}))
