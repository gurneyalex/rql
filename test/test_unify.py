""" Copyright (c) 2003-2005 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from logilab.common.testlib import TestCase, unittest_main

from rql import RQLHelper, TypeResolverException
from rql.analyze import UnifyingETypeResolver

from unittest_analyze import DummySchema
        
UNRESOLVABLE_QUERIES = (
    'Person X WHERE Y work_for X',
    'Person X WHERE X work_for Y, Y is "Address"',
    'Insert Company X : X name "toto", X work_for Y WHERE Y name "logilab"',
    )

DEBUG = 0

class AnalyzerClassTest(TestCase):
    """check wrong queries arre correctly detected
    """

    def setUp(self):
        self.skip('need update')
        self.helper = RQLHelper(DummySchema(), None)
        
    def test_base_1(self):
        node = self.helper.parse('Any X')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Address'},
                                {'X': 'Company'},
                                {'X': 'Person'}])
    
    def test_base_2(self):
        node = self.helper.parse('Person X')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Person'}])
    
    def test_base_guess_1(self):
        node = self.helper.parse('Person X WHERE X work_for Y')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'}])
    
    def test_base_guess_2(self):
        node = self.helper.parse('Any X WHERE X name "Logilab"')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Company'}, {'X': 'Person'}])

    def test_not(self):
        node = self.helper.parse('Any X WHERE not X is "Person"')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Address'}, {'X': 'Boolean'}, {'X': 'Company'}, {'X': 'Date'}, {'X': 'Float'}, {'X': 'Int'}, {'X': 'String'}])

    def test_uid_func_mapping(self):
        node = self.helper.parse('Any X WHERE X name "Logilab"')
        uid_func_mapping = {'name': lambda uid: 'Company' }
        sols = self.helper.get_solutions(node, uid_func_mapping, debug=DEBUG)
        self.assertEqual(sols, [{'X': 'Company'}])
        
        node = self.helper.parse('Any N WHERE X name N')
        uid_func_mapping = {'name': lambda uid: 'Company' }
        sols = self.helper.get_solutions(node, uid_func_mapping, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Company', 'N': 'String'},
                                {'X': 'Person', 'N': 'String'}])

    def test_base_guess_3(self):
        node = self.helper.parse('Any Z WHERE X name Z GROUPBY Z')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Company', 'Z': 'String'},
                                {'X': 'Person', 'Z': 'String'}])

    def test_var_name(self):
        node = self.helper.parse('Any E1 WHERE E2 is Person, E2 name E1 GROUPBY E1')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'E2': 'Person', 'E1': 'String'}])

    def test_insert_1(self):
        node = self.helper.parse('Insert Person X : X name "toto", X work_for Y WHERE Y name "logilab"')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        sols.sort()
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'}])

    def test_raise(self):
        for rql in UNRESOLVABLE_QUERIES:
            if DEBUG:
                print rql
            node = self.helper.parse(rql)
            self.assertRaises(TypeResolverException, self.helper.get_solutions, node, debug=DEBUG)
            

if __name__ == '__main__':
    unittest_main()
