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
# /slices/optimize.py                                                          #
# VLAN reduction optimizations                                                 #
################################################################################
"""Tools to calculate the minimium assignment of vlans to slices."""

import Numberjack as nj
import MiniSat

MAX_VLAN = 255
MIN_VLAN = 1

def assign_vlans(slices, conflicts):
    """Assign vlans to slices minimizing the number of tags used.

    ARGS:
        slices:  a set of slices
        conflicts:  a set of pairs of slices, may be undirected; putting in both
            directions only adds work for the solver

    RETURNS:
        {slice: vlan_tag}

    At present, uses the one-vlan-per-slice method via graph coloring.  For
    efficiency, we force vlan numbers to be at most len(slices), since
    n-coloring a graph with n vertices is guaranteed to be possible.
    """
    max_vlan = min(MAX_VLAN, len(slices))
    vlan_vars = nj.VarArray(len(slices), MIN_VLAN, max_vlan)
    vlans = dict(zip(slices, vlan_vars))
    constraints = []
    # Build color constraints
    for (s1, s2) in conflicts:
        constraints.append(vlans[s1] != vlans[s2])
    # Build variables to count distinct vlans, so we can minimize
    count_vars = []
    for i in range(MIN_VLAN, max_vlan + 1):
        for var in vlan_vars:
            count_vars.append(var != i)
    constraints.append(nj.Minimise(sum(count_vars)))
    model = nj.Model(constraints)
    solver = MiniSat.Solver(model)
    if solver.solve():
        return dict([(k, v.get_value()) for k, v in vlans.items()])
    else:
        return None

