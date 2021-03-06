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
import updates.policy as policy
import logging

# Translation from NetCore to policy.py header names.
FIELD_TRANSLATION = {
  'port': policy.Pattern.IN_PORT,
  'srcmac' : policy.Pattern.DL_SRC,
  'dstmac' : policy.Pattern.DL_DST,
  'ethtype' : policy.Pattern.DL_TYPE,
  'srcip' : policy.Pattern.NW_SRC,
  'dstip' : policy.Pattern.NW_DST,
  'vlan' : policy.Pattern.DL_VLAN,
  'protocol' : policy.Pattern.NW_PROTO,
  'srcport' : policy.Pattern.TP_SRC,
  'dstport' : policy.Pattern.TP_DST
  }

def translate_fields(fields):
    """Convert {netcore_field: value} -> {policy_field: value}.

    Removes switch from the field.
    """
    output = {}
    for k, v in fields.items():
        if k is not 'switch':
            output[FIELD_TRANSLATION[k]] = v
    return output

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
        action  : either True/False/Maybe, in the first phase, or a list of
                  netcore.Action objects in the second.
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
        bones: a list of Bones with arbitrary actions.

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

    # Disallow wildcards for now
#    try:
#        if header.field != 'loc':
#            int(header.pattern)
#    except ValueError:
#        raise ConstraintException(
#          "Pattern in '%s' is not a number (wildcards currently disallowed)." % header)

    fields = header.fields
    if 'switch' in fields:
        sw = fields['switch']
        switchMatches = (sw == switch)
    else:
        switchMatches = True
    d = translate_fields(fields)
    if len(d) > 0:
        return [Bone(d, switchMatches), Bone({}, False)]
    else:
        return [Bone(d, switchMatches)]

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
        return [Bone({}, False)]
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
        newActions.append(policy.modify((FIELD_TRANSLATION[k],v)))

    # Convert the forward action
    for p in action.ports:
        newActions.append(policy.forward(p))

    return newActions

def pattern_cmp(p1, p2):
    '''
    Compare patterns p1 and p2.

    RETURN
        -1 if p1 is a subset of p2
         0 if p1 == p2
         1 if p2 is a subset of p1

    EXCEPTIONS
        Raise a ConstraintException if p1 and p2 are incomparable.

    '''
    if pattern_is_subset(p1, p2):
        return -1
    elif p1 == p2:
        return 0
    elif pattern_is_subset(p2, p1):
        return 1

    # TODO: find a better way to report this error
    raise ConstraintException("Illegal pattern comparison.")

def compile_actions(actions):
    """
    Compile a list of NetCore actions (where the output is the union
    of the actions in the list) or fail if the actions cannot be
    represented on the switches.
    """
    assert(isinstance(actions, type([])))
    # Fail if we cannot establish a subset ordering on the modifications
    # of each action.
    # i.e. it is safe to do
    #   (VLAN = 1, Forward 1), (VLAN = 1 IP = 2, Forward 2)
    actions.sort(cmp=pattern_cmp, key=(lambda action: action.modify))

    # Flatten the list of Action objects
    action_lists = [compile_action(action) for action in actions]
    return [action for sublist in action_lists for action in sublist]

def action_union(a1, a2):
    # TODO: dead code?
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

def actions_union(l1, l2):
    '''
    Return a new list of Actions that is the union of Actions in l1 and l2,
    or fail if such a union cannot be represented on the switches.
    '''
    assert(isinstance(l1, type([])))
    assert(isinstance(l2, type([])))
    # Try compiling, just to see if we can.
    discard = compile_actions(l1 + l2)
    return l1 + l2

def compile_policy_primitive(switch, p):
    assert(isinstance(p, netcore.PrimitivePolicy))

    predBones = compile_predicate(switch, p.predicate)
    bones = []
    for b in predBones:
        if b.action == True:
            bones.append(Bone(b.pattern, p.actions))
        elif b.action == False:
            bones.append(Bone(b.pattern, []))
        else:
            raise ConstraintException("Unsupported truth value: %s" % b.action)
    return bones

def compile_policy_union(switch, p):
    assert(isinstance(p, netcore.PolicyUnion))
    bonesLeft = compile_policy(switch, p.left)
    bonesRight = compile_policy(switch, p.right)
    return bones_cross_product(bonesLeft, bonesRight, actions_union)

def compile_policy_restriction(switch, p):
    assert(isinstance(p, netcore.PolicyRestriction))
    bonesPolicy = compile_policy(switch, p.policy)
    bonesPred = compile_predicate(switch, p.predicate)
    return bones_cross_product(bonesPred,
                               bonesPolicy,
                               lambda b, a: a if b else [])

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
        return [Bone({}, [])]
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
    are lists of netcore.Actions.
    '''
    for b in bones:
        assert('loc' not in b.pattern)

    return [policy.Rule(policy.Pattern(old=p), acts)
            for p, acts
            in map(lambda b: (b.pattern, compile_actions(b.action)), bones)]

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
        raise ConstraintException("Unsupported predicate: %s" % pred)

def prune_policy(switch, pol):
    assert(isinstance(pol, netcore.Policy))
    if isinstance(pol, netcore.BottomPolicy):
        return pol
    elif isinstance(pol, netcore.PrimitivePolicy):
        pred = prune_predicate(switch, pol.predicate)
        if isinstance(pred, netcore.Bottom):
            return netcore.BottomPolicy()
        return netcore.PrimitivePolicy(pred, pol.actions)
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
        raise ConstraintException("Unsupported policy: %s" % pred)

def compile(topo, pol):
    '''
    Compile a netcore.Policy and a topology to a policy.NetworkPolicy.

    ARGS
        topo: either an nxtopo or a list of switches.
        pol: a netcore.Policy object.

    RETURNS
        a policy.NetworkPolicy object.

    '''
    logger = logging.getLogger('isolation')
    networkConfig = policy.NetworkPolicy()
    i = 1
    l = len(topo.switches())
    for switch in topo.switches():
        logger.debug('... Switch %s / %s:' % (i, l))
        i += 1

        # Prune w.r.t. this switch
        logger.debug('... pruning policy.')
        pruned_policy = prune_policy(switch, pol)

        # Compile to bones
        logger.debug('... compiling policy.')
        bones = compile_policy(switch, pol)

        # Translate bones to rules
        logger.debug('... translating bones to rules.')
        rules = translate_bones_to_rules(bones)

        networkConfig.set_configuration(switch, policy.SwitchConfiguration(rules))
    return networkConfig

