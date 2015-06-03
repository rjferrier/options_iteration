import sys
sys.path.append('..')

import unittest
import os
from unit_options_dict import UnitOptionsDict
from options_dict import freeze, OptionsDictException, NodeInfoException


class TestOptionsDictCreation(unittest.TestCase):

    def test_create_from_dict(self):
        """
        When I create an OptionsDict from a dict, there is no error.
        """
        UnitOptionsDict({'foo': 'bar'})

    def test_create_from_dynamic_entries(self):
        """
        When I create an OptionsDict from a list of functions, there
        is no error.
        """
        def foo(opt):
            return 'bar'
        UnitOptionsDict([foo])

    def test_create_from_non_dict(self):
        """
        When I create an OptionsDict using something other than a dict
        or a list of functions, an error should be raised.
        """
        create_od = lambda: UnitOptionsDict('foo')
        self.assertRaises(OptionsDictException, create_od)


class TestOptionsDictBasics(unittest.TestCase):
    
    def setUp(self):
        "I create an anonymous OptionsDict."
        self.od = UnitOptionsDict(entries={'foo': 'bar'})
        
    def test_equal(self):
        self.assertEqual(self.od, UnitOptionsDict({'foo': 'bar'}))

    def test_unequal(self):
        self.assertNotEqual(self.od, UnitOptionsDict({'baz': 'bar'}))

    def test_node_info_empty(self):
        self.assertRaises(NodeInfoException, lambda: self.od.get_node_info())
    
    def test_set_and_get_node_info(self):
        od = UnitOptionsDict({'foo': 'bar'})
        ni = od.create_orphan_node_info('foo')
        # ni should be some throwaway value
        self.assertIsNotNone(ni)
        od.set_node_info(ni)
        self.assertEqual(ni, od.get_node_info())
        
    def test_copy(self):
        other = self.od.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.od)
        self.assertFalse(other is self.od)
        # test that entries have been copied and not simply linked (we
        # do not guarantee that their components have been
        # deep-copied, however)
        other.update(UnitOptionsDict({'foo': 'baz'}))
        self.assertNotEqual(other, self.od)

        
        
class TestOptionsDictDynamicEntries(unittest.TestCase):
    
    def setUp(self):
        """
        I create an OptionsDict with two variables: kinematic_viscosity
        and pipe_diameter.  I define Reynolds_number, which is a dynamic
        entry dependent on velocity, pipe_diameter and
        kinematic_viscosity.  I haven't defined velocity yet.
        """
        self.od = UnitOptionsDict({
            'kinematic_viscosity': 1.e-6,
            'pipe_diameter'      : 0.1 })
        def Reynolds_number(d):
            return d['velocity'] * d['pipe_diameter'] / \
                d['kinematic_viscosity']
        self.od.update([Reynolds_number])

    def test_missing_information_raises_error(self):
        """
        I try and obtain Reynolds_number before velocity is defined.  A
        KeyError should be raised.
        """
        self.assertRaises(KeyError, 
                          lambda: self.od['Reynolds_number'])

    def test_dynamic_entry(self):
        """
        I define velocity and change one the variables.
        Reynolds_number should update automatically.
        """
        self.od['velocity'] = 0.02
        self.assertAlmostEqual(self.od['Reynolds_number'], 2000.)
        self.od['pipe_diameter'] = 0.15
        self.assertAlmostEqual(self.od['Reynolds_number'], 3000.)

    def test_nested_entry(self):
        """
        I add an 'observation' entry which depends on Reynolds_number.
        When velocity is changed, observation should update
        automatically.
        """
        def observation(d):
            if d['Reynolds_number'] < 2100.:
                return 'laminar'
            elif d['Reynolds_number'] > 4000.:
                return 'turbulent'
            else:
                return 'transitional'
        # modify the dict
        self.od.update([observation])
        # now test
        self.od['velocity'] = 0.02
        self.assertEqual(self.od['observation'], 'laminar')
        self.od['velocity'] = 0.05
        self.assertEqual(self.od['observation'], 'turbulent')
        
    def test_nested_object(self):
        """
        Suppose I use self.od to create a new OptionsDict.  The new
        object should be equivalent, but not identical to, the old
        object.  That is, it should be a copy.
        """
        self.od['velocity'] = 0.
        dd = UnitOptionsDict(self.od)
        # test for equivalence and non-identity
        self.assertEqual(dd, self.od)
        self.assertFalse(dd is self.od)
        # try changing the new object.  Its options entries should
        # update accordingly, while the old object should be unaffected
        dd['velocity'] = 0.02
        self.assertAlmostEqual(dd['Reynolds_number'], 2000.)
        self.assertAlmostEqual(self.od['Reynolds_number'], 0.)

    def test_freeze(self):
        """
        I set velocity, which should in turn set the Reynolds_number.
        However, after I freeze the dictionary, redefining velocity
        should not redefine the Reynolds number.
        """
        self.od['velocity'] = 0.02
        self.assertAlmostEqual(self.od['Reynolds_number'], 2000.)
        self.od.freeze()
        self.od['velocity'] = 0.04
        self.assertAlmostEqual(self.od['Reynolds_number'], 2000.)

    def test_freeze_list(self):
        """
        Same as test_freeze, but I use the options_dict module's freeze
        function to work on a list.
        """
        self.od['velocity'] = 0.02
        self.assertAlmostEqual(self.od['Reynolds_number'], 2000.)
        ods = freeze([self.od] * 3)
        ods[2]['velocity'] = 0.04
        self.assertAlmostEqual(ods[2]['Reynolds_number'], 2000.)
        

class TestOptionsDictTemplateExpansion(unittest.TestCase):

    def setUp(self):
        self.od = UnitOptionsDict({'fluid'         : 'water',
                                   'melting_point' :       0,
                                   'boiling_point' :     100})

    def test_expand_string(self):
        template = "$fluid has a melting point of $melting_point"+\
                   " degrees C."
        expected = "water has a melting point of 0 degrees C."
        self.assertEqual(self.od.expand_template_string(template), expected)

    def test_expand_string_missing_entry(self):
        template = "$fluid has a density of $density kg/m^3."
        expected = "water has a density of $density kg/m^3."
        self.assertEqual(self.od.expand_template_string(template), expected)


    def test_expand_nested(self):
        template = "$fluid has a $change point of ${${change}_point}"+\
                   " degrees C."
        
        self.od['change'] = 'melting'
        expected = "water has a melting point of 0 degrees C."
        self.assertEqual(self.od.expand_template_string(template, loops=2),
                         expected)
        
        self.od['change'] = 'boiling'
        expected = "water has a boiling point of 100 degrees C."
        self.assertEqual(self.od.expand_template_string(template, loops=2),
                         expected)

        
    def test_expand_not_enough_loops(self):
        template = "$fluid has a $change point of ${${change}_point}"+\
                   " degrees C."
        
        self.od['change'] = 'melting'
        expected = "water has a melting point of ${melting_point}"+\
                   " degrees C."
        self.assertEqual(self.od.expand_template_string(template),
                         expected)

        
    
if __name__ == '__main__':
    unittest.main()
        
