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
# /updates/compile.py                                                          #
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

We further need to add VLAN tags to packets coming in over external ports.

Finally, we traverse the tree again, mapping virtual nodes and ports to their
physical counterparts as provided by the slice's mapping.
"""

import copy
import netcore as nc
from netcore import then
import slicing
import vlan as vl

def transform(combined, assigner=vl.sequential, verbose=False):
    """Turn a set of slices sharing a physical topology into a single policy.
    ARGS:
        combined:  set of (slices, policies) (with the same physical topology) to
            combine
        assigner:  function to use to assign vlans to slices.  Must return a
            {slice: vlan} dictionary, defaults to sequential.
        verbose:  print out progress information

    RETURNS:
        a single Policy encapsulating the shared but isolated behavior of all
        the slices
    """
    policy_list = compile_slices(combined, assigner=assigner, verbose=verbose)
    return nc.nary_policy_union(policy_list)

def compile_slices(combined, assigner=vl.sequential, verbose=False):
    """Turn a set of slices sharing a physical topology into a single policy.
    ARGS:
        combined:  set of (slices, policies) (with the same physical topology) to
            combine
        assigner:  function to use to assign vlans to slices.  Must return a
            {slice: vlan} dictionary, defaults to sequential.
        verbose:  print out progress information

    RETURNS:
        a single Policy encapsulating the shared but isolated behavior of all
        the slices
    """
    slices = [s for (s, p) in combined]
    vlans = assigner(slices)
    policy_list = []
    count = 0
    for slic, policy in combined:
        vlan = vlans[slic]
        # Produce a policy that only accepts packets within our vlan
        safe_policy = isolated_policy(policy, vlan)
        safe_policy.get_physical_rep(slic.node_map, slic.port_map)
        # Produce a separate policy that adds vlan tags to safe incoming packets
        inport_policy = external_to_vlan_policy(slic, policy, vlan)
        inport_policy.get_physical_rep(slic.node_map, slic.port_map)
        # Take their union
        safe_inport_policy = safe_policy + inport_policy
        safe_inport_policy.get_physical_rep(slic.node_map, slic.port_map)

        # Modify the result to strip the vlan tag from outbound ports
        # Note that this should be the last step.  If our policy takes an
        # incoming packet and forwards it directly out, we should not add a vlan
        # tag.
        full_policy = internal_strip_vlan_policy(slic, safe_inport_policy)

        policy_list.append(
            full_policy.get_physical_rep(slic.node_map, slic.port_map))
        if verbose:
            print 'Processed %d slices.' % count
            count += 1
    return policy_list

def isolated_policy(policy, vlan):
    """Produce a policy for slic restricted to its vlan.

    ARGS:
        policy:  Policy to restrict
        vlan:  vlan id to restrict policy to

    RETURNS:
        a new policy object that is policy but restricted to its vlan.
    """
    vlan_predicate = nc.Header({'vlan': vlan})
    return policy % vlan_predicate

def external_predicate((switch, port), predicate):
    """Produce a predicate that matches predicate incoming on (switch, port).

    ARGS:
        (switch, port):  precise network location of incoming port
        predicate:  isolation predicate to satisfy

    RETURNS:
        Predicate object matching predicate on switch and port.
    """
    return nc.inport(switch, port) & predicate

def modify_vlan(policy, vlan):
    """Re-write all actions of policy to set vlan to vlan."""
    if isinstance(policy, nc.PrimitivePolicy):
        policy = copy.deepcopy(policy)
        for action in policy.actions:
            action.modify['vlan'] = vlan
        return policy
    elif isinstance(policy, nc.PolicyUnion):
        left = modify_vlan(policy.left, vlan)
        right = modify_vlan(policy.right, vlan)
        return left + right
    else: # isinstance(policy, nc.PolicyRestriction)
        new_policy = modify_vlan(policy.policy, vlan)
        return new_policy % policy.predicate

def modify_vlan_local(policy, (switch, port), tag):
    """Re-write all actions of policy to set vlan to tag on switch, port.

    Non-destructive, returns an entirely new object.
    """
    if isinstance(policy, nc.PrimitivePolicy):
        # get a new copy of all the actions so we can safely modify them
        output_actions = []
        for action in policy.actions:
            if action.switch == switch and port in action.ports:
                # Split ports into ports we need to change and ports we don't
                bad_ports = [port]
                good_ports = set(action.ports).difference([port])

                # Build new actions around these objects
                out_modify = dict(action.modify)
                out_modify['vlan'] = tag
                out_a = nc.Action(action.switch, bad_ports,
                                  out_modify, action.obs)
                output_actions.append(out_a)
                if len(good_ports) > 0:
                    output_actions.append(nc.Action(action.switch, good_ports,
                                                    action.modify, action.obs))
            else:
                # No need to modify it
                output_actions.append(action)
        return policy.predicate |then| output_actions
    elif isinstance(policy, nc.PolicyUnion):
        left = modify_vlan_local(policy.left, (switch, port), tag)
        right = modify_vlan_local(policy.right, (switch, port), tag)
        return left + right
    elif isinstance(policy, nc.PolicyRestriction):
        new_policy = modify_vlan_local(policy.policy, (switch, port), tag)
        return new_policy % policy.predicate
    elif isinstance(policy, nc.BottomPolicy):
        return policy
    else:
        raise Exception("Unexpected policy: %s\n" % policy)

def strip_vlan(policy, (switch, port)):
    """Re-write all actions of policy to set vlan to 0 on switch, port."""
    return modify_vlan_local(policy, (switch, port), 0)

def external_to_vlan_policy(slic, policy, vlan):
    """Produce a policy that moves packets along external ports into the vlan.

    Just restricting packets to the vlan means that packets can never enter the
    slice.  To let packets enter, we need to make another copy of the policy,
    restrict it to only entrances, and change the actions to add the vlan.

    ARGS:
        slic:  Slice to produce this policy for
        policy:  Policy to restrict
        vlan:  vlan to enter

    RETURNS:
        A policy that moves packets incoming to external ports into the vlan,
        but only if they satisfy the slice's isolation predicates.
    """
    external_predicates = [external_predicate(loc, pred)
                           for loc, pred in slic.edge_policy.iteritems()]
    predicate = nc.nary_union(external_predicates)
    policy_into_vlan = modify_vlan(policy, vlan)
    return policy_into_vlan % (predicate & nc.Header({'vlan': 0}))

def internal_strip_vlan_policy(slic, policy):
    """Produce a policy that strips the vlan tags from outgoing edge ports.

    The produced policy can be thought of as working the following way:
        def actions(packet, loc):
            acts = policy.get_actions(packet, loc)
            if loc in slic.edge_ports:
                [act.set_vlan(0) for act in acts]
            return acts

    but must take care to split actions that forward to multiple ports into
    smaller actions where necessary so that the vlan stripping is only done as
    appropriate.
    """
    for ((switch, port), _) in slic.edge_policy.iteritems():
        policy = strip_vlan(policy, (switch, port))
    return policy
