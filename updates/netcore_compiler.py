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
# /updates/netcore_compiler.py                                                 #
# Compile NetCore policies to OpenFlow classifiers.                            #
################################################################################
"""
Compile NetCore policies to OpenFlow classifiers.

The following restrictions on NetCore are currently in place:

    1. The patterns associated with header fields may not contain wildcards.
       However, unspecified header fields are considered to match anything.
       This restriction helps ensure that every policy may be fully
       implemented on the switches (i.e. without reactive specialization).
    2. Predicates may not contain Bottom.
    3. PrimitivePolicy nodes may only contain a single Action.

"""

# TODO: remove
global log

##
# NetCore (Python) predicate and policy language, as defined in netcore.py.
#
# Predicate ::= Top
#            |  Bottom
#            |  Header field pattern
#            |  Union pred1 pred2
#            |  Intersection pred1 pred2
#            |  Difference pred1 pred2
#
# Action    ::= Action switch port modification
#
# Policy    ::= PrimitivePolicy predicate [action]
#            |  PolicyUnion policy1 policy2
#            |  PolicyRestriction policy predicate
#

import netcore
import policy

class ConstraintException(Exception):
    """Exception representing a violation of a constraint imposed on the 
       NetCore IR."""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# TODO: use policy.Pattern
class Bone:
    """A decorated rule in the internal NetCore IR of the form

        <pattern : action>

    Each object contains three accessible fields:

        pattern : a (possibly empty) dictionary of header fields (keys) and
                  NetCore patterns (values).
        action  : either True/False/Maybe, in the first phase, or a
                  netcore.Action in the second.
    """
    def __init__(self, pattern, action):
        self.pattern = pattern
        self.action = action

    def __str__(self):
        return "%s :: (%s)" % (self.pattern, self.action)

    def __repr__(self):
        return self.__str__()

def minimize_bones(bones):
    '''
    Attempt to remove redundant bones---e.g. those shadowed by
    bones earlier in the list.  This function is O(n^2) in the
    length of the list.

    ARGS
        bones: a list of Bones, where the action is an Action.

    '''
    if len(bones) < 2:
        return bones

    # Remove any bone completely shadowed by a previous bone.
    to_be_removed = []
    for i in xrange(len(bones) - 1):
        for j in xrange(i+1, len(bones)):
            if pattern_is_subset(bones[j].pattern, bones[i].pattern):
                to_be_removed.append(j)

    new_bones = []
    for i in xrange(len(bones)):
        if i not in to_be_removed:
            new_bones.append(bones[i])

    # Starting at the bottom and working backwards, remove any bone
    # that is immediately redundant.
    # i.e. with
    #   VLAN = 1 : DROP
    #   *        : DROP
    # becomes
    #   *        : DROP
    i = 1
    while i < len(new_bones) - 1:
        if (new_bones[-i].action == new_bones[-(i+1)].action 
            and pattern_is_subset(new_bones[-(i+1)].pattern, new_bones[-i].pattern)):
            del new_bones[-(i+1)]
        else:
            i += 1

    return new_bones


def bones_cross_product(bones1, bones2, f1):
    '''Return the cross product of the two lists of bones, using function f1
    to join the actions of each Bone.'''
    # TODO: remove
    global log
    log.write('--------------\n')
    log.write('%s\nINTERSECT\n%s\n' % (bones1, bones2))
    log.write('======\n')
    # Pattern intersection
    def pattern_and(p1, p2):
        p = p2.copy()
        for field in p1:
            if field not in p2:
                p[field] = p1[field]
            elif p1[field] == p2[field]:
                continue
            else:
                raise ConstraintException("Bottom pattern.")
        return p

    bones = []
    for b1 in bones1:
        for b2 in bones2:
            try:
                newBone = Bone(pattern_and(b1.pattern, b2.pattern),
                               f1(b1.action, b2.action))
                bones.append(newBone)
            except ConstraintException:
                continue
    #TODO: remove
    log.write('%s\n' % bones)
    return minimize_bones(bones)

def compile_bones_intersection(bones1, bones2):
    return bones_cross_product(bones1, bones2,
                               (lambda x, y: x and y))

def compile_bones_negation(bones):
    return map(lambda b: Bone(b.pattern, not b.action), bones)

def compile_bones_difference(bones1, bones2):
    notBones2 = compile_bones_negation(bones2)
    return compile_bones_intersection(bones1, notBones2)

def compile_bones_union(bones1, bones2):
    return bones_cross_product(bones1, bones2, (lambda x, y: x or y))


def compile_predicate_header(switch, header):
    """Compile a NetCore pattern to a Policy pattern."""
    assert(isinstance(header, netcore.Header))

    # Translation from NetCore to OpenFlow header names.
    field_translation = {
      'srcmac' : policy.DL_SRC,
      'dstmac' : policy.DL_DST,
      'ethtype' : policy.DL_TYPE,
      'srcip' : policy.NW_SRC,
      'dstip' : policy.NW_DST,
      'vlan' : policy.DL_VLAN,
      'protocol' : policy.NW_PROTO,
      'srcport' : policy.TP_SRC,
      'dstport' : policy.TP_DST
      }

    # Disallow wildcards for now
