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
"""Netcore grammar objects and related functions."""

from abc import ABCMeta, abstractmethod
import copy

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
    """A fully-defined network packet, for testing purposes."""
    def __init__(self, fields):
        self.fields = fields

    def __getitem__(self, key):
        return self.fields[key]

    def __eq__(self, other):
        return self.fields == other.fields

class Predicate:
    """Top-level abstract class for predicates."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

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

    def get_physical_predicate(self, port_map, switch_map):
        return Top()

    def match(self, packet, (switch, port)):
        return True

    def __str__(self):
        return "Top"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, Top)

class Bottom(Predicate):
    """The always-false predicate."""
    def __init__(self):
        pass

    def get_physical_predicate(self, port_map, switch_map):
        return Bottom()

    def match(self, packet, (switch, port)):
        return False

    def __str__(self):
        return "Bottom"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, Bottom)


HEADER_FIELDS = set (['loc', # See Header for special note about this value
                      'srcmac',
                      'dstmac',
                      'ethtype',
                      'srcip',
                      'dstip',
                      'vlan',
                      'protocol',
                      'srcport',
                      'dstport'])

def inport(switch, ports):
    """Construct a predicate accepting packets on one or a list of ports."""
    if isinstance(ports, type([])):
        return nary_union([Header('loc', (switch, p)) for p in ports])
    else:
        return Header('loc', (switch, ports))

class Header(Predicate):
    """A predicate representing matching a header with a wildcard pattern.

    Matches a header against a wildcard.  Note that "header" fields also include
    switch and port fields.  See header_fields for a complete list
    """
    def __init__(self, field, pattern):
        """
       ARGS:
            field: header field to match pattern against
            pattern: (possibly) wildcarded bitstring, except in the case of loc,
                where it's (switch, port), where both are ints, with 0
                representing a wildcard.
        """
        assert(field in HEADER_FIELDS)
        if field == 'loc':
            assert(len(pattern) == 2)
        self.field = field
        self.pattern = pattern

    def __str__(self):
        return "%s : %s" % (self.field, self.pattern)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (isinstance(other, Header) and
            self.field == other.field and
            self.pattern == other.pattern)

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that the switch is mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        if self.field == 'loc':
            l_switch, l_port = self.pattern
            if l_switch == 0:
                if not l_port == 0:
                    raise PhysicalException(
                        'cannot map a logical port on a wildcard switch')
                else:
                    return Header('loc', (0, 0))
            else:
                switch = switch_map[l_switch]
                if l_port == 0:
                    return Header('loc', (switch, 0))
                else:
                    _, port = port_map[(l_switch, l_port)]
                    return Header('loc', (switch, port))
        else:
            # Matching on packet headers does not require mapping
            return Header(self.field, self.pattern)

    def match(self, packet, (switch, port)):
        """Does this header match this located packet?"""
        if self.field == 'loc':
            (s, p) = self.pattern
            return (s == 0 or s == switch) and (p == 0 or p == port)
        else:
            p = self.pattern
            return p == 0 or p == packet[self.field]

def on_port(switch, port):
    """Return a predicate matching packets on switch and port."""
    return Header('loc', (switch, port))

# Compound predicates
class Union(Predicate):
    """A predicate representing the union of two predicates."""
    def __init__(self, left, right):
        """
        ARGS:
            left: first predicate to union
            right: second predicate to union
        """
        assert(isinstance(left, Predicate))
        assert(isinstance(right, Predicate))
        self.left = left
        self.right = right

    def __str__(self):
        return "Union\n%s\n%s" % (self.left, self.right)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pred = self.left.get_physical_predicate(port_map, switch_map)
        r_pred = self.right.get_physical_predicate(port_map, switch_map)
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
        assert(isinstance(left, Predicate))
        assert(isinstance(right, Predicate))
        self.left = left
        self.right = right

    def __str__(self):
        return "Intersection\n%s\n%s" % (self.left, self.right)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pred = self.left.get_physical_predicate(port_map, switch_map)
        r_pred = self.right.get_physical_predicate(port_map, switch_map)
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
        assert(isinstance(left, Predicate))
        assert(isinstance(right, Predicate))
        self.left = left
        self.right = right

    def __str__(self):
        return "Difference\n%s\n%s" % (self.left, self.right)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pred = self.left.get_physical_predicate(port_map, switch_map)
        r_pred = self.right.get_physical_predicate(port_map, switch_map)
        return Difference(l_pred, r_pred)

    def match(self, packet, loc):
        return (self.left.match(packet, loc) and
                not self.right.match(packet, loc))

def nary_union(predicates):
    """Return a union of all predicates in predicates."""
    if len(predicates) == 0:
        return None
    else:
        base = predicates[0]
        for predicate in predicates[1:]:
            base = Union(predicate, base)
        return base

def nary_intersection(predicates):
    """Return a intersection of all predicates in predicates."""
    if len(predicates) == 0:
        return None
    else:
        base = predicates[0]
        for predicate in predicates[1:]:
            base = Intersection(predicate, base)
        return base

def forward(switch, ports):
    if isinstance(ports, int):
        ports = [ports]
    return Action(switch, ports=ports)

class Action:
    """Description of a forwarding action, with possible modification."""
    def __init__(self, switch, ports=[], modify=dict()):
        """
        ARGS:
            switch: switch on which the ports live
            ports: ports to which to forward packet
            modify: dictionary of header fields to values, fields that are set
                will overwrite the packet's fields
        """
        assert(isinstance(ports, type([])))
        assert(isinstance(modify, type({})))
        self.switch = switch
        self.ports = ports
        self.modify = modify

    def __str__(self):
        return "%s: %s %s" % (self.switch, self.modify, self.ports)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (self.switch == other.switch and
            self.ports == other.ports and
            self.modify == other.modify)

    def modify_packet(self, packet):
        """Modify packet with this action's modify pattern.

        ARGS:
            packet: packet to modify

        RETURNS:
            packet modified by this action's modify pattern
        """
        new = copy.deepcopy(packet)
        # TODO(astory): update wildcards correctly that are smaller than whole
        # fields
        new.fields.update(self.modify)
        return (new, (self.switch, self.ports))

    def get_physical_rep(self, port_map, switch_map):
        """Return this action mapped to a physical network."""
        # Only return the port number, not the (switch, port) pair
        p_ports = [port_map[(self.switch, p)][1] for p in self.ports]
        return Action(switch_map[self.switch], p_ports, self.modify)

class Policy:
    """Top-level abstract description of a static network program."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        pass

    @abstractmethod
    def get_actions(self, packet, loc):
        """Get set of (pkt, loc) this policy generates for a located packet."""
        pass

    def __add__(self, other):
        return PolicyUnion(self, other)

    def __mod__(self, predicate):
        return PolicyRestriction(self, predicate)

