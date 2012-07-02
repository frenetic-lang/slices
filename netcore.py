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
# /updates/netcore.py                                                          #
# Netcore grammar objects and related functions                                #
################################################################################
"""Netcore grammar objects and related functions.

For convenience, here's the grammar:

Switch s

Observation obs

Port t      ::= int

Field f     ::= switch
              | port
              | srcmac
              | dstmac
              | ethtype
              | srcip
              | dstip
              | vlan
              | protocol
              | srcport
              | dstport

Value v     ::= int

Predicate d ::= Top
              | Bottom
              | Header({f: v})
   d1 + d2    | Union(d1, d2)
   d1 & d2    | Intersection(d1, d2)
   d1 - d2    | Difference(d1, d2)

Action a    ::= Action(s, p Set, {f: v}, obs)

Policy p    ::= BottomPolicy
  d |then| a  | PrimitivePolicy(d, a)
  p1 + p2     | PolicyUnion(p1, p2)
  p % d       | PolicyRestriction(p, d)

PolicyRestriction objects are never found in policies that have been reduced by
policy.reduce().
"""

from abc import ABCMeta, abstractmethod
import copy

# Two constants, one for quick lookups, one to have a canonical ordering.
HEADERS = ['switch',
           'port',
           'srcmac',
           'dstmac',
           'ethtype',
           'srcip',
           'dstip',
           'vlan',
           'protocol',
           'srcport',
           'dstport']
HEADER_FIELDS = set (HEADERS)

def simulate(policy, packet, (switch, port)):
    """Get resulting located packets, observations."""
    actions = policy.get_actions(packet, (switch, port))
    actions = [a for a in actions if a.switch == switch]
    observations = set()
    for a in actions:
        observations.update(a.obs)
    packets = set()
    for a in actions:
        packets.update(a.modify_packet(packet))
    return (packets, observations)

class Infix:
    """Class to define infix operators like |so|."""
    def __init__(self, function):
        self.function = function
    def __ror__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __or__(self, other):
        return self.function(other)
    def __rlshift__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __rshift__(self, other):
        return self.function(other)
    def __call__(self, value1, value2):
        return self.function(value1, value2)

class PhysicalException(Exception):
    """Exceptions during logical-to-physical mapping."""
    pass

class Packet:
    """A fully-defined, immutable network packet."""
    def __init__(self, fields):
        self._fields = fields

    def __getitem__(self, key):
        return self._fields[key]
    
    def items(self):
        return self._fields.items()
    
    def __hash__(self):
       return hash(tuple(sorted(self._fields.iteritems())))

    def __eq__(self, other):
        return self._fields == other._fields

