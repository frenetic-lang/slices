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
# /slices/verification.py                                                      #
# Tools to verify properties of netcore programs and slices                    #
################################################################################
"""Non-SAT-based validation tools for netcore programs and slices."""

import util

def slice_switch_iso(slice1, slice2):
    """Test if two slices overlap on any switches."""
    switches1 = set(slice1.node_map.values())
    switches2 = set(slice2.node_map.values())
    return len(switches1.intersection(switches2)) > 0

def slice_node_iso(slice1, slice2):
    """Test if two slices overlap on any switches or hosts.
    
    Note that we can only generally detect hosts by mapping ports.
    """
    ports1 = util.ports_of_topo(slice1.l_topo, end_hosts=True)
    ports2 = util.ports_of_topo(slice2.l_topo, end_hosts=True)

    ports_mapped1 = [slice1.port_map[p] for p in ports1]
    ports_mapped2 = [slice2.port_map[p] for p in ports2]

    switches1 = set([s for (s, _) in ports_mapped1])
    switches2 = set([s for (s, _) in ports_mapped2])

    return len(switches1.intersection(switches2)) > 0

def disjoint_observations(policy1, policy2):
    obs1 = util.observations(policy1)
    obs2 = util.observations(policy2)
    intersection = obs1.intersection(obs2)
    return len(intersection) == 0
