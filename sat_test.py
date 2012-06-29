#!/usr/bin/python
import sat
from netcore import then, Header, Action, forward, inport, BottomPolicy
import unittest

class SatTest(unittest.TestCase):
    def test_compiled_correctly(self):
        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        self.assertIsNone(sat.simulates(o, r))
        self.assertIsNone(sat.simulates(r, o))
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 2, 'port': 2}) |then| Action(2, [1])
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1])
        self.assertIsNone(sat.simulates(o, r, ['vlan']))
        self.assertIsNone(sat.simulates(r, o))
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 2, 'port': 2}) |then| forward(2, 1)
        r = Header({'switch': 2, 'port': 2, 'vlan': 2}) |then| Action(2, [1], {'vlan': 2})
        self.assertIsNone(sat.simulates(o, r, ['vlan']))
        self.assertIsNone(sat.simulates(r, o))
        self.assertTrue(sat.compiled_correctly(o, r))

        o = Header({'switch': 0, 'port': 1}) |then| Action(0, [1])
        r = Header({'switch': 0, 'port': 1, 'vlan': 1}) |then| Action(0, [1], {'vlan': 1})
        self.assertIsNone(sat.simulates(o, r, ['vlan']))
        self.assertIsNone(sat.simulates(r, o))
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
