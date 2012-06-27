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
# /slices/examples/policy_gen.py                                               #
# Tools to generate policies                                                   #
################################################################################
"""Tools to generate policies"""

from netcore import forward, inport, nary_policy_union, then

def flood(topo, all_ports=False):
    """Construct a policy that floods packets out each port on each switch.

    if all_ports is set, even forward back out the port it came in.
    """
    switches = topo.switches()
    policies = []
    for switch in switches:
        ports = set(topo.node[switch]['port'].keys())
        for port in ports:
            # Make a copy of ports without this one
            if all_ports:
                other_ports = ports
            else:
                other_ports = ports.difference([port])
            for other_port in other_ports:
                pol = inport(switch, port) |then| forward(switch, other_port)
                policies.append(pol)
    return nary_policy_union(policies).reduce()
