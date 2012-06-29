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
from z3.z3 import Consts, ForAll, Exists, Int, Implies, Datatype, BitVecSort
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

FIELD_SORTS = {
               'switch': IntSort(),
               'port': IntSort(),
               'srcmac': BitVecSort(48),
               'dstmac': BitVecSort(48),
               'ethtype': BitVecSort(16),
               'srcip': BitVecSort(32),
               'dstip': BitVecSort(32),
               'vlan': BitVecSort(8),
               'protocol': BitVecSort(8),
               'srcport': BitVecSort(16),
               'dstport': BitVecSort(16),
              }
def make_qpacket(fields):
    """Construct a quantifier-safe packet type that only considers fields.

    Note that fields are set in the order given, so keep that in mind if you're
    debugging models.
    """
    # Packet type to use for predicates containing quantifiers.  Much slower.
    decls = [(field, FIELD_SORTS[field]) for field in fields]

    QPacket = Datatype('Packet')
    QPacket.declare('build', *decls)
    QPacket = QPacket.create()

    headers = dict([(field, getattr(QPacket, field)) for field in fields])

    return QPacket, headers

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

def equiv_modulo(fields, p1, p2, headers):
    """Return a predicate testing if p1 and p2 are equivalent up to fields.

    Uses headers to test equality."""
    constraints = []
    for h in headers:
        if h not in fields:
            constraints.append(headers[h](p1) == headers[h](p2))

    return nary_and(constraints)

def match_of_predicate(pred, pkt, headers):
    """Build the constraint for pred on pkt."""
    if isinstance(pred, nc.Top):
        return True
    elif isinstance(pred, nc.Bottom):
        return False
    elif isinstance(pred, nc.Header):
        # Default to accepting, since the blank header accepts everything.
        constraints = []
        for field, value in pred.fields.items():
            constraints.append(headers[field](pkt) == value)
        return nary_and(constraints)
    elif isinstance(pred, nc.Union):
        left = match_of_predicate(pred.left, pkt, headers)
        right = match_of_predicate(pred.right, pkt, headers)
        return Or(left, right)
    elif isinstance(pred, nc.Intersection):
        left = match_of_predicate(pred.left, pkt, headers)
        right = match_of_predicate(pred.right, pkt, headers)
        return And(left, right)
    elif isinstance(pred, nc.Difference):
        left = match_of_predicate(pred.left, pkt, headers)
        right = match_of_predicate(pred.right, pkt, headers)
        return And(left, Not(right))

# TODO(astory): observations
def modify_packet(action, p_in, p_out, headers):
    """Build the constraint for action producing p_out from p_in."""
    ports = action.ports
    modify = action.modify
    obs = action.obs

    constraints = []
    constraints.append(headers['switch'](p_in) == action.switch)
    constraints.append(headers['switch'](p_out) == action.switch)

    port_constraints = []
    for p in ports:
        port_constraints.append(headers['port'](p_out) == p)
    # Note that if there are no ports, port_constraints is empty, so we get
    # False back:  drop the packet, no packet can match.
    constraints.append(nary_or(port_constraints))

    for h in headers:
        if h is not 'switch' and h is not 'port':
            # If a h is not modified, it must remain constant across both
            # packets.
            if h not in modify:
                pass
            else:
                constraints.append(headers[h](p_out) == modify[h])
    constraints.append(equiv_modulo(modify.keys() + ['switch', 'port'],
                                    p_in, p_out, headers))

    # We add at least two constraints, so constraints is never empty.
    return nary_and(constraints)

def match_of_policy(policy, packet, test_forward=False, headers=HEADER_INDEX):
    """Determine if policy matches a packet.

    if test_forward=True, also verify that it doesn't just drop the packet even
    if it matches.

    headers is the dictionary of header lookup functions.  Defaults to
    non-quantified packets.
    """
    if isinstance(policy, nc.BottomPolicy):
        # No forwarding happens, fail immediately (unless there's a union above
        # us, in which case the Or takes care of it)
        return False
    elif isinstance(policy, nc.PrimitivePolicy):
        pred = policy.predicate
        if test_forward:
            actions = policy.actions
            # If the predicate matches, any one of the actions may fire.
            return And(match_of_predicate(pred, packet), len(actions) > 0)
        return match_of_predicate(pred, packet, headers)
    elif isinstance(policy, nc.PolicyUnion):
        left = policy.left
        right = policy.right
        return Or(match_of_policy(left, packet, test_forward, headers),
                  match_of_policy(right, packet, test_forward, headers))
    elif isinstance(policy, nc.PolicyRestriction):
        subpolicy = policy.policy
        pred = policy.predicate
        return And(match_of_policy(subpolicy, packet, test_forward, headers),
                   match_of_predicate(pred, packet, headers))
    else:
        raise Exception('unknown policy type: %s' % policy.__class__)

def forwards(policy, p_in, p_out, headers=HEADER_INDEX):
    """Build constraint for policy producing p_in from p_out in one hop.

    headers is the dictionary of header lookup functions.  Defaults to
    non-quantified packets.
    """
    if isinstance(policy, nc.BottomPolicy):
        # No forwarding happens, fail immediately (unless there's a union above
        # us, in which case the Or takes care of it)
        return False
    elif isinstance(policy, nc.PrimitivePolicy):
        pred = policy.predicate
        actions = policy.actions
        # If the predicate matches, any one of the actions may fire.
        action_constraints = nary_or([modify_packet(a, p_in, p_out, headers)
                                      for a in actions])
        # Use and here rather than implies because if the input packet doesn't
        # match, we don't want the rule to fire - without this, we can get
        # really weird behavior if the predicate is false over a packet, since
        # False -> x for all x
        return And(match_of_predicate(pred, p_in, headers), action_constraints)
    elif isinstance(policy, nc.PolicyUnion):
        left = policy.left
        right = policy.right
        return Or(forwards(left, p_in, p_out, headers),
                  forwards(right, p_in, p_out, headers))
    elif isinstance(policy, nc.PolicyRestriction):
        subpolicy = policy.policy
        pred = policy.predicate
        return And(forwards(subpolicy, p_in, p_out, headers),
                   match_of_predicate(pred, p_in, headers))
    else:
        raise Exception('unknown policy type: %s' % policy.__class__)
