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
# /updates/examples/isolization.py                                             #
################################################################################

import sys
import logging

import networkx as nx
import verification
from experiment_base import *
import string

import update_lib
from run import send_signal 

from netcore import *
import policy
import netcore_compiler
import compile

from routing_policies import shortest_path_policy

import amaz_ex

class FakeNX(object):
    def __init__(self, switch_list):
        self.switch_list = switch_list
    def switches(self):
        return self.switch_list

def test_1():
    '''
    Construct and compile a policy for a forwarding switch.
    '''

    # Build a netcore policy
    switch = 1
    pol = PolicyUnion(
            PrimitivePolicy(Header('loc', (switch, 2)), [Action(1, [1], {'VLAN' : 1})]),
            PrimitivePolicy(Header('loc', (switch, 1)), [Action(1, [1], {'VLAN' : 0})]))

    networkConfig = netcore_compiler.compile(FakeNX([switch]), pol)
    send_signal("In main:\n%s\n" % networkConfig)

def ip(h):
    return "10.0.0." + str(h)

def netcore_shortest_path(graph):
    raw = []
    for src in graph.hosts():
        for dst in graph.hosts():
            if src != dst:
                try:
                    path = nx.shortest_path(graph,src,dst)
                except nx.exception.NetworkXNoPath:
                    continue
                last = path.pop(0)
                curr = path.pop(0)
                for next in path:
                    inport = graph.node[curr]['ports'][last]
                    outport = graph.node[curr]['ports'][next]
                    assert(isinstance(inport, type(0)))
                    assert(isinstance(curr, type(0)))
                    headers = [Header('loc', (curr, inport)),
                               Header('ethtype', 0x800),
                               Header('srcip', ip(src)), 
                               Header('dstip', ip(dst))]
                    pol = PrimitivePolicy(nary_intersection(headers), 
                                          [Action(curr, [outport], {})])
                    raw.append(pol)
                    last = curr
                    curr = next
    return nary_policy_union(raw)

def test_2(Topology, flavor):
    '''
    Mimic the routing example from routing.py.
    '''
    topo = topologies[flavor](1, Topology)
    netcorePolicy = netcore_shortest_path(topo)
    spp = shortest_path_policy(topo)
#    send_signal("Topology: %s\n\nSPP:\n%s\n\nNetwork policy:\n%s\n" % 
#      ([s for s in topo], spp, networkConfig))

#    networkConfig = netcore_compiler.compile(topo, netcorePolicy)
#    update_lib.install(networkConfig, count=False)
    send_signal("Success!")

def test_3(Topology, flavor):
    '''
    Verification over the routing example.
    '''
    topo = topologies[flavor](1, Topology)
    netcorePolicy = netcore_shortest_path(topo)
    networkPolicy = netcore_compiler.compile(topo, netcorePolicy)
    
    # Verification: no loops
    model = verification.KripkeModel(topo, networkPolicy)
    result, msg = model.verify(verification.ISOLATE_HOSTS(topo.hosts()))
    if result:
        send_signal('SUCCESS - hosts isolated!\n')
    else:
        send_signal('FAILURE - hosts not isolated.\n%s\n' % msg)

def slice_sp(slice):
    '''Shortest-path routing for a slice.'''
    return netcore_shortest_path(slice.l_topo)

def test_4():
    logger.debug('Getting slices.')
    topo, slices = amaz_ex.get_slices()
    logger.debug('Compiling slices.')
    netcorePolicy = compile.transform([(s, slice_sp(s)) for s in slices])
    #logger.debug('NetCore policy:\n%s\n' % netcorePolicy)
    logger.debug('Compiling NetCore policy.')
    networkPolicy = netcore_compiler.compile(topo, netcorePolicy)
    #logger.debug('Network Policy:\n%s\n' % networkPolicy)
    logger.debug('Building model.')
    model = verification.KripkeModel(topo, networkPolicy)
    logger.debug('Verifying ISOLATE_HOSTS:')
    result, msg = model.verify(verification.ISOLATE_HOSTS(topo.hosts()))
    if result:
        logger.debug('... SUCCESS - hosts isolated!')
    else:
        logger.debug('... FAILURE - hosts not isolated.')
        logger.debug('%s' % msg)
    logger.debug('Done!')
    send_signal('Done!')
    return

def main(Topology, size, flavor=1, opt=None):
    global logger
    logger = logging.getLogger('isolation')
    logger.setLevel(logging.DEBUG)
    ch = logging.FileHandler('/home/openflow/isolization-master/updates/log.txt')
    ch.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%I:%M:%S %p'))
    logger.addHandler(ch)
    logger.debug('Starting TEST 4.')
    set_size(2)
    #test_3(Topology, int(flavor)-1)
    test_4()
    return

