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
# /updates/util.py                                                             #
# Tools for slicing                                                            #
################################################################################
"""Tools for slicing."""

def id_map(items):
    """Make a mapping that is the identity over items."""
    return dict((i, i) for i in items)

def ports_of_topo(topo, end_hosts=False):
    """Get all (switch, port)s of a topo as a set."""
    output = set()
    for number, node in topo.node.items():
        ports = node['port'].keys()
        for p_num in ports:
            # Only include if a switch, or we're including end hosts
            if p_num != 0 or end_hosts:
                output.add((number, p_num))
    return output

def build_external_predicate(l_topo):
    """Build external predicates for topo that accept all packets."""
    predicates = {}
    for n, node in l_topo.node.items():
        if node['isSwitch']:
            for p, (target, target_port) in node['port'].items():
                if target_port == 0: # that means target is an end host
                    predicates[(n, p)] = nc.Top()
    return predicates
