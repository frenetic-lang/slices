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

from abc import ABCMeta

class Predicate:
    """Top-level abstract class for predicates."""
    __metaclass__ = ABCMeta

# Primitive predicates

# Should these just be one class that holds a boolean?
class Top(Predicate):
    """The always-true predicate."""
    pass

class Bottom(Predicate):
    """The always-false predicate."""
    pass

HEADER_FIELDS = set (["switch",
                      "inport",
                      "srcmac",
                      "dstmac",
                      "ethtype",
                      "srcip",
                      "dstip",
                      "vlan",
                      "protocol",
                      "srcport",
                      "dstport",
                      "srcip",
                      "dstip" ])

class Header(Predicate):
    """A predicate representing matching a header with a wildcard pattern.
    
    Matches a header against a wildcard.  Note that "header" fields also include
    switch and port fields.  See header_fields for a complete list
    """
    def __init__(self, field, pattern):
        """
        ARGS:
            field: header field to match pattern against
            pattern: (possibly) wildcarded bitstring
        """
        self.field = field
        self.pattern = pattern

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

class Action:
    """Description of a forwarding action, with possible modification."""
    def __init__(self, port, modify=dict()):
        """
        ARGS:
            port: port to which to forward packet
            modify: dictionary of header fields to wildcarded strings, those
                fields in the packet will be overwritten by non-wildcard bits in
                the corresponding string.
        """
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

class Policy:
    """Top-level abstract description of a static network program."""
    __metaclass__ = ABCMeta

class PrimitivePolicy(Policy):
    def __init__(self, predicate, actions):
        """
        ARGS:
            predicate: predicate under which to apply actions
            actions: list of actions to apply to packets which match predicate,
                all actions are applied, resulting in potentially multiple
                packets.
        """
        self.predicate = predicate
        self.actions = actions

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
