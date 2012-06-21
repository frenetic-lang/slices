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
    # for each possible value v, that value is used iff
    # s1 = v \/ s2 = v \/ ... \/ sn = v
    # This term is true (1) if that color is used.
    # Minimize the sum of those terms, and you minimize the number of colors
    # used.
    count_vars = []
    for i in range(MIN_VLAN, max_vlan + 1):
        terms = []
        for var in vlan_vars:
            terms.append(var == i)
        count_vars.append(reduce(lambda x, y: x | y, terms))

    constraints.append(nj.Minimise(sum(count_vars)))
    model = nj.Model(constraints)
    solver = MiniSat.Solver(model)
    if solver.solve():
        return dict([(k, v.get_value()) for k, v in vlans.items()])
    else:
        return None

def assign_n_vlans(n, slices, conflicts):
    """Assign at most n vlans to slices, or return None.

    Does not try to optimize, just tries to meet the constraint."""
    max_vlan = min(MAX_VLAN, n)
    vlan_vars = nj.VarArray(len(slices), MIN_VLAN, max_vlan)
    vlans = dict(zip(slices, vlan_vars))
    constraints = []
    # Build color constraints
    for (s1, s2) in conflicts:
        constraints.append(vlans[s1] != vlans[s2])
    model = nj.Model(constraints)
    solver = MiniSat.Solver(model)
    if solver.solve():
        return dict([(k, v.get_value()) for k, v in vlans.items()])
    else:
        return None

def main():
    slices = [1, 2, 3, 4]
    # Graph is 3 colorable
    conflicts = [
                 (1, 2),
                 (1, 3),
                 (1, 4),
                 (2, 3),
                 (3, 4),
                ]
    print assign_vlans(slices, conflicts)
    print assign_n_vlans(3, slices, conflicts)

if __name__ == '__main__':
    main()
