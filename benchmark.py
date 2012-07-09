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
# /slices/examples/benchmark.py                                                #
# Tools to benchmark netcore compilation.                                      #
################################################################################
"""Tools to benchmark netcore compilation."""

import argparse
import compile as cp
import edge_compile as ec
import netcore as nc
import examples.policy_gen as pg
import random
import sat
import slicing
import examples.topology_gen as tg
import verification
import util
import time

def build_slices(topo, policy):
    predicates1 = util.build_external_predicate(topo, nc.Header({'dstport': 80}))
    predicates2 = util.build_external_predicate(topo, nc.Header({'dstport': 22}))
    slice1 = slicing.ident_map_slice(topo, predicates1)
    slice2 = slicing.ident_map_slice(topo, predicates2)
    return [(slice1, policy),
            (slice2, policy)]

# Topology generators
def waxman(n_hosts):
    topo = tg.waxman(20, beta=0.18)
    tg.add_random_hosts(topo, n_hosts)
    topo.finalize()
    return topo

def smallworld(n_hosts):
    topo = tg.smallworld(20)
    tg.add_random_hosts(topo, n_hosts)
    topo.finalize()
    return topo

def fattree(n_hosts):
    topo = tg.fattree(numEdgeSwitches=(n_hosts-1)/6 + 1)
    topo.finalize()
    return topo

def flood(topo):
    return pg.flood(topo)

def flood_observe(topo):
    return pg.flood_observe(topo)

def shortest_path(topo):
    return pg.all_pairs_shortest_path(topo, hosts_only=True)

def multicast(topo):
    return pg.multicast(topo)

def do_compile(topo, combined, edge=False):
    if edge:
        compiled = ec.compile_slices(topo, combined)
    else:
        compiled = cp.compile_slices(combined)
    return compiled

def main():
    parser = argparse.ArgumentParser(description='Compile netcore programs.')
    parser.add_argument('--waxman', action='store_const', const=waxman,
                        dest='topo_gen', help='Generate a waxman topology')
    parser.add_argument('--smallworld', action='store_const', const=smallworld,
                        dest='topo_gen', help='Generate a smallworld topology')
    parser.add_argument('--fattree', action='store_const', const=fattree,
                        dest='topo_gen', help='Generate a fattree topology')
    parser.add_argument('--flood', action='store_const', const=flood,
                        dest='policy_gen', help='Use a flood routing policy')
    parser.add_argument('--flood_observe', action='store_const',
                        const=flood_observe, dest='policy_gen',
                        help='Use a flood and observe routing policy')
    parser.add_argument('--shortest_path', action='store_const',
                        const=shortest_path, dest='policy_gen',
                        help='Use a shortest path routing policy')
    parser.add_argument('--multicast', action='store_const',
                        const=multicast, dest='policy_gen',
                        help='Use a multicast routing policy')
    parser.add_argument('-e', '--edge', action='store_true', default=False,
                        help='Use the per-edge compiler.')
    parser.add_argument('--hosts', action='store', type=int, default=20,
                        help='Number of hosts on network (approximate for '
                        'fattree).')
    parser.add_argument('--ast', action='store_true', default=False, help=
                        'Print out AST size statistics.')
    parser.add_argument('--ctime', action='store_true', default=False, help=
                        'Print out compilation timing information.')
    parser.add_argument('--vtime', action='store_true', default=False, help=
                        'Print out validation timing information.')
    args = parser.parse_args()
    init = time.time()
    topo = args.topo_gen(args.hosts)
    topo_time = time.time()
    policy = args.policy_gen(topo)
    policy_time = time.time()
    combined = build_slices(topo, policy)
    slice_time = time.time()
    compiled = do_compile(topo, combined, edge=args.edge)
    compile_time = time.time()
    if args.ast:
        ast_orig = policy.size()
        ast_final = compiled[0].size()
        print 'AST Nodes: %5d -> %5d' % (ast_orig, ast_final)
    if args.ctime:
        t = topo_time - init
        p = policy_time - topo_time
        s = slice_time - policy_time
        c = compile_time - slice_time
        print '\n'.join([
                         'Time to compile:        %f' % c,
                        ])
    if args.vtime:
        policy1 = compiled[0]
        policy2 = compiled[1]
        init = time.time()
        assert sat.shared_io(topo, policy1, policy2) is None
        assert sat.shared_io(topo, policy2, policy1) is None
        assert sat.shared_inputs(policy1, policy2) is None
        assert sat.shared_inputs(policy2, policy1) is None
        # Not None because we're not doing output restrictions
        assert sat.shared_outputs(policy1, policy2) is not None
        assert sat.shared_outputs(policy2, policy1) is not None
        assert verification.disjoint_observations(policy1, policy2)
        # Not None because we're not doing output restrictions
        assert sat.shared_transit(topo, policy1, policy2) is not None
        iso_t = time.time()

        print 'Time to check isolation:   %f' % (iso_t - init)
        init = time.time()
        assert sat.simulates_forwards(policy, compiled[0]) is None
        assert sat.simulates_observes(policy, compiled[0]) is None
        assert sat.simulates_forwards2(topo, policy, compiled[0]) is None
        assert sat.simulates(topo, compiled[0], policy)
        assert sat.one_per_edge(topo, compiled[0]) is None
        comp_t = time.time()
        print 'Time to check compilation: %f' % (comp_t - init)

if __name__ == '__main__':
    main()
