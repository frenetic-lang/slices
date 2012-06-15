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
import netcore

class VlanException(Exception):
    """Exception to represent failure to map to VLAN tags."""
    pass

def sequential(slices):
    """Assign vlans to slices assuming they all overlap, sequentially."""
    if len(slices) > 255:
        raise VlanException('Too many slices')
    vlan = 1
    d = {}
    for s in slices:
        d[s] = vlan
        vlan += 1
    return d

def links(topo, sid):
    """Get a list of ((s,p), (s,p)) for all outgoing links from this switch."""
    switch = topo.node[sid]
    return [((sid, our_port), (them, their_port))
            for our_port, (them, their_port) in switch['port'].items()
            # If their_port == 0, they're an end host, not a switch.
            # We don't care about end hosts.
            if their_port != 0]

def edges_of_topo(topo):
    """Get all switch-switch edges in a topo, in links format."""
    # Need to dereference switch id to get full object
    ls = []
    for switch in topo.switches():
        ls.extend(links(topo, switch))
    return ls

def map_edges(links, switch_map, port_map):
    """Map ((s, p), (s, p)) edges according to the two maps."""
    mapped = []
    for (s1, p1), (s2, p2) in links:
        # only include the port result from the port map, don't rely on the
        # switch recorded there
        mapped.append(((switch_map[s1], port_map[(s1, p1)][1]),
                       (switch_map[s2], port_map[(s2, p2)][1])))
    return mapped

def share_edge(s1, s2):
    """Determine whether two slices share a physical edge."""
    # This is only correct if we have a guarantee that the topologies are sane,
    # and only give us real internal edges.
    s1_ls = set(map_edges(edges_of_topo(s1.l_topo), s1.node_map, s1.port_map))
    s2_ls = set(map_edges(edges_of_topo(s2.l_topo), s2.node_map, s2.port_map))
    return not s1_ls.isdisjoint(s2_ls)

def slice_optimal(slices):
    # Import here because optimize has hard-to-install dependencies
    import optimize
    conflicts = []
    for i in range(0, len(slices)):
        for j in range(i+1, len(slices)):
            if share_edge(slices[i], slices[j]):
                conflicts.append((slices[i], slices[j]))
    return optimize.assign_vlans(slices, conflicts)

def transform(slices, assigner=sequential):
    """Turn a set of slices sharing a physical topology into a single policy.
    ARGS:
        slices:  set of (slices, policies) (with the same physical topology) to
            combine
        assigner:  function to use to assign vlans to slices.  Must return a
            {slice: vlan} dictionary, defaults to sequential.

    RETURNS:
        a single Policy encapsulating the shared but isolated behavior of all
        the slices
    """
    vlans = assigner(slices)
    policy_list = []
    for slic in slices:
        vlan = vlans[slic]
        # Produce a policy that only accepts packets within our vlan
        safe_policy = isolated_policy(policy, vlan)
        # Produce a separate policy that adds vlan tags to safe incoming packets
        inport_policy = external_to_vlan_policy(slic, policy, vlan)
        # Take their union
        safe_inport_policy = safe_policy + inport_policy

        # Modify the result to strip the vlan tag from outbound ports
        # Note that this should be the last step.  If our policy takes an
        # incoming packet and forwards it directly out, we should not add a vlan
        # tag.
        full_policy = internal_strip_vlan_policy(slic, safe_inport_policy)

        policy_list.append(
            full_policy.get_physical_rep(slic.port_map, slic.node_map))
    return nc.nary_policy_union(policy_list)

def isolated_policy(policy, vlan):
    """Produce a policy for slic restricted to its vlan.

    ARGS:
        policy:  Policy to restrict
        vlan:  vlan id to restrict slic to

    RETURNS:
        a new policy object that is slic's policy but restricted to its vlan.
    """
    vlan_predicate = nc.Header('vlan', vlan)
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

def strip_vlan(policy, (switch, port)):
    """Re-write all actions of policy to set vlan to 0 on switch, port."""
    assert(isinstance(policy, netcore.Policy))
    if isinstance(policy, nc.PrimitivePolicy):
        # get a new copy of all the actions so we can safely modify them
        actions = copy.deepcopy(policy.actions)
        output_actions = []
        for action in actions:
            if action.switch == switch and port in action.ports:
                # Split ports into ports we need to change and ports we don't
                bad_ports = [port]
                good_ports = action.ports
                good_ports.remove(port)

                # Build new actions around these objects
                out_modify = dict(action.modify)
                out_modify['vlan'] = 0
                out_a = nc.Action(switch, bad_ports, out_modify)
                output_actions.append(out_a)
                if len(good_ports) > 0:
                    output_actions.append(action)
            else:
                # No need to modify it
                output_actions.append(action)
        return policy.predicate |then| output_actions
    elif isinstance(policy, nc.PolicyUnion):
        left = strip_vlan(policy.left, (switch, port))
        right = strip_vlan(policy.right, (switch, port))
        return left + right
    elif isinstance(policy, nc.PolicyRestriction):
        new_policy = strip_vlan(policy.policy, (switch, port))
        return new_policy % policy.predicate
    else:
        raise Exception("Unexpected policy: %s\n" % policy)

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
    assert(isinstance(slic, slicing.Slice))
    assert(isinstance(policy, netcore.Policy))
    external_predicates = [external_predicate(loc, pred)
                           for loc, pred in slic.edge_policy.iteritems()]
    predicate = nc.nary_union(external_predicates)
    policy_into_vlan = modify_vlan(policy, vlan)
    return nc.PolicyRestriction(policy_into_vlan, predicate)

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
