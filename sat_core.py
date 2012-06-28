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

from z3.z3 import And, Or, Not, Function, DeclareSort, IntSort
from netcore import HEADERS
import netcore as nc

HEADERS= ['switch', 'port', 'vlan']

Packet = DeclareSort('Packet')

HEADER_INDEX = {}
for h in HEADERS:
    HEADER_INDEX[h] = Function(h, Packet, IntSort())

def nary_or(constraints):
    if len(constraints) < 1:
        return False
    if len(constraints) == 1:
        return constraints[0]
    else:
        return Or(constraints[0], nary_or(constraints[1:]))

def nary_and(constraints):
    if len(constraints) < 1:
        return True
    if len(constraints) == 1:
        return constraints[0]
    else:
        return And(constraints[0], nary_and(constraints[1:]))

def match_of_predicate(pred, pkt):
    """Build the constraint for pred on pkt."""
    if isinstance(pred, nc.Top):
        return True
    elif isinstance(pred, nc.Bottom):
        return False
    elif isinstance(pred, nc.Header):
        # Default to accepting, since the blank header accepts everything.
        constraints = []
        for field, value in pred.fields.items():
            constraints.append(HEADER_INDEX[field](pkt) == value)
        return nary_and(constraints)
    elif isinstance(pred, nc.Union):
        left = match_of_predicate(pred.left, pkt)
        right = match_of_predicate(pred.right, pkt)
        return Or(left, right)
    elif isinstance(pred, nc.Intersection):
        left = match_of_predicate(pred.left, pkt)
        right = match_of_predicate(pred.right, pkt)
        return And(left, right)
    elif isinstance(pred, nc.Difference):
        left = match_of_predicate(pred.left, pkt)
        right = match_of_predicate(pred.right, pkt)
        return And(left, Not(right))

# TODO(astory): observations
def modify_packet(action, p_in, p_out):
    """Build the constraint for action producing p_out from p_in."""
    ports = action.ports
    modify = action.modify
    obs = action.obs

    constraints = []
    constraints.append(HEADER_INDEX['switch'](p_in) == action.switch)
    constraints.append(HEADER_INDEX['switch'](p_out) == action.switch)

    port_constraints = []
    for p in ports:
        port_constraints.append(HEADER_INDEX['port'](p_out) == p)
    # Note that if there are no ports, port_constraints is empty, so we get
    # False back:  drop the packet, no packet can match.
    constraints.append(nary_or(port_constraints))

    for h in HEADERS:
        if h is not 'switch' and h is not 'port':
            # If a h is not modified, it must remain constant across both
            # packets.
            if h not in modify:
                constraints.append(HEADER_INDEX[h](p_in) ==
                                   HEADER_INDEX[h](p_out))
            else:
                constraints.append(HEADER_INDEX[h](p_out) == modify[h])

    # We add at least two constraints, so constraints is never empty.
    return nary_and(constraints)

def match_of_policy(policy, p_in, p_out):
    """Build constraint for policy producing p_in from p_out in one hop."""
    if isinstance(policy, nc.BottomPolicy):
        # No forwarding happens, fail immediately (unless there's a union above
        # us, in which case the Or takes care of it)
        return False
    elif isinstance(policy, nc.PrimitivePolicy):
        pred = policy.predicate
        actions = policy.actions
        # If the predicate matches, any one of the actions may fire.
        action_constraints = nary_or([modify_packet(a, p_in, p_out)
                                      for a in actions])
        # Use and here rather than implies because if the input packet doesn't
        # match, we don't want the rule to fire - without this, we can get
        # really weird behavior if the predicate is false over a packet, since
        # False -> x for all x
        return And(match_of_predicate(pred, p_in), action_constraints)
    elif isinstance(policy, nc.PolicyUnion):
        left = policy.left
        right = policy.right
        return Or(match_of_policy(left, p_in, p_out),
                  match_of_policy(right, p_in, p_out))
    elif isinstance(policy, nc.PolicyRestriction):
        subpolicy = policy.policy
        pred = policy.predicate
        return And(match_of_policy(subpolicy, p_in, p_out),
                   match_of_predicate(pred, p_in))
    else:
        raise Exception('unknown policy type: %s' % policy.__class__)