class Predicate:
    """Top-level abstract class for predicates."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_physical_predicate(self, switch_map, port_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        pass

    @abstractmethod
    def match(self, packet, (switch, port)):
        """Does this header match this located packet?"""
        pass

    def __repr__(self):
        return self.__str__()

    @abstractmethod
    def reduce(self):
        """Return a copy with removed redundencies."""
        pass

    def is_bottom(self):
        return False

    def __add__(self, other):
        return Union(self, other)

    def __and__(self, other):
        return Intersection(self, other)

    def __sub__(self, other):
        return Difference(self, other)

# Primitive predicates

# Should these just be one class that holds a boolean?
class Top(Predicate):
    """The always-true predicate."""
    def __init__(self):
        pass

    def get_physical_predicate(self, switch_map, port_map):
        return Top()

    def match(self, packet, (switch, port)):
        return True

    def reduce(self):
        return Top()

    def __str__(self):
        return "Top"

    def __eq__(self, other):
        return isinstance(other, Top)

class Bottom(Predicate):
    """The always-false predicate."""
    def __init__(self):
        pass

    def get_physical_predicate(self, switch_map, port_map):
        return Bottom()

    def is_bottom(self):
        return True

    def match(self, packet, (switch, port)):
        return False

    def reduce(self):
        return Bottom()

    def __str__(self):
        return "Bottom"

    def __eq__(self, other):
        return isinstance(other, Bottom)

def inport(switch, ports):
    """Construct a predicate accepting packets on one or a list of ports."""
    if isinstance(ports, type([])):
        return nary_union([Header({'switch': switch, 'port': p}) for p in ports])
    else:
        return Header({'switch': switch, 'port': ports})

def intersect_headers(h1, h2):
    """Return the intersection of two headers.

    Since header fields are finite, we can easily compute their intersection
    piecewise on each field.

    * If a field is only present in one header or the other, just take it from
      that one.
    * If a field is present in both, and the same, copy it over
    * If a field is present in both, and different, return Bottom since no
      packet can match both headers, so the intersection of the two headers is
      empty

    For location fields, we do the same thing, but intersect the switch and port
    independently.
    """

    f1 = copy.copy(h1.fields)
    f2 = h2.fields
    for f, p2 in f2.items():
        if f in f1:
            p1 = f1[f]
            if p1 != p2:
                return Bottom()
            else: # they're equal, the value is already in f1
                pass
        else: # f not in f1, copy it over
            f1[f] = p2
    return Header(f1)

class Header(Predicate):
    """A predicate representing matching a header with a wildcard pattern.

    Matches a header against a wildcard.  Note that "header" fields also include
    switch and port fields.  See header_fields for a complete list
    """
    def __init__(self, fields):
        """
        ARGS:
            fields: {field: pattern}

        field: header field to match pattern against
        pattern: value to match.
        """
        self.fields = fields

    def __str__(self):
        return "Header: %s" % str(self.fields)

    def __eq__(self, other):
        return (isinstance(other, Header) and self.fields == other.fields)

    def reduce(self):
        return Header(self.fields)

    def get_physical_predicate(self, switch_map, port_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that the switch is mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        out_fields = {}
        for f, p in self.fields.items():
            if f == 'switch':
                out_fields[f] = switch_map[p]
            elif f == 'port':
                if not 'switch' in self.fields:
                    raise PhysicalException(
                        'cannot map a logical port on a wildcard switch')
                else:
                    # discard the switch
                    if p == 0:
                        # This is an end host, they don't get their ports mapped
                        out_fields[f] = p
                    else:
                        _, out_fields[f] = port_map[(self.fields['switch'], p)]
            else:
                # Matching on packet headers does not require mapping
                out_fields[f] = p
        return Header(out_fields)

    def match(self, packet, (switch, port)):
        """Does this header match this located packet?"""
        for f, pat in self.fields.items():
            if f == 'switch':
                if pat != switch:
                    return False
            elif f == 'port':
                if pat != port:
                    return False
            else:
                p = pat
                if p != packet[f]:
                    return False
        return True

# Compound predicates
class Union(Predicate):
    """A predicate representing the union of two predicates."""
    def __init__(self, left, right):
        """
        ARGS:
            left: first predicate to union
            right: second predicate to union
        """
        self.left = left
        self.right = right

    def __str__(self):
        left_s = str(self.left)
        right_s = str(self.right)
        left_lines  = ['|' + s for s in left_s.split('\n')]
        right_lines = ['|' + s for s in right_s.split('\n')]
        return "\n".join(["Union"] + left_lines + right_lines)

    def __eq__(self, other):
        return (isinstance(other, Union) and
                ((self.left == other.left and self.right == other.right) or
                 (self.right == other.left and self.left == other.right)))

    # TODO(astory): top-reduction over subcomponents
    def reduce(self):
        r_left = self.left.reduce()
        r_right = self.right.reduce()
        if isinstance(r_left, Top) or isinstance(r_right, Top):
            return Top()
        elif r_left.is_bottom():
            return r_right
        elif r_right.is_bottom():
            return r_left
        else:
            return r_left + r_right

    def get_physical_predicate(self, switch_map, port_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pred = self.left.get_physical_predicate(switch_map, port_map)
        r_pred = self.right.get_physical_predicate(switch_map, port_map)
        return Union(l_pred, r_pred)

    def match(self, packet, loc):
        return self.left.match(packet, loc) or self.right.match(packet, loc)

class Intersection(Predicate):
    """A predicate representing the intersection of two predicates."""
    def __init__(self, left, right):
        """
        ARGS:
            left: first predicate to intersection
            right: second predicate to intersection
        """
        self.left = left
        self.right = right

    def __str__(self):
        left_s = str(self.left)
        right_s = str(self.right)
        left_lines  = ['|' + s for s in left_s.split('\n')]
        right_lines = ['|' + s for s in right_s.split('\n')]
        return "\n".join(["Intersection"] + left_lines + right_lines)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (isinstance(other, Intersection) and
                ((self.left == other.left and self.right == other.right) or
                 (self.right == other.left and self.left == other.right)))

    def reduce(self):
        r_left = self.left.reduce()
        r_right = self.right.reduce()
        if r_left.is_bottom() or r_right.is_bottom():
            return Bottom()
        elif isinstance(r_left, Top):
            return r_right
        elif isinstance(r_right, Top):
            return r_left
        # We can compute smaller predicates by re-writing some intersections
        # The rule-of-thumb to follow is that if the transformation increases
        # the AST depth unless bottom or top reduction occurs, it's probably not
        # worth it.
        elif isinstance(r_left, Header) and isinstance(r_right, Header):
            # We can form the intersection manually.
            return intersect_headers(r_left, r_right)
        # This transformation does not increase the depth
        elif isinstance(r_left, Union) and isinstance(r_right, Header):
            u_left = (r_left.left & r_right).reduce()
            u_right = (r_left.right & r_right).reduce()
            return (u_left + u_right).reduce()
        elif isinstance(r_right, Union) and isinstance(r_left, Header):
            u_left = (r_right.left & r_left).reduce()
            u_right = (r_right.right & r_left).reduce()
            return (u_left + u_right).reduce()
        # If one side of the intersection is also an intersection, but didn't
        # reduce, we might get it to reduce by moving the other predicate over
        # to it, and it doesn't increase depth
        elif isinstance(r_left, Intersection) and isinstance(r_right, Header):
            i_left = (r_left.left & r_right).reduce()
            i_right = (r_left.right & r_right).reduce()
            return i_left & i_right
        elif isinstance(r_right, Intersection) and isinstance(r_left, Header):
            i_left = (r_right.left & r_left).reduce()
            i_right = (r_right.right & r_left).reduce()
            return (i_left & i_right).reduce()
        # Don't do union-union because that gets too combinatorically messy
        # Note that nary unions are produced with n-1 unions, so this should
        # traverse down them.
        elif isinstance(r_left, Difference) and isinstance(r_right, Header):
            d_left = (r_left.left & r_right).reduce()
            return (d_left - r_left.right).reduce()
        elif isinstance(r_right, Difference) and isinstance(r_left, Header):
            d_left = (r_right.left & r_left).reduce()
            return (d_left - r_right.right).reduce()
        else:
            return r_left & r_right

    def get_physical_predicate(self, switch_map, port_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pred = self.left.get_physical_predicate(switch_map, port_map)
        r_pred = self.right.get_physical_predicate(switch_map, port_map)
        return Intersection(l_pred, r_pred)

    def match(self, packet, loc):
        return self.left.match(packet, loc) and self.right.match(packet, loc)

class Difference(Predicate):
    """A predicate representing the difference of two predicates."""
    def __init__(self, left, right):
        """
        ARGS:
            left: set to subtract from
            right: set to subtract
        """
        self.left = left
        self.right = right

    def __str__(self):
        left_s = str(self.left)
        right_s = str(self.right)
        left_lines  = ['|' + s for s in left_s.split('\n')]
        right_lines = ['|' + s for s in right_s.split('\n')]
        return "\n".join(["Difference"] + left_lines + right_lines)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def reduce(self):
        r_left = self.left.reduce()
        r_right = self.right.reduce()
        if r_left.is_bottom() or isinstance(r_right, Top):
            return Bottom()
        elif r_right.is_bottom():
            return r_left
        elif isinstance(r_left, Header) and isinstance(r_right, Header):
            # if a field is in left, and is specified to something different in
            # right, then there are no packets that are restricted by the
            # difference, since no packets matched by left are matched by right
            total_match = True
            for f in r_right.fields:
                # don't deal with locations, they're too messy for now
                if (f in r_left.fields and
                        r_right.fields[f] != r_left.fields[f]):
                    # If left only matches packets with f:x, and right only
                    # matches packets with f:y, then right does not restrict
                    # left at all.  With a fixed field in right's predicate,
                    # this makes right _entirely_ useless, so there's no point
                    # in checking the rest.
                    return r_left
                elif (f in r_left.fields and
                        r_left.fields[f] == r_right.fields[f]):
                    pass
                else:
                    total_match = False
            if total_match:
                # Each field in right matches left, which means that right
                # matches all the packets left does (plus maybe more).  Thus, no
                # packets are in the difference, because there are no packets in
                # left that are not in right.
                return Bottom()
            else:
                return r_left - r_right
        else:
            return r_left - r_right

    def get_physical_predicate(self, switch_map, port_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pred = self.left.get_physical_predicate(switch_map, port_map)
        r_pred = self.right.get_physical_predicate(switch_map, port_map)
        return Difference(l_pred, r_pred)

    def match(self, packet, loc):
        return (self.left.match(packet, loc) and
                not self.right.match(packet, loc))

def nary_union(predicates):
    """Return a union of all predicates in predicates."""
    if len(predicates) == 0:
        return Bottom()
    else:
        base = predicates[0]
        return sum(predicates[1:], base)

def nary_intersection(predicates):
    """Return a intersection of all predicates in predicates."""
    if len(predicates) == 0:
        return Bottom()
    else:
        base = predicates[0]
        for predicate in predicates[1:]:
            base = Intersection(predicate, base)
        return base

def forward(switch, ports):
    """Construct an action to forward out ports on switch.

    ports may be a port number or a list of port numbers.
    """
    if isinstance(ports, int):
        ports = [ports]
    return Action(switch, ports=ports)

class Action:
    """Description of a forwarding action, with possible modification."""
    def __init__(self, switch, ports=set(), modify=dict(), obs=set()):
        """
        ARGS:
            switch: switch on which the ports live.
            ports: ports to which to forward packet
            modify: dictionary of header fields to values, fields that are set
                will overwrite the packet's fields
            obs: counters to increment when this action fires.
        """
        self.switch = switch
        self.ports = ports
        self.modify = modify
        self.obs = obs

    def __str__(self):
        return "%s: %s -%s-> %s" % (self.switch, self.modify,
                                    list(self.obs), list(self.ports))

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (isinstance(other, Action) and
            self.switch == other.switch and
            self.ports == other.ports and
            self.modify == other.modify)

    def modify_packet(self, packet):
        """Modify packet with this action's modify pattern.

        ARGS:
            packet: packet to modify

        RETURNS:
            list of new (packet, loc) with packet modified by this action's
            modify pattern at each output port of the pattern.
        """
        fields = dict(packet.items())
        fields.update(self.modify)
        packet = Packet(fields)
        lps = []
        for p in self.ports:
            lps.append((packet, (self.switch, p)))
        return lps

    def get_physical_rep(self, switch_map, port_map):
        """Return this action mapped to a physical network."""
        # Only return the port number, not the (switch, port) pair
        p_ports = [port_map[(self.switch, p)][1] for p in self.ports]
        return Action(switch_map[self.switch], p_ports, self.modify, self.obs)

class Policy:
    """Top-level abstract description of a static network program."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_physical_rep(self, switch_map, port_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        pass

    def __repr__(self):
        return self.__str__()

    @abstractmethod
    def get_actions(self, packet, loc):
        """Get set of actions this policy generates for a located packet."""
        pass

    def reduce(self):
        """Return copy with removed redundencies."""
        return self.__class__()

    def is_bottom(self):
        return False

    @abstractmethod
    def restrict(self, predicate):
        """Return this policy restricted by a predicate internally."""

    def __add__(self, other):
        return PolicyUnion(self, other)

    def __mod__(self, predicate):
        return PolicyRestriction(self, predicate)