class BottomPolicy(Policy):
    """Policy that drops everything."""
    def __init__(self):
        pass

    def get_physical_rep(self, port_map, switch_map):
        return self

    def get_actions(self, packet, loc):
        return []

    def __str__(self):
        return "BottomPolicy"

    def __repr__(self):
        return self.__str__()

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
        assert(isinstance(predicate, Predicate))
        assert(isinstance(actions, type([])))
        self.predicate = predicate
        self.actions = actions

    def __str__(self):
        return "PrimitivePolicy\n%s\n%s" % (self.predicate, self.actions)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.predicate == other.predicate and \
            self.actions == other.actions

    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        p_pred = self.predicate.get_physical_predicate(port_map, switch_map)
        p_act = [action.get_physical_rep(port_map, switch_map)
                 for action in self.actions]
        return PrimitivePolicy(p_pred, p_act)

    def get_actions(self, packet, loc):
        if self.predicate.match(packet, loc):
            return self.actions
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
        assert(isinstance(left, Policy))
        assert(isinstance(right, Policy))
        self.left = left
        self.right = right

    def __str__(self):
        return "PolicyUnion\n%s\n%s" % (self.left, self.right)

    def __repr__(self):
        return self.__str__()

    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        l_pol = self.left.get_physical_rep(port_map, switch_map)
        r_pol = self.right.get_physical_rep(port_map, switch_map)
        return PolicyUnion(l_pol, r_pol)

    def get_actions(self, packet, loc):
        left = self.left.get_actions(packet, loc)
        left.extend(self.right.get_actions(packet, loc))
        return left

def nary_policy_union(policies):
    """Take the union of many policies."""
    if len(policies) == 0:
        return None
    else:
        base = policies[0]
        for policy in policies[1:]:
            base = PolicyUnion(policy, base)
        return base

# Maybe we can provide this with just a function that transforms the policy?
# -astory
class PolicyRestriction(Policy):
    """A policy restricted by a predicate."""
    def __init__(self, policy, predicate):
        """
        ARGS:
            policy: policy to restrict
            predicate: predicate to restrict it by
        """
        assert(isinstance(policy, Policy))
        assert(isinstance(predicate, Predicate))
        self.policy = policy
        self.predicate = predicate

    def __str__(self):
        return "PolicyRestriction\n%s\n%s" % (self.predicate, self.policy)

    def __repr__(self):
        return self.__str__()

    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts

        ARGS:
        port_map: {(l_switch, l_port): (p_switch, p_port)}
        switch_map: {l_switch: p_switch}

        Note that switches are mapped according to the switch map, not the
        switch recorded in the port map.  If they are not the same, that is an
        error, but this function does not check.

        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical
        counterparts
        """
        pol = self.policy.get_physical_rep(port_map, switch_map)
        pred = self.predicate.get_physical_predicate(port_map, switch_map)
        return PolicyRestriction(pol, pred)

    def get_actions(self, packet, loc):
        if self.predicate.match(packet, loc):
            return self.policy.get_actions(packet, loc)
        else:
            return []
