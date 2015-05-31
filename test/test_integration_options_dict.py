import sys
sys.path.append('..')

import unittest
from options_dict import OptionsDict, CallableEntry
from tree_elements import OptionsNode, OptionsArray


class TestOptionsDictInteractionsWithNode(unittest.TestCase):

    def setUp(self):
        self.node = OptionsNode('foo')
        self.od = OptionsDict(entries={'bar': 1})

    def test_donate_copy(self):
        """
        Passing a node to OptionsDict's donate_copy method should furnish
        the node with dictionary information.
        """
        od_init = self.od.copy()
        self.node, remainder = self.od.donate_copy(self.node)
        node_od = self.node.collapse()[0]
        self.assertEqual(node_od['bar'], 1)
        self.assertEqual(len(remainder), 0)


class TestOptionsDictAfterTreeCollapse(unittest.TestCase):

    def setUp(self):
        """
        Run tests on this tree:
        0: a
            1: a
                2: a
                2: b
                2: c
            1: b
                2: a
                2: b
                2: c
        """
        self.tree = OptionsArray('0', ['a']) * \
                    OptionsArray('1', ['a', 'b']) * \
                    OptionsArray('2', ['a', 'b', 'c'])
        
#     def test_tree_str(self):
#         # import pdb
#         # pdb.set_trace()
#         ods = self.tree.collapse()
#         expected = """
# 0: a
#     1: a
#         2: a
#         2: b
#         2: c
#     1: b
#         2: a
#         2: b
#         2: c"""
#         result = ''
#         for od in ods:
#             result += '\n' + od.tree_str()
#         print result
#         self.assertEqual(result, expected)
        
        
class TestCallableEntry(unittest.TestCase):
    
    def test_callable_entry(self):
        """
        I create an OptionsDict with a callable entry stored under
        'my_func'.  This should not evaluate like a dynamic entry but
        instead remain intact and work as intended.
        """
        od = OptionsDict({
            'my_func': CallableEntry(lambda a, b=1: a + b)})
        self.assertIsInstance(od['my_func'], CallableEntry)
        self.assertEqual(od['my_func'](1), 2)
        self.assertEqual(od['my_func'](1, 2), 3)

        
if __name__ == '__main__':
    unittest.main()