class BottomPolicy(Policy):
    """Policy that drops everything."""
    def __init__(self):
        pass

    def get_physical_rep(self, switch_map, port_map):
        return self

    def get_actions(self, packet, loc):
        return []

    def is_bottom(self):
        return True

    def restrict(self, predicate):
        return BottomPolicy()

    def __str__(self):
        return "BottomPolicy"

    def __eq__(self, other):
        return isinstance(other, BottomPolicy)

def make_policy(predicate, action):
    """Construct a policy with one or more actions.

    Auto-converts action to a list if it is a solitary action.  Otherwise, pass
    whatever we got, and deal with the potential consequences.
    """
    if isinstance(action, Action):
        return PrimitivePolicy(predicate, [action])
    else:
        return PrimitivePolicy(predicate, action)

then = Infix(make_policy)

class PrimitivePolicy(Policy):
    """Policy for mapping a single predicate to a list of actions."""
    def __init__(self, predicate, actions):
        """
        ARGS:
            predicate: predicate under which to apply action
            actions: a list of Actions to apply to packets which match
                predicate.  Each action is applied to such a
                packet, first effecting any modifications in the action, then
                forwarding out any given ports, before applying the next
                action.  In this way, a PrimitivePolicy may result in multiple
                packets.  Note that actions may be the empty list.
        """
        self.predicate = predicate
        self.actions = actions

    def __str__(self):
        return "PrimitivePolicy\n|%s\n|%s" % (self.predicate, self.actions)

    def __eq__(self, other):
        return self.predicate == other.predicate and \
            self.actions == other.actions

    def reduce(self):
        if len(self.actions) == 0:
            return BottomPolicy()
        r_pred = self.predicate.reduce()
        if r_pred.is_bottom():
            return BottomPolicy()
        else:
            # Prefer direct constructor here for speed over clarity
            # same as r_pred |then| actions
            return PrimitivePolicy(r_pred, self.actions)

    def restrict(self, predicate):
        return (self.predicate & predicate) |then| self.actions

    def get_physical_rep(self, switch_map, port_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        p_pred = self.predicate.get_physical_predicate(switch_map, port_map)
        p_act = [action.get_physical_rep(switch_map, port_map)
                 for action in self.actions]
        return PrimitivePolicy(p_pred, p_act)

    def get_actions(self, packet, loc):
        if self.predicate.match(packet, loc):
            switch = loc[0]
            return [a for a in self.actions if a.switch == switch]
        else:
            return []

class PolicyUnion(Policy):
    """The union of two policies."""
    def __init__(self, left, right):
        """
        ARGS:
            left: first policy to union
            right: second policy to union
        """
        self.left = left
        self.right = right

    def __str__(self):
        left_s = str(self.left)
        right_s = str(self.right)
        left_lines  = ['|' + s for s in left_s.split('\n')]
        right_lines = ['|' + s for s in right_s.split('\n')]
        return "\n".join(["PolicyUnion"] + left_lines + right_lines)

    def reduce(self):
        r_left = self.left.reduce()
        r_right = self.right.reduce()
        if r_left.is_bottom():
            return r_right
        elif r_right.is_bottom():
            return r_left
        else:
            return r_left + r_right

    def restrict(self, predicate):
        r_left = self.left.restrict(predicate)
        r_right = self.right.restrict(predicate)
        return r_left + r_right

    def get_physical_rep(self, switch_map, port_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pol = self.left.get_physical_rep(switch_map, port_map)
        r_pol = self.right.get_physical_rep(switch_map, port_map)
        return PolicyUnion(l_pol, r_pol)

    def get_actions(self, packet, loc):
        left = self.left.get_actions(packet, loc)
        left.extend(self.right.get_actions(packet, loc))
        return left

def nary_policy_union(policies):
    """Take the union of many policies."""
    if len(policies) == 0:
        return BottomPolicy()
    else:
        base = policies[0]
        return sum(policies[1:], base)

class PolicyRestriction(Policy):
    """A policy restricted by a predicate.

    Note that a reduced policy NEVER contains restrictions since they are
    transformed into intersections.
    """
    def __init__(self, policy, predicate):
        """
        ARGS:
            policy: policy to restrict
            predicate: predicate to restrict it by
        """
        self.policy = policy
        self.predicate = predicate

    def __str__(self):
        left_s = str(self.policy)
        right_s = str(self.predicate)
        left_lines  = ['|' + s for s in left_s.split('\n')]
        right_lines = ['|' + s for s in right_s.split('\n')]
        return "\n".join(["PolicyRestriction"] + left_lines + right_lines)

    def reduce(self):
        r_pred = self.predicate.reduce()
        return self.policy.restrict(r_pred).reduce()

    def get_physical_rep(self, switch_map, port_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        switch_map: {l_switch: p_switch}
        port_map: {(l_switch, l_port): (p_switch, p_port)}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        pol = self.policy.get_physical_rep(switch_map, port_map)
        pred = self.predicate.get_physical_predicate(switch_map, port_map)
        return PolicyRestriction(pol, pred)

    def restrict(self, predicate):
        return self.policy.restrict(self.predicate & predicate)

    def get_actions(self, packet, loc):
        if self.predicate.match(packet, loc):
            return self.policy.get_actions(packet, loc)
        else:
            return []
