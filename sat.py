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

ONLY CHECK FOR UNSAT UNLESS YOU'RE MARK

No observations yet.
"""

from z3.z3 import And, Or, Not, Implies, Function, ForAll
from z3.z3 import Const, Consts, Solver, unsat, set_option, Int, Ints
from netcore import HEADERS
import netcore as nc

from util import fields_of_policy

set_option(pull_nested_quantifiers=True)

from sat_core import nary_or, nary_and
from sat_core import HEADER_INDEX, Packet, switch, port, vlan
from sat_core import forwards, forwards_with, observes, observes_with
from sat_core import input, output, ingress, egress
from sat_core import external_link, edges_ingress, on_valid_port
from verification import disjoint_observations

def transfer(topo, p_out, p_in):
    """Build constraint for moving p_out to p_in across an edge."""
    options = []
    for s1, s2 in topo.edges():
        p1 = topo.node[s1]['ports'][s2]
        p2 = topo.node[s2]['ports'][s1]
        # Need both directions because topo.edges() only gives one direction for
        # undirected graphs.
        constraint1 = And(And(switch(p_out) == s1, port(p_out) == p1),
                          And(switch(p_in) == s2, port(p_in) == p2))
        constraint2 = And(And(switch(p_out) == s2, port(p_out) == p2),
                          And(switch(p_in) == s1, port(p_in) == p1))
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

# TODO(astory): make sure this is rigorous.  I think it might have holes in it.
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
    constraint = Implies(forwards(policy1, p1_in, p1_out),
                         forwards(policy2, p1_in, p1_out))
    # Second, we want to ensure that if p2 forwards a packet, and it's a packet
    # that p1 can forward, that p2 only forwards it in ways that p1 does.
    constraint = And(constraint,
                     Implies(And(forwards(policy2, p2_in, p2_out1),
                                 forwards(policy1, p2_in, p2_out2)),
                             forwards(policy1, p2_in, p2_out1)))
    # We want to check for emptiness, so our model gives us a packet back
    s.add(Not(constraint))

    if s.check() == unsat:
        return None
    else:
        return (s.model(), (p1_in, p1_out, p2_in, p2_out1, p2_out2),
                HEADER_INDEX)

def not_empty(policy):
    """Determine if there are any packets that the policy forwards.

    RETURNS:
        None if not forwardable.
        (model, (p_in, p_out), HEADERS) if forwardable.
    """
    p_in, p_out = Consts('p_in p_out', Packet)
    s = Solver()
    s.add(forwards(policy, p_in, p_out))
    if s.check() == unsat:
        return None
    else:
        return (s.model(), (p_in, p_out), HEADER_INDEX)

def compiled_correctly(topo, orig, result, edge_policy={}):
    """Determine if result is a valid compilation of orig.

    Preconditions:
        Topo is the relevant topology
        orig is vlan-agnostic.  That is:
            ForAll v, simulates(orig, orig % {vlan: v})

    RETURNS: True or False.
    """
    return (simulates(topo, orig, result, edge_policy=edge_policy) and
            simulates(topo, result, orig) and
            one_per_edge(topo, result) is None)

def simulates(topo, a, b, field='vlan', edge_policy={}):
    """Determine if b simulates a up to field.
    
    This ensures all the observations, 1-hop and 2-hop paths are equivalent.  It
    DOES NOT ensure that b is a sane compilation; this requires that b only uses
    one vlan, but we don't want to fail in the general case where b might be the
    source, not the compilation target, so you need to check one_per_edge after
    calling this to ensure compilation correctness.
    """
    return (simulates_forwards(topo, a, b, field=field, edge_policy=edge_policy)
                is None and
            simulates_observes(topo, a, b, field=field, edge_policy=edge_policy)
                is None and
            simulates_forwards2(topo, a, b, field=field, edge_policy=edge_policy)
                is None)

def simulates_forwards(topo, a, b, field='vlan', edge_policy={}):
    """Determine if b simulates a up to field on one hop."""
    p, pp = Consts('p pp', Packet)
    v, vv = Ints('v vv')
    # Z3 emits a warning about not finding a pattern for our quantification.
    # This is fine, so ignore it.
    set_option('WARNING', False)

    solv = Solver()
    solv.add(on_valid_port(topo, p))

    # b doesn't need to forward packets on external links that don't satisfy the
    # ingress predicate
    edge_option = And(external_link(edge_policy, p),
                      Not(edges_ingress(edge_policy, p)))

    solv.add(And(forwards(a, p, pp),
             ForAll([v, vv], Not(Or(forwards_with(b, p, {field: v},
                                                     pp, {field: vv}),
                                    edge_option)),
                    patterns=[])))
    if solv.check() == unsat:
        set_option('WARNING', True)
        return None
    else:
        set_option('WARNING', True)
        return solv.model(), (p, pp), HEADER_INDEX

def simulates_observes(topo, a, b, field='vlan', edge_policy={}):
    p = Const('p', Packet)
    o, v = Ints('o v')
    # Z3 emits a warning about not finding a pattern for our quantification.
    # This is fine, so ignore it.
    set_option('WARNING', False)

    solv = Solver()

    solv.add(on_valid_port(topo, p))

    # b doesn't need to observe packets on external links that don't satisfy the
    # ingress predicate
    edge_option = And(external_link(edge_policy, p),
                      Not(edges_ingress(edge_policy, p)))

    solv.add(And(observes(a, p, o),
             ForAll([v], Not(Or(observes_with(b, p, {field: v}, o),
                                edge_option)),
                    patterns=[])))

    if solv.check() == unsat:
        set_option('WARNING', True)
        return None
    else:
        set_option('WARNING', True)
        return solv.model(), (p), HEADER_INDEX

def simulates_forwards2(topo, a, b, field='vlan', edge_policy={}):
    """Determine if b simulates a up to field on two hop on topo."""
    p, pp, q, qq = Consts('p pp q qq', Packet)
    v, vv, vvv = Ints('v vv, vvv')
    # Z3 emits a warning about not finding a pattern for our quantification.
    # This is fine, so ignore it.
    set_option('WARNING', False)

    solv = Solver()

    solv.add(on_valid_port(topo, p))

    # b doesn't need to forward packets on external links that don't satisfy the
    # ingress predicate, but we only care about the first hop
    edge_option = And(external_link(edge_policy, p),
                      Not(edges_ingress(edge_policy, p)))

    # This case breaks the And inside the ForAll because they're both False and
    # z3 can't handle that.  
    # However, it does mean that they simulate each other, because neither
    # forwards packets, so just short-circuit.
    if forwards(b, p, pp) is False and forwards(b, q, qq) is False:
        return None
    c = And(forwards(a, p, pp), transfer(topo, pp, q), forwards(a, q, qq),
            ForAll([v, vv, vvv],
                   Not(Or(And(forwards_with(b, p, {field: v}, pp, {field: vv}),
                              forwards_with(b, q, {field: vv}, qq, {field: vvv})),
                          edge_option)))

           )

    solv.add(c)
    if solv.check() == unsat:
        set_option('WARNING', True)
        return None
    else:
        set_option('WARNING', True)
        return solv.model(), (p, pp), HEADER_INDEX

def one_per_edge(topo, pol, field='vlan'):
    """Determine if pol only uses one value of field on each internal edge.
    
    We don't care about external edges because they never have the problem of
    preventing tiling of two-node connectivity since this slice never reads
    packets sent to them.
    """

    p, pp, q, qq = Consts('p pp q qq', Packet)
    r, rr, s, ss = Consts('r rr s ss', Packet)

    solv = Solver()
    solv.add(forwards(pol, p, pp))
    solv.add(transfer(topo, pp, r))
    solv.add(forwards(pol, r, rr))
    solv.add(forwards(pol, q, qq))
    solv.add(switch(pp) == switch(qq))
    solv.add(port(pp) == port(qq))
    solv.add(HEADER_INDEX[field](pp) != HEADER_INDEX[field](qq))
    if solv.check() == unsat:
        return None
    else:
        return solv.model(), (p, pp), HEADER_INDEX

def separate(topo, policy1, policy2):
    return (shared_io(topo, policy1, policy2) is None) and\
           (shared_io(topo, policy2, policy1) is None) and\
           (shared_inputs(policy1, policy2) is None) and\
           (shared_inputs(policy2, policy1) is None) and\
           (shared_outputs(policy1, policy2) is None) and\
           (shared_outputs(policy2, policy1) is None)

def unshared_portals(topo, policy1, policy2):
    return (disjoint_observations(policy1, policy2) and
            shared_transit(topo, policy1, policy2) is None)

def shared_io(topo, policy1, policy2):
    """Try to find output of policy1 in the inputs of policy2."""
    p, pp, q, qq = Consts('p pp q qq', Packet)
    o = Int('o')

    solv = Solver()
    solv.add(output(policy1, p, pp))
    solv.add(transfer(topo, pp, q))
    solv.add(input(policy2, q, qq, o))

    if solv.check() == unsat:
        return None
    else:
        return solv.model(), (p, pp, q, qq), HEADER_INDEX

def shared_inputs(policy1, policy2):
    """Try to find packet in input of policy1 and ingress of policy2."""
    p, pp, qq = Consts('p pp qq', Packet)
    o, n = Ints('o n')

    solv = Solver()
    solv.add(input(policy1, p, pp, o))
    solv.add(ingress(policy2, p, qq, n))

    if solv.check() == unsat:
        return None
    else:
        return solv.model(), (p, pp, qq), HEADER_INDEX

def shared_outputs(policy1, policy2):
    """Try to find packet in output of policy1 and egress of slice2."""
    p, q, pp = Consts('p q pp', Packet)

    solv = Solver()
    solv.add(output(policy1, p, pp))
    solv.add(egress(policy2, q, pp))

    if solv.check() == unsat:
        return None
    else:
        return solv.model(), (p, pp), HEADER_INDEX

# TODO(astory): test!
def shared_transit(topo, policy1, policy2):
    """Try to find packet in the border of policy1 and the border of policy2.
    
    Note that this is symmetric.
    """
    p, pp, ppp, qq, qqq = Consts('p pp ppp qq qqq', Packet)
    o, n = Ints('o n')

    solv = Solver()
    # Predicates are focused on a packet p, all other packets are fodder for
    # that one.  We want an input packet p or an output packet after a hop p in
    # each case.
    solv.add(Or(ingress(policy1, p, pp, o),
                And(egress(policy1, pp, ppp),
                    transfer(topo, ppp, p))))
    solv.add(Or(ingress(policy2, p, qq, n),
                And(egress(policy2, qq, qqq),
                    transfer(topo, qqq, p))))

    if solv.check() == unsat:
        return None
    else:
        return solv.model(), (p,), HEADER_INDEX
