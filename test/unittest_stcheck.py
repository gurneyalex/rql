""" Copyright (c) 2003-2004 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from logilab.common.testlib import TestCase, unittest_main

from rql import RQLHelper, BadRQLQuery

class DummySchema:
    def has_entity(self, e_type):
        if e_type == 'Missing':
            return 0
        return 1
    def has_relation(self, r_type):
        if r_type == 'nonexistant':
            return 0
        return 1
    def entities(self):
        return ['Person']
    def relations(self):
        return []
    
BAD_QUERIES = (
    'Any X, Y GROUPBY X',
    
    'DISTINCT Any X WHERE X related Y ORDERBY Y',
    
    'Missing X',
    
    'Any X WHERE X is "Missing"',

    'Any X WHERE X nonexistant Y',
    
    'Any X WHERE X name Person',
    
    'Any X WHERE X name nofunction(Y)',

    'Any X WHERE X name nofunction(Y)',
    
    'Any Y WHERE X name "toto"',
    
    'Any UPPER(Y) WHERE X name "toto"',

    'Any C where C suivi_par P, P eid %(x)s ORDERBY N', #15066

#    'Any COUNT(X),P WHERE X concerns P', #9726
    )

class CheckClassTest(TestCase):
    """check wrong queries arre correctly detected
    """
    
    def setUp(self):
        self.parse = RQLHelper(DummySchema(), None).parse
        
    def _test(self, rql):
        try:
            self.parse(rql)
        except Exception, ex:
            print rql, ex
        try:
            self.assertRaises(BadRQLQuery, self.parse, rql)
        except:
            print rql
            raise
        
    def test_raise(self):
        for rql in BAD_QUERIES:
            yield self._test, rql
        
if __name__ == '__main__':
    unittest_main()
