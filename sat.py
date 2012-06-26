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
# /slices/sat.py                                                               #
# Sat conversion and solving for netcore.                                      #
################################################################################
"""Sat conversion and solving for netcore.

No observations yet.
"""

from z3.z3 import And, Or, Not, Implies, Function, DeclareSort, IntSort
from z3.z3 import Consts, Solver, unsat
from netcore import HEADERS
import netcore as nc

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
        return False
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
        constraints = [True] if len(pred.fields) == 0 else []
        for field, value in pred.fields.items():
            constraints.append(HEADER_INDEX[field](pkt) == value)
        # Never empty, so never completely false.
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

def transfer(topo, p_out, p_in):
    """Build constraint for moving p_out to p_in across an edge."""
    options = []
    for s1, s2 in topo.edges():
        p1 = topo.node[s1]['ports'][s2]
        p2 = topo.node[s2]['ports'][s1]
        # Need both directions because topo.edges() only gives one direction for
        # undirected graphs.
        constraint1 = And(And(HEADER_INDEX['switch'](p_out) == s1,
                              HEADER_INDEX['port'](p_out) == p1),
                          And(HEADER_INDEX['switch'](p_in) == s2,
                              HEADER_INDEX['port'](p_in) == p2))
        constraint2 = And(And(HEADER_INDEX['switch'](p_out) == s2,
                              HEADER_INDEX['port'](p_out) == p2),
                          And(HEADER_INDEX['switch'](p_in) == s1,
                              HEADER_INDEX['port'](p_in) == p1))
        options.append(constraint1)
        options.append(constraint2)
    forward = nary_or(options)

    # We also need to ensure that the rest of the packet is the same.  Without
    # this, packet properties can change in flight.
    header_constraints = []
    for f in HEADERS:
        if f is not 'switch' and f is not 'port':
            header_constraints.append(
                    HEADER_INDEX[f](p_out) == HEADER_INDEX[f](p_in))
    # header_constraints is never empty
    return And(forward, nary_and(header_constraints))

def explain(model, packet, headers):
    """Build {field: value} from model, packet and {field: function}."""
    properties = {}
    for f, v in headers.items():
        prop = model.evaluate(v(packet))
        # This is dirty, but this seems to be the only way to tell if
        # this value is determined or not
        if 'as_long' in dir(prop):
            properties[f] = int(prop.as_long())
        else: # Value not determined
            pass
    return properties

def equivalent(policy1, policy2):
    """Determine if policy1 is equivalent to policy2 under equality.

    Note that this is unidirectional, it only asks if the packets that can go
    into policy1 behave the same under policy1 as they do under policy2.
    """
    p1_in, p1_out = Consts('p1_in p1_out', Packet)
    p2_in, p2_out1, p2_out2 = Consts('p2_in p2_out1 p2_out2', Packet)
    s = Solver()
    # There are two components to this.  First, we want to ensure that if p1
    # forwards a packet, p2 also forwards it
    constraint = Implies(match_of_policy(policy1, p1_in, p1_out),
                         match_of_policy(policy2, p1_in, p1_out))
    # Second, we want to ensure that if p2 forwards a packet, and it's a packet
    # that p1 can forward, that p2 only forwards it in ways that p1 does.
    constraint = And(constraint,
                     Implies(And(match_of_policy(policy2, p2_in, p2_out1),
                                 match_of_policy(policy1, p2_in, p2_out2)),
                             match_of_policy(policy1, p2_in, p2_out1)))
    # We want to check for emptiness, so our model gives us a packet back
    s.add(Not(constraint))

    if s.check() == unsat:
        return None
    else:
#       explanations = [str(explain(s.model(), p, HEADER_INDEX))
#                       for p in (p1_in, p1_out, p2_in, p2_out1, p2_out2)]
        return (s.model(), (p1_in, p1_out, p2_in, p2_out1, p2_out2),
                HEADER_INDEX)

def isolated(topo, policy1, policy2):
    """Determine if policy1 is isolated from policy2.

    RETURNS: True or False
    """
    return isolated_model(topo, policy1, policy2) is None

def isolated_diagnostic(topo, policy1, policy2):
    """Determine if policy1 is isolated from policy2.

    RETURNS: The empty string if they are isolated, or a diagnostic string
        detailing what packets will break isolation if they are not.
    """

    solution = isolated_model(topo, policy1, policy2)
    if solution is None:
        return ''
    else:
        (model, (p1, p2, p3, p4), hs) = solution
        properties = {}
        for p in (p1, p2, p3, p4):
            properties[p] = explain(model, p, hs)
    return ('%s\n'
            '---policy1--->\n'
            '%s\n'
            '---topology-->\n'
            '%s\n'
            '---policy2--->\n'
            '%s'
            % (properties[str(p1)], properties[str(p2)],
               properties[str(p3)], properties[str(p4)]))

def isolated_model(topo, policy1, policy2):
    """Determine if policy1 can produce a packet that goes to policy2.

    RETURNS: None if the policies are isolated
             (model, (pkt1, pkt2, pkt3, pkt4), HEADER_INDEX) if they are not

    The idea here is that if

    \exists pkt1, pkt2, pkt3, pkt4 . P1(pkt1, pkt2) and
                                     transfer(pkt2, pkt3) and
                                     P2(pkt3, pkt4)

    is inhabited, then they're not isolated.

    If you want to get back the problematic packets, evaluate the HEADER_INDEX
    functions in the model on the packets.
    """
    pkt1, pkt2, pkt3, pkt4 = Consts('pkt1 pkt2 pkt3 pkt4', Packet)
    s = Solver()
    s.add(match_of_policy(policy1, pkt1, pkt2))
    s.add(transfer(topo, pkt2, pkt3))
    s.add(match_of_policy(policy2, pkt3, pkt4))

    if s.check() == unsat:
        return None
    else:
        return (s.model(), (pkt1, pkt2, pkt3, pkt4), HEADER_INDEX)
