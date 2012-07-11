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
# /slices/encoder.py                                                           #
# JSON serialization for netcore objects.                                      #
################################################################################
"""JSON serialization for netcore objects.

Interfaces are essentially exactly the same as each object's __dict__, except
that '__class__' is replaced with 'type'.  The procedure is simple enough that a
glance at NetcoreEncoder should explain the whole thing.
"""

import json
import netcore as nc

class NetcoreEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, nc.Predicate):
            return self.predicate(o)
        elif isinstance(o, nc.Action):
            return self.action(o)
        elif isinstance(o, nc.Policy):
            return self.policy(o)
        else:
            raise TypeError('%s not a Netcore policy, action or predicate.' % o)

    def predicate(self, p):
        if isinstance(p, nc.Top):
            return {'type': 'Top'}
        elif isinstance(p, nc.Bottom):
            return {'type': 'Bottom'}
        elif isinstance(p, nc.Header):
            return {'type': 'Header',
                    'fields': p.fields}
        elif isinstance(p, nc.Union):
            return {'type': 'Union',
                    'left': self.predicate(p.left),
                    'right': self.predicate(p.right)}
        elif isinstance(p, nc.Intersection):
            return {'type': 'Intersection',
                    'left': self.predicate(p.left),
                    'right': self.predicate(p.right)}
        elif isinstance(p, nc.Difference):
            return {'type': 'Difference',
                    'left': self.predicate(p.left),
                    'right': self.predicate(p.right)}
        else:
            raise TypeError('Unknown predicate type: %s' % p)

    def action(self, a):
        return {'type': 'Action',
                'switch': a.switch,
                'ports': list(a.ports),
                'modify': a.modify,
                'obs': list(a.obs)}

    def policy(self, p):
        if isinstance(p, nc.BottomPolicy):
            return {'type': 'BottomPolicy'}
        elif isinstance(p, nc.PrimitivePolicy):
            return {'type': 'PrimitivePolicy',
                    'predicate': self.predicate(p.predicate),
                    'actions': [self.action(a) for a in p.actions]}
        elif isinstance(p, nc.PolicyUnion):
            return {'type': 'PolicyUnion',
                    'left': self.policy(p.left),
                    'right': self.policy(p.right)}
        elif isinstance(p, nc.PolicyRestriction):
            return {'type': 'PolicyRestriction',
                    'policy': self.policy(p.policy),
                    'predicate': self.predicate(p.predicate)}
        else:
            raise TypeError('Unknown policy type: %s' % p)

class NetcoreDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.to_netcore, **kwargs)

    def to_netcore(self, d):
        if 'type' not in d:
            # This means that we're at a leaf dictionary, for a header, or
            # modification.  We want to return it as a dictionary.
            return d
        typ = d['type']

        try:
            # Predicates
            if typ == 'Top':
                return nc.Top()
            elif typ == 'Bottom':
                return nc.Bottom()
            elif typ == 'Header':
                return nc.Header(d['fields'])
            elif typ == 'Union':
                return nc.Union(d['left'], d['right'])
            elif typ == 'Intersection':
                return nc.Intersection(d['left'], d['right'])
            elif typ == 'Difference':
                return nc.Difference(d['left'], d['right'])

            # Action
            elif typ == 'Action':
                return nc.Action(d['switch'], ports=d['ports'],
                                 modify=d['modify'], obs=d['obs'])

            # Policies
            elif typ == 'BottomPolicy':
                return nc.BottomPolicy()
            elif typ == 'PrimitivePolicy':
                return nc.PrimitivePolicy(d['predicate'], d['actions'])
            elif typ == 'PolicyUnion':
                return nc.PolicyUnion(d['left'], d['right'])
            elif typ == 'PolicyRestriction':
                return nc.PolicyRestriction(d['policy'], d['predicate'])
        except KeyError, e:
            raise TypeError('Expected field of type %s when decoding type %s'
                            % (e, typ))
