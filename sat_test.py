#!/usr/bin/python
import sat
from netcore import then, Header, Action, forward, inport, BottomPolicy
import unittest

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
        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1])
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 2, 'port': 2}) |then| forward(2, 1)
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1], {'vlan': 2})
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 0, 'port': 1}) |then| Action(0, [1])
        r = Header({'switch': 0, 'port': 1, 'vlan': 1}) |then| Action(0, [1], {'vlan': 1})
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 0, 'port': 1, 'srcmac': 32432, 'dstmac': 324322}) |then| Action(0, [1])
        r = Header({'switch': 0, 'port': 1, 'srcmac': 32432, 'dstmac': 324322, 'vlan': 1}) |then| Action(0, [1], {'vlan': 1})
        self.assertTrue(sat.compiled_correctly(o, r))

    def test_compiled_badly(self):
        o = Header({'switch': 2, 'port': 1}) |then| Action(2, [1])
        r = BottomPolicy()
        self.assertFalse(sat.compiled_correctly(o, r))

        o = Header({'switch': 2, 'port': 1}) |then| Action(2, [1])
        r = Header({'switch': 1, 'port': 1}) |then| Action(2, [1])
        self.assertFalse(sat.compiled_correctly(o, r))


if __name__ == '__main__':
    unittest.main()
