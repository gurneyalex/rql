""" Copyright (c) 2003-2004 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: unittest_stcheck.py,v 1.9 2004-06-30 06:39:59 syt Exp $"

import unittest
import sys

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
    )

class CheckClassTest(unittest.TestCase):
    """check wrong queries arre correctly detected
    """
    
    def setUp(self):
        self.parse = RQLHelper(DummySchema(), None).parse
        
    
    def test_raise(self):
        for rql in BAD_QUERIES:
            #print rql
            self.assertRaises(BadRQLQuery, self.parse, rql)
        
if __name__ == '__main__':
    unittest.main()
