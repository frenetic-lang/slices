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

def get_physical_rules(slices):
    """Turns a list of virtual slices into a physical topo with netcore 
       predicates

    ARGS:
        slices: a list of slices

    RETURNS:
        A list containing the mappings from physical ports to predicates
    """

    port_policies = dict()
    for slic in slices:
        for (port, predicate) in slic.physical_policies():
            if port in port_policies:
                port_policies[port].append(predicate)
            else:
                port_policies[port] = [predicate]

    # TODO combine policies, assign VLANs (probably at an earlier step) 
    # This may involve adding computations to the loop

    return port_policies
            
        

def is_injective(mapping):
    """Determine if a mapping is injective.

    ARGS:
        mapping: map to check

    RETURNS:
        True if mapping is injective, False otherwise
    """
    codomain = set(mapping.values())
    return len(mapping) == len(codomain)

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

    for (edge_port, predicate) in edge_policy:
        if predicate is None:
            return False #Do we want this?
        port_set.add(edge_port)
    for switch in topo.edge_switches():
        for port in topo.edge_ports(switch):
            if not port in port_set:
                return False
    return True

class Slice:
    """Data structure to represent virtual network slices."""
    def __init__(self, logical_topology, physical_topology, node_map, port_map,
                 edge_policy):
        """Create a Slice.

        ARGS:
            logical_topology: NXTopo object representing the logical topology
                that this slice uses
            physical_topology: NXTopo this slice will run on top of
            node_map: mapping from nodes in the logical topology to nodes in
                the physical topology, must be injective
            port_map: mapping from ports in the logical topology to ports in the
                physical topology, must be injective
            edge_policy: set of (edge_port, predicate) pairs, only packets
                entering the edge port that satisfy the predicate will be allowed to
                pass
        
        Note that because we need to have the ports in both topologies be
        defined, only finalized NXTopo objects will work for creating a slice.
        """
        self.l_topo = logical_topology
        self.p_topo = physical_topology
        self.node_map = node_map
        self.port_map = port_map
        self.edge_policy = edge_policy
        assert self.validate()

    def physical_policies(self):
        """Convert the slice's virtual policies and internal edges 
        to physical netcore policies.

        RETURNS:
        A dictionary mapping physical edge ports to netcore policies
        """
        port_map = dict() # change if injection removed
        
        for (l_port, p_port) in self.port_map:
            if l_port in self.edge_policy:
                port_map[p_port] = self.edge_policy[l_port]
            else:
                port_map[p_port] = self.get_internal_predicate(l_port) 
           
        return port_map          

    def get_internal_predicate(self, l_port):
        """Get physical policy for the non-edge port
       
        ARGS:
        l_port: the logical port
        
        RETURNS:
        the physical policy for the given port

        """

        # get dest switch
        l_dest = l_port[1]
        # get outgoing ports from dest
        for port in self.l_topo.edges(l_dest):
            if not port in self.l_topo.edge_ports(l_dest):
                # add forwarding policy to datastructure using physical ports
                pass # TODO construct policy
               
    def validate(self):
        """Check sanity conditions on this slice.

        Validates the following concerns:
        * All nodes in the logical topology are mapped by node_map
        * All ports in the logical topology are mapped by port_map
        * node_map is injective
        * port_map is injective
        * every edge port in the logical topology is associated with a predicate
        """
        return (self.l_topo.nodes == self.node_map.keys() and
                self.l_topo.edges == self.port_map.keys() and
                is_injective(self.node_map) and
                is_injective(self.port_map) and
                policy_is_total(self.edge_policy, self.l_topo))