#    try:
#        if header.field != 'loc':
#            int(header.pattern)
#    except ValueError:
#        raise ConstraintException(
#          "Pattern in '%s' is not a number (wildcards currently disallowed)." % header)

    # Location is a special case.  Morally, return
    # (switch : sw) /\ (port : p).
    if header.field == 'loc':
        sw,p = header.pattern
        switchMatches = (sw == switch or sw == 0)
        if p != 0:
            d = {policy.IN_PORT : p}
            return [Bone(d, switchMatches), Bone({}, False)]
        return [Bone({}, switchMatches)]

    d = {field_translation[header.field] : header.pattern}
    return [Bone(d, True), Bone({}, False)]

def compile_binary_predicate(switch, p, f):
    '''Compile f.left and f.right, then apply f to merge the results.'''
    assert(isinstance(p, netcore.Predicate))
    bonesLeft = compile_predicate(switch, p.left)
    bonesRight = compile_predicate(switch, p.right)
    return f(bonesLeft, bonesRight)

def compile_predicate(switch, p):
    '''
    Compile a NetCore predicate with respect to a given switch, 
    producing a list of Bones, wherein actions are True or False.
    '''
    assert(isinstance(p, netcore.Predicate))
    if isinstance(p, netcore.Top):
        return [Bone({}, True)]
    elif isinstance(p, netcore.Bottom):
        raise [Bone({}, False)]
    elif isinstance(p, netcore.Header):
        return compile_predicate_header(switch, p)
    elif isinstance(p, netcore.Union):
        return compile_binary_predicate(switch, p, compile_bones_union)
    elif isinstance(p, netcore.Intersection):
        return compile_binary_predicate(switch, p, compile_bones_intersection)
    elif isinstance(p, netcore.Difference):
        return compile_binary_predicate(switch, p, compile_bones_difference)
    else:
        raise ConstraintException("Unsupported predicate: %s" % p)

def compile_action(action):
    """
    Compile a NetCore action to a list of Policy actions.
    """
    assert(isinstance(action, netcore.Action))
    newActions = []

    # Convert any modify actions
    for k,v in action.modify.iteritems():
        newActions.append(policy.modify((k,v)))
    
    # Convert the forward action
    for p in action.ports:
        newActions.append(policy.forward(p))

    return newActions

def action_union(a1, a2):
    '''
    Return a new Action that is the union of Actions a1 and a2, or fail
    if such a union cannot be represented on the switches.

    Let (|) : Action -> Action -> Action
    be a union operator, defined as follows:

        _ | Controller = Controller
        Controller | _ = Controller
        (M1,F1) | (M2,F2) =
           { (M1, F1 U F2) if F2 == 0 or M1 == M2
           { (M2, F1 U F2) if F1 == 0 and M1 /= M2
           { Controller             otherwise

    '''
    assert(isinstance(a1, netcore.Action))
    assert(isinstance(a2, netcore.Action))

    if len(a2.ports) == 0 or a1.modify == a2.modify:
        assert(a1.switch is None or a2.switch is None or a1.switch == a2.switch)
        switch = a1.switch if a1.switch else a2.switch
        ports = list(a1.ports)
        ports.extend(a2.ports)
        return netcore.Action(switch, ports, a1.modify.copy())
    elif len(a1.ports) == 0 and a1.modify != a2.modify:
        assert(a1.switch is None or a2.switch is None or a1.switch == a2.switch)
        switch = a1.switch if a1.switch else a2.switch
        ports = list(a1.ports)
        ports.extend(a2.ports)
        return netcore.Action(switch, ports, a2.modify.copy())
    else:
        raise ConstraintException("Unsupported union of two Actions.")


def compile_policy_primitive(switch, p):
    assert(isinstance(p, netcore.PrimitivePolicy))

    predBones = compile_predicate(switch, p.predicate)
    bones = []
    for b in predBones:
        if b.action == True:
            bones.append(Bone(b.pattern, p.action))
        elif b.action == False:
            bones.append(Bone(b.pattern, netcore.Action(None)))
        else:
            raise ConstraintException("Unsupported truth value: %s" % b.action)
    return bones

def compile_policy_union(switch, p):
    assert(isinstance(p, netcore.PolicyUnion))
    bonesLeft = compile_policy(switch, p.left)
    bonesRight = compile_policy(switch, p.right)
    return bones_cross_product(bonesLeft, bonesRight, action_union)

def compile_policy_restriction(switch, p):
    assert(isinstance(p, netcore.PolicyRestriction))
    bonesPolicy = compile_policy(switch, p.policy)
    bonesPred = compile_predicate(switch, p.predicate)
    return bones_cross_product(bonesPred, 
                               bonesPolicy, 
                               lambda b, a: a if b else netcore.Action(None))

