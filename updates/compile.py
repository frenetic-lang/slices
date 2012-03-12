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
# /updates/slicing.py                                                          #
# Tools to compile virtual network policies to physical network policies       #
################################################################################
"""Tools to compile virtual network policies to physical network policies.

An overview of the compilation process:

We take as input a set of slices that all share the same physical topology.

First, we assign each slice a VLAN id for internal, vetted traffic.

We next need to transform the slices so that when their traffic is mixed with
foreign traffic, they use their VLAN to distinguish safe and unsafe traffic.
This results in two sets of policies, and we take their union:

* All virtual policies restricted by the predicate that traffic is within the
    appropriate VLAN.
* All virtual policies intersected with ((incoming to external port n) union
    (satisfies the isolation predicate on internal port n)) for each external
    port.  This can be further reduced to only applying this transformation for
    rules on switches that actually bear the relevant external port, but for a
    first pass, we take the overapproximation.

At this point, all isolation properties are satisfied, but we need additionally
to take packets that travel out over external ports and strip then of their VLAN
tags.  This cannot be accomplished combinatorically, so instead we have to
traverse the policy's object tree, and wherever we have an action that results
in forwarding to an external port, modify the packet to have a vlan tag of 0.

Finally, we traverse the tree again, mapping virtual nodes and ports to their
physical counterparts as provided by the slice's mapping.
"""

def compile(slices):
    """Turn a set of slices sharing a physical topology into a single policy.
    ARGS:
        slices: set of slices (with the same physical topology) to combine

    RETURNS:
        a single Policy encapsulating the shared but isolated behavior of all
        the slices
    """
    # Pick VLANS
    for slic in slices:
        # Make slice safe
        # Drop out of vlan on external ports
        # Map to physical
        pass
    # return union of policies

def isolated_policy(slic, vlan):
    """Produce a policy for slic restricted to its vlan with edge constraints.

    ARGS:
        slic:  Slice to produce a safe policy for
        vlan:  vlan id to restrict slic to

    RETURNS:
        a new policy object that is slic's policy but restricted to its vlan and
        with slic's incoming edge constraints enforced.
    """
    pass
