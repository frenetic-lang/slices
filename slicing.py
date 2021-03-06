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
# /updates/slicing.py                                                          #
# Data structure to represent virtual network slices                           #
################################################################################
"""Data structure to represent virtual network slices and related tools."""
import util

def is_injective(mapping):
    """Determine if a mapping is injective.

    ARGS:
        mapping: map to check

    RETURNS:
        True if mapping is injective, False otherwise
    """
    codomain = set(mapping.values())
    return len(mapping) == len(codomain)

def assert_is_injective(mapping):
    """Asserts that a mapping is injective.

    ARGS:
        mapping: map to check
    """
    checked = set()
    err = "%s occurs more than once in the domain"
    for vlu in mapping.values():
        assert vlu not in checked, err % str(vlu)
        checked.add(vlu)

def policy_is_total(edge_policy, topo):
    """Determine if an edge policy covers all edge ports.

    ARGS:
        edge_policy:  collection of (edge_port, predicate) pairs that represents
            a slice's policy for ingress edges
        topo: NXTopo to which edge_policy applies

    RETURNS:
        True if all the edges in topo have a matching predicate, False
            otherwise.
    """
    port_set = set()

    for edge_port in edge_policy.keys():
        predicate = edge_policy[edge_port]
        if predicate is None:
            return False #Do we want this?
        port_set.add(edge_port)
    for switch in topo.edge_switches():
        for port in topo.edge_ports(switch):
            if not (switch, port) in port_set:
                return False
    return True

def assert_policy_is_total(edge_policy, topo):
    """Determine if an edge policy covers all edge ports and raises an
    AssertionError if it doesn't

    ARGS:
        edge_policy:  collection of (edge_port, predicate) pairs that represents
            a slice's policy for ingress edges
        topo: NXTopo to which edge_policy applies
    """
    port_set = set()

    err = "port %s has null edge predicate"
    for edge_port in edge_policy.keys():
        predicate = edge_policy[edge_port]
        #Do we want this?
        assert predicate is not None, err % str(edge_port)
        port_set.add(edge_port)
    err =  "port %s  has no edge predicate"
    for switch in topo.edge_switches():
        for port in topo.edge_ports(switch):
            assert (switch, port) in port_set, err % str((switch, port))

def assert_set_equals(set1, set2):
    """Asserts two sets are equal

    ARGS:
        set1: 1st set to check
        set2: 2nd set to check
    """
    err =  "expected <type 'set'>; got %s"
    assert type(set1) is set, err % str(type(set1))
    assert type(set2) is set, err % str(type(set2))

    err =  "%s in 1st set but not 2nd"
    if(len(set1) < len(set2)):
        temp = set1
        set1 = set2
        set2 = temp
        err =  "%s in 2nd set but not 1st"

    for entry in set1:
        assert entry in set2, err % str(entry)

def ident_map_slice(topo, edge_policy, map_end_hosts=False):
    """Build a slice using topo as both the physical and logical topology."""
    node_map = util.id_map(topo.nodes() if map_end_hosts else topo.switches())
    port_map = util.id_map(util.ports_of_topo(topo))
    return Slice(topo, topo, node_map, port_map, edge_policy, map_end_hosts)

class Slice:
    """Data structure to represent virtual network slices."""
    def __init__(self, logical_topology, physical_topology, node_map, port_map,
                 edge_policy, map_end_hosts=False):
        """Create a Slice.

        ARGS:
            logical_topology: NXTopo object representing the logical topology
                that this slice uses.  It should INCLUDE the end hosts.
            physical_topology: NXTopo this slice will run on top of
            node_map: mapping from nodes in the logical topology to nodes in
                the physical topology, must be injective
            port_map: mapping from (switch,port) in the logical topology to
                (switch,port) in the physical topology, must be injective
            edge_policy: dictionary of {(switch, port) : predicate} pairs,
                only packets entering the edge port that satisfy the predicate
                will be allowed to pass
            map_end_hosts: whether end hosts are mapped in the node_map or not,
                only affects validation

        Note that because we need to have the ports in both topologies be
        defined, only finalized NXTopo objects will work for creating a slice.
        """
        self.l_topo = logical_topology
        self.p_topo = physical_topology
        self.node_map = node_map
        self.port_map = port_map
        self.edge_policy = edge_policy
        self.map_end_hosts = map_end_hosts
        self.validate()

    def validate(self):
        """Check sanity conditions on this slice.

        Validates the following concerns:
        * All nodes in the logical topology are mapped by node_map
        * All ports in the logical topology are mapped by port_map
        * node_map is injective
        * port_map is injective
        * every edge port in the logical topology is associated with a predicate
        """

        ports = set()
        if self.map_end_hosts:
            switches = set(self.l_topo.nodes())
        else:
            switches = set(self.l_topo.switches())
        for switch in switches:
            for port in self.l_topo.node[switch]['ports'].values():
                if port != 0 or self.map_end_hosts:
                    ports.add((switch, port))

        assert_set_equals(switches,
                          set(self.node_map.keys()))
        assert_set_equals(ports, set(self.port_map.keys()))
        assert_is_injective(self.node_map)
        assert_is_injective(self.port_map)
        assert_policy_is_total(self.edge_policy, self.l_topo)
