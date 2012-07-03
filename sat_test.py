#!/usr/bin/python
import sat
from netcore import then, Header, Action, forward, inport, BottomPolicy
import nxtopo
import unittest

topo = nxtopo.NXTopo()
topo.add_switch(1)
topo.add_switch(2)
topo.add_switch(3)
topo.add_switch(4)
topo.add_switch(5)

topo.add_link(1, 2)
topo.add_link(2, 3)
topo.add_link(3, 4)
topo.add_link(4, 5)
topo.finalize()

class SatTest(unittest.TestCase):
    def test_forwards(self):
        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        self.assertIsNone(sat.simulates_forwards(o, r))
        self.assertIsNone(sat.simulates_forwards(r, o))

        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1])
        self.assertIsNone(sat.simulates_forwards(o, r))
        self.assertIsNone(sat.simulates_forwards(r, o))

        o = Header({'switch': 2, 'port': 2}) |then| forward(2, 1)
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1], {'vlan': 2})
        self.assertIsNone(sat.simulates_forwards(o, r))
        self.assertIsNone(sat.simulates_forwards(r, o))

        o = Header({'switch': 0, 'port': 1}) |then| Action(0, [1])
        r = Header({'switch': 0, 'port': 1, 'vlan': 1}) |then| Action(0, [1], {'vlan': 1})
        self.assertIsNone(sat.simulates_forwards(o, r))
        self.assertIsNone(sat.simulates_forwards(r, o))

        o = Header({'switch': 0, 'port': 1, 'srcmac': 32432, 'dstmac': 324322}) |then| Action(0, [1])
        r = Header({'switch': 0, 'port': 1, 'srcmac': 32432, 'dstmac': 324322, 'vlan': 1}) |then| Action(0, [1], {'vlan': 1})
        self.assertIsNone(sat.simulates_forwards(o, r))
        self.assertIsNone(sat.simulates_forwards(r, o))

    def test_observes(self):
        o = BottomPolicy()
        r = BottomPolicy()
        self.assertIsNone(sat.simulates_observes(o, r))

        o = Header({'switch': 1, 'port': 1}) |then| Action(1, [2], obs=[0])
        r = Header({'switch': 1, 'port': 1, 'vlan': 1}) |then|\
            Action(1, [2], obs=[0])
        self.assertIsNone(sat.simulates_observes(o, r))

        o = Header({'switch': 1, 'port': 1}) |then| Action(1, [2])
        r = Header({'switch': 1, 'port': 1, 'vlan': 1}) |then|\
            Action(1, [2], obs=[0])
        self.assertIsNone(sat.simulates_observes(o, r))

        o = Header({'switch': 1, 'port': 1}) |then| Action(1, [2], obs=[0])
        r = Header({'switch': 1, 'port': 1, 'vlan': 1}) |then|\
            Action(1, [2])
        self.assertIsNotNone(sat.simulates_observes(o, r))

    def test_compiled_correctly(self):
        o = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1])
        self.assertTrue(sat.compiled_correctly(topo, o, r))

        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1])
        self.assertTrue(sat.compiled_correctly(topo, o, r))

        o = Header({'switch': 2, 'port': 2}) |then| forward(2, 1)
        r = Header({'switch': 2, 'port': 2, 'vlan': 2})\
            |then| Action(2, [1], {'vlan': 2})
        self.assertTrue(sat.compiled_correctly(topo, o, r))

        o = Header({'switch': 1, 'port': 1}) |then| Action(1, [1])
        r = Header({'switch': 1, 'port': 1, 'vlan': 1}) |then|\
            Action(1, [1], {'vlan': 1})
        self.assertTrue(sat.compiled_correctly(topo, o, r))

        o = Header({'switch': 1, 'port': 1, 'srcmac': 33, 'dstmac': 32})\
            |then| Action(1, [1])
        r = Header({'switch': 1, 'port': 1, 'srcmac': 33, 'dstmac': 32, 'vlan': 1})\
            |then| Action(1, [1], {'vlan': 1})
        self.assertTrue(sat.compiled_correctly(topo, o, r))

    def test_compiled_badly(self):
        o = Header({'switch': 2, 'port': 1}) |then| Action(2, [1])
        r = BottomPolicy()
        self.assertFalse(sat.compiled_correctly(topo, o, r))

        o = Header({'switch': 2, 'port': 1}) |then| Action(2, [1])
        r = Header({'switch': 1, 'port': 1}) |then| Action(2, [1])
        self.assertFalse(sat.compiled_correctly(topo, o, r))

    def test_simulates_forwards2(self):
        o = (Header({'switch': 2, 'port': 1}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1}) |then| forward(3, 2))
        r = (Header({'switch': 2, 'port': 1, 'vlan': 2}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 2}) |then| forward(3, 2))
        self.assertIsNone(sat.simulates_forwards2(topo, o, r))
        self.assertIsNotNone(sat.simulates_forwards2(topo, o, r, field='srcmac'))

        o = (Header({'switch': 2, 'port': 1, 'vlan': 1}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 1}) |then| forward(3, 2))
        r = (Header({'switch': 2, 'port': 1, 'vlan': 2}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 2}) |then| forward(3, 2))
        self.assertIsNone(sat.simulates_forwards2(topo, o, r))
        self.assertIsNotNone(sat.simulates_forwards2(topo, o, r, field='srcmac'))

        # This is the corner case that demonstrates that we need to restrict
        # compiled policies to only one vlan per slice.
        o = (Header({'switch': 2, 'port': 1}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1}) |then| forward(3, 2))+\
            (Header({'switch': 4, 'port': 1}) |then| forward(4, 2))
        r = (Header({'switch': 2, 'port': 1, 'vlan': 1}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 1}) |then| forward(3, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 2}) |then| forward(3, 2))+\
            (Header({'switch': 4, 'port': 1, 'vlan': 2}) |then| forward(4, 2))
        self.assertIsNone(sat.simulates_forwards(o, r))
        # NOTE: We would really like this to be a failure, but it isn't.
        # Therefore, for compiler correctness, we also need one vlan per edge.
        self.assertIsNone(sat.simulates_forwards2(topo, o, r))
        self.assertIsNotNone(sat.simulates_forwards2(topo, o, r, field='srcmac'))

        # And verify that the compilation test finds this failure
        self.assertFalse(sat.compiled_correctly(topo, o, r))

    def test_one_per_edge(self):
        topo = nxtopo.NXTopo()
        topo.add_switch(1)
        topo.add_switch(2)
        topo.add_switch(3)
        topo.add_switch(4)
        topo.add_switch(5)

        topo.add_link(1, 2)
        topo.add_link(2, 3)
        topo.add_link(3, 4)
        topo.add_link(4, 5)
        topo.finalize()

        r = (Header({'switch': 2, 'port': 1, 'vlan': 2}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 2}) |then| forward(3, 2))
        self.assertIsNone(sat.one_per_edge(topo, r))
        self.assertIsNotNone(sat.one_per_edge(topo, r, field='srcmac'))

        r = (Header({'switch': 2, 'port': 1, 'vlan': 1}) |then| forward(2, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 1}) |then| forward(3, 2))+\
            (Header({'switch': 3, 'port': 1, 'vlan': 2}) |then| forward(3, 2))+\
            (Header({'switch': 4, 'port': 1, 'vlan': 2}) |then| forward(4, 2))
        self.assertIsNotNone(sat.one_per_edge(topo, r))
        self.assertIsNotNone(sat.one_per_edge(topo, r, field='srcmac'))

if __name__ == '__main__':
    unittest.main()
