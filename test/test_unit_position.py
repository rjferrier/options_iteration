import sys
sys.path.append('..')

import unittest
from options import Position


class TestPositionString(unittest.TestCase):

    def setUp(self):
        """
        With a sequence of nodes named 'A', 'B' and 'C', I create a
        Position for the second node.
        """
        self.pos = Position(['A', 'B', 'C'], 1)

    def test_repr(self):
        self.assertEqual(repr(self.pos),
                         "Position(['A', 'B', 'C'], 1)")

    def test_node_name(self):
        """
        I should be able to recover the name of the node from both 
        __str__ and str() methods.
        """
        self.assertEqual(self.pos.str(), 'B')
        self.assertEqual(str(self.pos), 'B')

    def test_other_node_name_from_absolute_index(self):
        """
        I should be able to recover the name of another node using an
        absolute index.  This will follow the usual Python indexing
        convention where a minus sign denotes position from the end.
        If the index runs past the end, an IndexError should be
        raised.
        """
        self.assertEqual(self.pos.str(0), 'A')
        self.assertEqual(self.pos.str(-1), 'C')
        self.assertRaises(IndexError, lambda: self.pos.str(3))

    def test_other_node_name_from_relative_index(self):
        """
        I should be able to recover the name of another node using a
        relative index.  If it runs past the beginning, an IndexError
        should be raised.
        """
        self.assertEqual(self.pos.str(relative=-1), 'A')
        self.assertRaises(IndexError,
                          lambda: self.pos.str(relative=-2))

    def test_other_node_name_from_relative_and_absolute_index(self):
        """
        Using both a relative and absolute index should also work.
        A resulting negative index raises an IndexError.
        """
        self.assertEqual(self.pos.str(relative=-1, absolute=2), 'B')
        self.assertRaises(
            IndexError, lambda: self.pos.str(relative=-2, absolute=1))


class TestPositionEnds(unittest.TestCase):
    
    def setUp(self):
        """
        With a sequence of nodes named 'A', 'B' and 'C', I create
        Positions for all three nodes.  I'll want to know which of
        these represent the start or end of the sequence.
        """
        seq = ['A', 'B', 'C']
        self.a = Position(seq, 0)
        self.b = Position(seq, 1)
        self.c = Position(seq, 2)
    
    def test_at(self):
        # check position from start
        self.assertTrue(self.b.at(1))
        self.assertFalse(self.b.at(2))
        # check position from end
        self.assertTrue(self.b.at(-2))
        self.assertFalse(self.b.at(-1))
    
    def test_is_first(self):
        self.assertTrue(self.a.is_first())
        self.assertFalse(self.b.is_first())
        self.assertFalse(self.c.is_first())
    
    def test_is_last(self):
        self.assertFalse(self.a.is_last())
        self.assertFalse(self.b.is_last())
        self.assertTrue(self.c.is_last())


        
if __name__ == '__main__':
    unittest.main()
        
