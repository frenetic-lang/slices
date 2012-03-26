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

class Predicate:
    """Top-level abstract class for predicates."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        pass

# Primitive predicates

# Should these just be one class that holds a boolean?
class Top(Predicate):
    """The always-true predicate."""
    def get_physical_predicate(self, port_map, switch_map):
        return Top()

class Bottom(Predicate):
    """The always-false predicate."""
    def get_physical_predicate(self, port_map, switch_map):
        return Bottom()

HEADER_FIELDS = set (['loc', # See Header for special note about this value
                      'srcmac',
                      'dstmac',
                      'ethtype',
                      'srcip',
                      'dstip',
                      'vlan',
                      'protocol',
                      'srcport',
                      'dstport',
                      'srcip',
                      'dstip' ])

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
        self.field = field
        self.pattern = pattern

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        if self.field == 'loc':
            switch = 0
            if self.pattern[0] != 0:
                switch = switch_map[self.pattern[0]]
            port = 0
            if self.pattern[1] != 0:
                port = port_map[self.pattern[1]]
            return Header(self.field, (switch, port))
        return Header(self.field, self.pattern)

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
        self.left = left
        self.right = right

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        l_pred = self.left.get_physical_predicate(port_map, switch_map)
        r_pred = self.right.get_physical_predicate(port_map, switch_map)
        return Union(l_pred, r_pred)


def nary_union(predicates):
    if len(predicates) == 0:
        return None
    else:
        base = predicates[0]
        for p in predicates[1:]:
            base = Union(p, base)
        return base

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

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        l_pred = self.left.get_physical_predicate(port_map, switch_map)
        r_pred = self.right.get_physical_predicate(port_map, switch_map)
        return Union(l_pred, r_pred)

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

    def get_physical_predicate(self, port_map, switch_map):
        """ Creates a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this Predicate in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        l_pred = self.left.get_physical_predicate(port_map, switch_map)
        r_pred = self.right.get_physical_predicate(port_map, switch_map)
        return Union(l_pred, r_pred)

class Action:
    """Description of a forwarding action, with possible modification."""
    def __init__(self, switch, port, modify=dict()):
        """
        ARGS:
            switch: switch on which the port lives
            port: port to which to forward packet
            modify: dictionary of header fields to wildcarded strings, those
                fields in the packet will be overwritten by non-wildcard bits in
                the corresponding string.
        """
        self.switch = switch
        self.port = port
        self.modify = modify

    def modify_packet(self, packet):
        """Modify packet with this action's modify pattern.

        ARGS:
            packet: packet to modify

        RETURNS:
            packet modified by this action's modify pattern
        """
        # TODO(astory): implement, which requires a fixed packet data structure
        return packet

    def get_physical_rep(self, port_map, switch_map):
        return Action(switch_map[self.switch], port_map[self.port], self.modify)

class Policy:
    """Top-level abstract description of a static network program."""
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        pass

class PrimitivePolicy(Policy):
    def __init__(self, predicate, actions):
        """
        ARGS:
            predicate: predicate under which to apply actions
            actions: list of actions to apply to packets which match predicate,
                all actions are applied, resulting in potentially multiple
                packets.  Note that this may be the empty list.
        """
        self.predicate = predicate
        self.actions = actions

    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        p_pred = self.predicate.get_physical_predicate(port_map, switch_map)
        p_acts = []
        for act in self.actions:
            p_acts.append(act.get_physical_rep(port_map, switch_map))
        return PrimitivePolicy(p_pred, p_acts)

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

    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        l_pol = self.left.get_physical_rep(port_map, switch_map)
        r_pol = self.right.get_physical_rep(port_map, switch_map)
        return PolicyUnion(l_pol, r_pol)

def nary_policy_union(policies):
    if len(policies) == 0:
        return None
    else:
        base = policies[0]
        for p in policies[1:]:
            base = PolicyUnion(p, base)
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
        self.policy = policy
        self.predicate = predicate

    def get_physical_rep(self, port_map, switch_map):
        """ Creates a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        
        ARGS:
        port_map: map from logical to physical ports
        switch_map: map from logical to physical switches


        RETURNS:
        a copy of this object in which all logical
        ports and switches have been mapped to their physical 
        counterparts
        """
        pol = self.policy.get_physical_rep(port_map, switch_map)
        pred = self.predicate.get_physical_predicate(port_map, switch_map)
        return PolicyRestriction(pol, pred)
