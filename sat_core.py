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
# /slices/sat-core.py                                                          #
# Sat conversion for netcore.                                                  #
################################################################################

from z3.z3 import And, Or, Not, Function, DeclareSort, IntSort, BoolSort
from z3.z3 import Consts, ForAll, Exists, Int, Implies
from netcore import HEADERS
import netcore as nc

# Packet type to use for simple predicates that do not have quantifiers in them.
Packet = DeclareSort('Packet')

HEADER_INDEX = {}
for h in HEADERS:
    HEADER_INDEX[h] = Function(h, Packet, IntSort())

switch = HEADER_INDEX['switch']
port = HEADER_INDEX['port']
vlan = HEADER_INDEX['vlan']

def nary_or(constraints):
    if len(constraints) < 1:
        return False
    else:
        return Or(*constraints)

def nary_and(constraints):
    if len(constraints) < 1:
        return True
    else:
        return And(*constraints)

def on_valid_port(topo, packet):
    constraints = []
    for node in topo.nodes():
        for p in topo.node[node]['port']:
            constraints.append(And(switch(packet) == node,
                                   port(packet) == p))
    return nary_or(constraints)

def equiv_modulo(fields, p1, p2):
    """Return a predicate testing if p1 and p2 are equivalent up to fields.

    Uses headers to test equality."""
    constraints = []
    for h in HEADER_INDEX:
        if h not in fields:
            constraints.append(HEADER_INDEX[h](p1) == HEADER_INDEX[h](p2))

    return nary_and(constraints)

def match(pred, pkt):
    """Build the constraint for pred matching pkt."""
    return match_with(pred, pkt, {})

def match_with(pred, pkt, mods):
    """Build the constraint for pred matching pkt."""
    if isinstance(pred, nc.Top):
        return True
    elif isinstance(pred, nc.Bottom):
        return False
    elif isinstance(pred, nc.Header):
        # Default to accepting, since the blank header accepts everything.
        constraints = []
        for field, value in pred.fields.items():
            if field in mods:
                constraints.append(mods[field] == value)
            else:
                constraints.append(HEADER_INDEX[field](pkt) == value)
        return nary_and(constraints)
    elif isinstance(pred, nc.Union):
        left = match_with(pred.left, pkt, mods)
        right = match_with(pred.right, pkt, mods)
        return Or(left, right)
    elif isinstance(pred, nc.Intersection):
        left = match_with(pred.left, pkt, mods)
        right = match_with(pred.right, pkt, mods)
        return And(left, right)
    elif isinstance(pred, nc.Difference):
        left = match_with(pred.left, pkt, mods)
        right = match_with(pred.right, pkt, mods)
        return And(left, Not(right))

def modify_packet(action, p_in, in_mods, p_out, out_mods):
    """Build the constraint for action producing p_out from p_in."""
    ports = action.ports
    modify = action.modify

    constraints = []
    if 'switch' in in_mods:
        constraints.append(in_mods['switch'] == action.switch)
    else:
        constraints.append(HEADER_INDEX['switch'](p_in) == action.switch)
    if 'switch' in out_mods:
        constraints.append(out_mods['switch'] == action.switch)
    else:
        constraints.append(HEADER_INDEX['switch'](p_out) == action.switch)

    port_constraints = []
    for p in ports:
        if 'port' in out_mods:
            port_constriants.append(out_mods['port'] == p)
        else:
            port_constraints.append(HEADER_INDEX['port'](p_out) == p)
    # Note that if there are no ports, port_constraints is empty, so we get
    # False back:  drop the packet, no packet can match.
    constraints.append(nary_or(port_constraints))

    for h in HEADER_INDEX:
        if h is not 'switch' and h is not 'port':
            # If a h is not modified, it must remain constant across both
            # packets.
            if h not in modify:
                if h in in_mods:
                    v_in = in_mods[h]
                else:
                    v_in = HEADER_INDEX[h](p_in)
                if h in out_mods:
                    v_out = out_mods[h]
                else:
                    v_out = HEADER_INDEX[h](p_out)
                constraints.append(v_in == v_out)
            else:
                if h in out_mods:
                    constraints.append(out_mods[h] == modify[h])
                else:
                    constraints.append(HEADER_INDEX[h](p_out) == modify[h])

    # We add at least two constraints, so constraints is never empty.
    return nary_and(constraints)

def observe_packet(action, packet, mods, obv):
    """Build the constraint for action observing obv from packet."""
    obs = action.obs

    constraints = []
    if 'switch' in mods:
        constraints.append(mods['switch'] == action.switch)
    else:
        constraints.append(HEADER_INDEX['switch'](packet) == action.switch)

    obv_constraints = []
    for o in obs:
        obv_constraints.append(obv == o)
    constraints.append(nary_or(obv_constraints))

    # We add at least two constraints, so constraints is never empty.
    return nary_and(constraints)

