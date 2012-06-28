#!/usr/bin/python
import sat
from netcore import then, Header, Action, forward, inport
import unittest

class SatTest(unittest.TestCase):
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

    def test_another1(self):
        o = Header({'switch': 0, 'port': 1}) |then| Action(0, [1])
        r = Header({'switch': 0, 'port': 1, 'vlan': 1}) |then| Action(0, [1], {'vlan': 1})
        self.assertTrue(sat.compiled_correctly(o, r))

if __name__ == '__main__':
    unittest.main()
