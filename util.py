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
# /updates/util.py                                                             #
# Tools for slicing                                                            #
################################################################################
"""Tools for slicing."""

import netcore as nc

def id_map(items):
    """Make a mapping that is the identity over items."""
    return dict((i, i) for i in items)

def links(topo, sid):
    """Get a list of ((s,p), (s,p)) for all outgoing links from this switch."""
    switch = topo.node[sid]
    return [((sid, our_port), (them, their_port))
            for our_port, (them, their_port) in switch['port'].items()
            # If their_port == 0, they're an end host, not a switch.
            # We don't care about end hosts.
            if their_port != 0]

def edges_of_topo(topo, undirected=False):
    """Get all switch-switch edges in a topo, as ((s,p), (s,p))."""
    # Need to dereference switch id to get full object
    lnks = []
    for switch in topo.switches():
        lnks.extend(links(topo, switch))
    if undirected:
        lnks_new = set()
        for (source, sink) in lnks:
            if (sink, source) not in lnks_new:
                lnks_new.add((source, sink))
        return lnks_new
    else:
        return lnks

def map_edges(lnks, switch_map, port_map):
    """Map ((s, p), (s, p)) edges according to the two maps."""
    mapped = []
    for (s1, p1), (s2, p2) in lnks:
        # only include the port result from the port map, don't rely on the
        # switch recorded there
        mapped.append(((switch_map[s1], port_map[(s1, p1)][1]),
                       (switch_map[s2], port_map[(s2, p2)][1])))
    return mapped

def ports_of_topo(topo, end_hosts=False):
    """Get all (switch, port)s of a topo as a set."""
    output = set()
    for number, node in topo.node.items():
        ports = node['port'].keys()
        for p_num in ports:
            # Only include if a switch, or we're including end hosts
            if p_num != 0 or end_hosts:
                output.add((number, p_num))
    return output

def build_external_predicate(l_topo):
    """Build external predicates for topo that accept all packets."""
    predicates = {}
    for n, node in l_topo.node.items():
        if node['isSwitch']:
            for p, (target, target_port) in node['port'].items():
                if target_port == 0: # that means target is an end host
                    predicates[(n, p)] = nc.Top()
    return predicates

def fields_of_predicate(pred):
    """Return all fields this predicate matches on."""
    if isinstance(pred, nc.Top) or isinstance(pred, nc.Bottom):
        return set([])
    elif isinstance(pred, nc.Header):
        return set(pred.fields.keys())
    elif (isinstance(pred, nc.Union) or
          isinstance(pred, nc.Intersection) or
          isinstance(pred, nc.Difference)):
        return fields_of_predicate(pred.left).union(
               fields_of_predicate(pred.right))
    else:
        raise Exception('unknown predicate %s' % p)

def fields_of_action(action):
    return set(['switch', 'port']).union(set(action.modify.keys()))

def fields_of_policy(pol):
    """Return all fields this policy matches on or modifies."""
    if isinstance(pol, nc.BottomPolicy):
        return set([])
    elif isinstance(pol, nc.PrimitivePolicy):
        fields = fields_of_predicate(pol.predicate)
        for a in pol.actions:
            fields.update(fields_of_action(a))
        return fields
    elif isinstance(pol, nc.PolicyUnion):
        return fields_of_policy(pol.left).union(
               fields_of_policy(pol.right))
    elif isinstance(pol, nc.PolicyRestriction):
        return fields_of_policy(pol.policy).union(
               fields_of_predicate(pol.predicate))

def observations(policy):
    """Return set of observations policy may emit."""
    if isinstance(policy, nc.BottomPolicy):
        return set()
    elif isinstance(policy, nc.PrimitivePolicy):
        obs = set()
        for a in policy.actions:
            obs.update(a.obs)
        return obs
    elif isinstance(policy, nc.PolicyUnion):
        left = observations(policy.left)
        left.update(observations(policy.right))
        return left
    elif isinstance(policy, nc.PolicyRestriction):
        return observations(policy.policy)