def compile_policy(switch, p):
    '''
    Compile a NetCore policy with respect to a given switch, producing a list 
    of Bones, where actions are lists of NetCore actions.
    '''
    assert(isinstance(p, netcore.Policy))

    if isinstance(p, netcore.PrimitivePolicy):
        return compile_policy_primitive(switch, p)
    elif isinstance(p, netcore.PolicyUnion):
        return compile_policy_union(switch, p)
    elif isinstance(p, netcore.PolicyRestriction):
        return compile_policy_restriction(switch, p)
    elif isinstance(p, netcore.BottomPolicy):
        return [Bone({}, netcore.Action(False))]
    else:
        raise ConstraintException("Unsupported policy type: %s" % p)

def pattern_is_subset(smaller, larger):
    '''
    Determine if all packets that match smaller will also match larger.
    '''
    assert(isinstance(smaller, type({})))
    assert(isinstance(larger, type({})))

    # TODO: handle wildcards
    for k in smaller:
        if k in larger and larger[k] != smaller[k]:
            return False
    for k in larger:
        if k not in smaller:
            return False
    return True

def translate_bones_to_rules(bones):
    '''
    Translate a list of Bones to a list of policy.Rules, where Bone actions
    are netcore.Actions.
    '''
    for b in bones:
        assert('loc' not in b.pattern)

    return [policy.Rule(policy.Pattern(old=p), acts) 
            for p, acts 
            in map(lambda b: (b.pattern, compile_action(b.action)), bones)]

def prune_predicate(switch, pred):
    assert(isinstance(pred, netcore.Predicate))
    if isinstance(pred, netcore.Top) or isinstance(pred, netcore.Bottom):
        return pred
    elif isinstance(pred, netcore.Header):
        if pred.field == 'loc' and pred.pattern[0] != switch:
            return netcore.Bottom()
        return pred
    elif isinstance(pred, netcore.Union):
        p1 = prune_predicate(switch, pred.left)
        p2 = prune_predicate(switch, pred.right)
        if isinstance(p1, netcore.Bottom):
            return p2
        elif isinstance(p2, netcore.Bottom):
            return p1
        return netcore.Union(p1, p2)
    elif isinstance(pred, netcore.Intersection):
        p1 = prune_predicate(switch, pred.left)
        p2 = prune_predicate(switch, pred.right)
        if isinstance(p1, netcore.Bottom) or isinstance(p2, netcore.Bottom):
            return netcore.Bottom()
        return netcore.Intersection(p1, p2)
    elif isinstance(pred, netcore.Difference):
        p1 = prune_predicate(switch, pred.left)
        p2 = prune_predicate(switch, pred.right)
        if isinstance(p1, netcore.Bottom):
            return netcore.Bottom()
        elif isinstance(p2, netcore.Bottom):
            return p1
        return netcore.Difference(p1, p2)
    else:
        raise ConstraintException("Unsupported predicate: %s" % p)

def prune_policy(switch, pol):
    assert(isinstance(pol, netcore.Policy))
    if isinstance(pol, netcore.BottomPolicy):
        return pol
    elif isinstance(pol, netcore.PrimitivePolicy):
        pred = prune_predicate(switch, pol.predicate)
        if isinstance(pred, netcore.Bottom):
            return netcore.BottomPolicy()
        return netcore.PrimitivePolicy(pred, pol.action)
    elif isinstance(pol, netcore.PolicyUnion):
        p1 = prune_policy(switch, pol.left)
        p2 = prune_policy(switch, pol.right)
        if isinstance(p1, netcore.BottomPolicy):
            return p2
        elif isinstance(p2, netcore.BottomPolicy):
            return p1
        return netcore.PolicyUnion(p1, p2)
    elif isinstance(pol, netcore.PolicyRestriction):
        p1 = prune_policy(switch, pol.policy)
        pred = prune_predicate(switch, pol.predicate)
        if isinstance(pred, netcore.Top):
            return p1
        elif isinstance(pred, netcore.Bottom):
            return netcore.BottomPolicy()
        elif isinstance(p1, netcore.BottomPolicy):
            return p1
        return netcore.PolicyRestriction(p1, pred)
    else:
        raise ConstraintException("Unsupported policy: %s" % p)

def compile(topo, pol):
    '''
    Compile a netcore.Policy and a topology to a policy.NetworkPolicy.

    ARGS
        topo: either an nxtopo or a list of switches.
        pol: a netcore.Policy object.

    RETURNS
        a policy.NetworkPolicy object.

    '''
    # TODO: remove
    global log
    log = open('/home/openflow/isolization-master/log.tmp', 'w')
    networkConfig = policy.NetworkPolicy()
    for switch in topo.switches():
        pruned_policy = prune_policy(switch, pol)
        bones = compile_policy(switch, pol)
        rules = translate_bones_to_rules(bones)
        networkConfig.set_configuration(switch, policy.SwitchConfiguration(rules))
    # TODO: remove
    log.close()
    return networkConfig

