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
# /slices/edge_compile.py                                                      #
# Tools to compile virtual network policies to physical network policies with  #
# separate vlans on each edge                                                  #
################################################################################
"""Compile with independent edge vlan tags."""

#TODO(astory): figure out a way to remove spurious policies inside of
#              restrictions and unions.  One way to do this is to have
#              restrictions auto-reduce themselves by applying their predicates
#              to their policies and seeing if they turn up empty, which would
#              let us prune the tree using the existing reduction steps.

from compile import external_predicate, modify_vlan_local
import copy
import netcore as nc
import vlan as vl

VLAN0 = nc.Header({'vlan': 0})

def transform(topo, slices, assigner=vl.edge_optimal, verbose=False):
    """Turn a set of slices sharing a physical topology into a single policy.
    ARGS:
        slices:  set of (slices, policies) (with the same physical topology) to
            combine
        assigner:  function to use to assign vlans to slices.  Must return a
            {slice: vlan} dictionary, defaults to sequential.
        verbose:  print out progress information

    RETURNS:
        a single Policy encapsulating the shared but isolated behavior of all
        the slices
    """
    policy_list = compile_slices(topo, slices, assigner, verbose)
    return nc.nary_policy_union(policy_list)

def compile_slices(topo, slices, assigner=vl.edge_optimal, verbose=False):
    """Turn a set of slices sharing a physical topology into a list of policies.

    See transform for more documentation.
    """
    slice_only = [s for (s, p) in slices]
    if verbose:
        import sys
        print 'Assigning slice vlans...',
    vlans = assigner(topo, slice_only, verbose=verbose)
    slice_lookup = get_slice_lookup(vlans)
    if verbose:
        print 'done.'
        for i in range(len(slice_lookup)):
            print '%d: %s' % (i, slice_lookup[slice_only[i]])
        print 'Compiling slices...',
    policy_list = []
    count = 0
    for slic, policy in slices:
        vlan_dict = symmetric_edge(slice_lookup[slic])
        internal_p = internal_policy(slic.l_topo, policy, vlan_dict)
        external_p = external_policy(slic, policy, vlan_dict)
        policies = [p.get_physical_rep(slic.node_map, slic.port_map)
                    for p in internal_p + external_p]
        policies = [p for p in policies if not isinstance(p, nc.BottomPolicy)]
        policy_list.append(nc.nary_policy_union(policies))
        if verbose:
            count += 1
            print '.',
            sys.stdout.flush()
    if verbose:
        print 'done.'
        print '%d policies generated.' % len(policy_list)
    return policy_list

def edge_of_port(topo, (switch, port)):
    """Return the edge that port traverses in topo.

    Note that this may be the other direction of edge from a dictionary
    representation.  The edge produced always starts from the given switch and
    goes to the found one.
    """
    return ((switch, port),
            topo.node[switch]['port'][port])

def symmetric_edge(vlan):
    """Return a new dictionary that has both edge directions."""
    output = {}
    for (s1, s2), tag in vlan.items():
        output[(s1, s2)] = tag
        output[(s2, s1)] = tag
    return output

def get_slice_lookup(edge_lookup):
    """Invert {edge: {slice: tag}} to get {slice: {edge: tag}}."""
    output = {}
    for edge, slice_dict in edge_lookup.items():
        for slic, tag in slice_dict.items():
            if slic not in output:
                output[slic] = {}
            output[slic][edge] = tag
    return output

# TODO(astory): don't set the vlan tag if it's already what we want it to be.
# But do this carefully.  We still need to completely remove forwards to ports
# that aren't under consideration at the moment.
def internal_policy(topo, policy, symm_vlan):
    """Produce a list of policies for slic restricted to its vlan.

    This policy must also carry the vlan tags through the network as they
    change.  These policies handle all and only packets incident to switches
    over an internal edge, and includes stripping vlan tags off them as they
    leave the network.

    ARGS:
        policy:  Policy to restrict
        vlan:  {edge -> vlan}, symmetric

    RETURNS:
        a new policy object that is policy but restricted to its vlan.
    """

#    print '========================='
#    print '========================='
#    print policy
#    print '----'
    policies = []
    # incoming edge to s1.  Note that we only get internal edges
    for ((s1, p1), (s2, p2)), tag in symm_vlan.items():
        if s1 in topo.node:
            pred = (nc.inport(s1, p1) & nc.Header({'vlan': tag})).reduce()
            # For each outgoing edge from s1, set vlan to what's appropriate
            for (p_out, dst) in topo.node[s1]['port'].items():
                if ((s1, p_out), dst) in symm_vlan:
                    target_vlan = symm_vlan[((s1, p_out), dst)]
                else:
                    target_vlan = 0
#                print '%s:%s on %s -> %s on %s' % (s1, p1, tag, p_out, target_vlan)
#                print 'restrict with %s' % pred
                new_policy = (policy % pred).reduce()
#                print new_policy
                new_policy = modify_vlan_local(new_policy, (s1, p_out),
                                               target_vlan, this_port_only=True)
                new_policy = new_policy.reduce()
#                print 'vvv'
#                print new_policy
#                print '----'
                # modify_vlan_local does not create any new reduceables
                policies.append(new_policy)
    return policies

def external_policy(slic, policy, symm_vlan):
    """Produce a policy that moves packets along external ports into the vlan.

    Just restricting packets to the vlan means that packets can never enter the
    slice.  To let packets enter, we need to make another copy of the policy,
    restrict it to only entrances, and change the actions to add the vlan.

    We also set packets leaving the network immediately back to 0

    ARGS:
        slic:  Slice to produce this policy for
        policy:  Policy to restrict
        vlan:  {edge -> vlan}, symmetric

    RETURNS:
        A policy that moves packets incoming to external ports into the vlan,
        but only if they satisfy the slice's isolation predicates.
    """
    policies = []
    for (s, p), pred in slic.edge_policy.items():
        if edge_of_port(slic.l_topo, (s, p)) in symm_vlan:
            # symm_vlan contains all the internal edges to the slice.
            # Since we only care about incident external edges, if we're
            # considering an internal edge, we don't want to add any predicates.
            # In principle, there shouldn't be any of these
            (_, (dst_switch, dst_port)) = edge_of_port(slic.l_topo, (s, p))
        else:
            # An external edge
            ext_pred = external_predicate((s, p), pred) & VLAN0
            for (p_out, dst) in slic.l_topo.node[s]['port'].items():
                if ((s, p_out), dst) in symm_vlan: # it's an internal edge
                    target_vlan = symm_vlan[((s, p_out), dst)]
                    new_policy = (policy % ext_pred).reduce()
                # modify_vlan_local does not create any new reduceables
                    policies.append(modify_vlan_local(new_policy, (s, p_out),
                                                      target_vlan))
                else: # outgoing, set it to 0
                    # but since we already know the packet is set to 0, just
                    # append the policy
                    new_policy = (policy % ext_pred).reduce()
                    policies.append(new_policy)
    return policies

def stress_test(inp=None, n=256):
    """Run a stress test, for profiling.

    can use inp=(topo, zip(slices, policies)) if you already have it.
    Otherwise, uses the n-ary break_vlans graph and slices.
    """
    if inp is None:
        from examples import break_vlans, policy_gen
        topo, slices = break_vlans.get_slices(n=n)
        policies = [policy_gen.flood(s.l_topo, all_ports=True) for s in slices]
        combined = zip(slices, policies)
    else:
        topo, combined = inp

    transformed = transform(topo, combined, verbose=True)

if __name__ == '__main__':
    stress_test(n=25)