def forwards(policy, p_in, p_out):
    return forwards_with(policy, p_in, {}, p_out, {})

def forwards_with(policy, p_in, in_mods, p_out, out_mods):
    """Build constraint for policy producing p_out from p_in in one hop.

    Modifies p_in with all the fields in in_mods
    Modifies p_out with all the fields in out_mods
    """
    if isinstance(policy, nc.BottomPolicy):
        # No forwarding happens, fail immediately (unless there's a union above
        # us, in which case the Or takes care of it)
        return False
    elif isinstance(policy, nc.PrimitivePolicy):
        pred = policy.predicate
        actions = policy.actions
        # If the predicate matches, any one of the actions may fire.
        action_constraints = nary_or([modify_packet(a, p_in, in_mods,
                                                    p_out, out_mods)
                                      for a in actions])
        # Use and here rather than implies because if the input packet doesn't
        # match, we don't want the rule to fire - without this, we can get
        # really weird behavior if the predicate is false over a packet, since
        # False -> x for all x
        return And(match_with(pred, p_in, in_mods),
                   action_constraints)
    elif isinstance(policy, nc.PolicyUnion):
        left = policy.left
        right = policy.right
        return Or(forwards_with(left, p_in, in_mods, p_out, out_mods),
                  forwards_with(right, p_in, in_mods, p_out, out_mods))
    elif isinstance(policy, nc.PolicyRestriction):
        subpolicy = policy.policy
        pred = policy.predicate
        return And(forwards_with(subpolicy, p_in, in_mods, p_out, out_mods),
                   match_with(pred, p_in, in_mods))
    else:
        raise Exception('unknown policy type: %s' % policy.__class__)

def observes(policy, packet, observations):
    return observes_with(policy, packet, {}, observations)

def observes_with(policy, packet, mods, obs):
    """Build constraint for policy observing observations from p_in in one hop.

    Modifies packet with all the fields in mods
    """
    if isinstance(policy, nc.BottomPolicy):
        # No observing happens, fail immediately (unless there's a union above
        # us, in which case the Or takes care of it)
        return False
    elif isinstance(policy, nc.PrimitivePolicy):
        pred = policy.predicate
        actions = policy.actions
        # If the predicate matches, any one of the actions may fire.
        action_constraints = nary_or([observe_packet(a, packet, mods, obs)
                                      for a in actions])
        # Use and here rather than implies because if the input packet doesn't
        # match, we don't want the rule to fire - without this, we can get
        # really weird behavior if the predicate is false over a packet, since
        # False -> x for all x
        return And(match_with(pred, packet, mods), action_constraints)
    elif isinstance(policy, nc.PolicyUnion):
        left = policy.left
        right = policy.right
        return Or(observes_with(left, packet, mods, obs),
                  observes_with(right, packet, mods, obs))
    elif isinstance(policy, nc.PolicyRestriction):
        subpolicy = policy.policy
        pred = policy.predicate
        return And(observes_with(subpolicy, packet, mods, obs),
                   match_with(pred, packet, mods))
    else:
        raise Exception('unknown policy type: %s' % policy.__class__)

def external_link(edge_policy, packet):
    """Build predicate for being on an external link."""
    constraints = []
    for ((s, p), predicate) in edge_policy.items():
        constraints.append(And(switch(packet) == s, port(packet) == p))
    return nary_or(constraints)

def edges_ingress(edge_policy, packet, mods={}):
    """Build predicate for packet being in the ingress set as defined.
    
    Mods don't work on switch and port yet.
    """
    constraints = []
    for ((s, p), predicate) in edge_policy.items():
        constraints.append(And(switch(packet) == s,
                               port(packet) == p,
                               match_with(predicate, packet, mods)))
    return nary_or(constraints)

def input(policy, packet, output, obs):
    """Build constriant for packet being in the input of policy."""
    fwrd = forwards(policy, packet, output)
    obsv = observes(policy, packet, obs)
    # Work around z3 limitation where you can't Or(False, False).
    # NOTE: z3 overloads the equality operator, but is is safe for True/False.
    if (fwrd is False) and (obsv is False):
        return False
    else:
        return Or(fwrd, obsv)

def output(policy, in_packet, packet):
    """Build constraint for packet being in the output of policy."""
    return forwards(policy, in_packet, packet)

def ingress(policy, packet, output, obs):
    """Build constriant for a packet being in the ingress set of the policy.

    Note that this differs from the paper definition in that it's not one hop
    across the topology.
    """
    return And(vlan(packet) == 0, input(policy, packet, output, obs))

def egress(policy, in_packet, packet):
    """Build constriant for a packet being in the egress set of the policy.

    Note that this differs from the paper definition in that it's not one hop
    across the topology.
    """
    return And(vlan(packet) == 0, output(policy, in_packet, packet))
