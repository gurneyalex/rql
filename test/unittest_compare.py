""" Copyright (c) 2000-2003 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: unittest_compare.py,v 1.7 2006-02-20 02:06:09 ludal Exp $"

import unittest
import sys

from rql import RQLHelper
from unittest_analyze import RelationSchema, EntitySchema, DummySchema as BaseSchema

class DummySchema(BaseSchema):
    _types = BaseSchema._types
    
    for type in ['Note',]:
        _types[type] = EntitySchema(type)

    _relations = BaseSchema._relations
    
    _relations['a_faire_par'] = RelationSchema( ( ('Note', ('Person',)),
                                                  )
                                                )
    _relations['creation_date'] = RelationSchema( ( ('Note', ('Date',)),
                                                  )
                                                )
    _relations['nom'] = _relations['name']
    _relations['prenom'] = _relations['firstname']
    
class RQLCompareClassTest(unittest.TestCase):
    """ Compare RQL strings """
    
    def setUp(self):
        self.h = RQLHelper(DummySchema(), None)
        
    def _compareEquivalent(self,r1,r2):
        """fails if the RQL strings r1 and r2 are equivalent"""
        self.failUnless(self.h.compare(r1, r2),
                        'r1: %s\nr2: %s' % (r1, r2))

    def _compareNotEquivalent(self,r1,r2):
        """fails if the RQL strings r1 and r2 are not equivalent"""
        self.failIf(self.h.compare(r1, r2),
                    'r1: %s\nr2: %s' % (r1, r2))

    # equivalent queries ##################################################

    def test_same_request_simple(self):
        r = "Any X where X is Note ;"
        self._compareEquivalent(r, r)

    def test_same_request_diff_names(self):
        r1 = "Any X ;"
        r2 = "Any Y ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_diff_names_simple(self):
        r1 = "Any X where X is Note ;"
        r2 = "Any Y where Y is Note ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_any(self):
        r1 = "Any X where X is Note ;"
        r2 = "Note X ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_any_diff_names(self):
        r1 = "Any X where X is Note ;"
        r2 = "Note Y ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_complex(self):
        r = "Any N, N2 where N is Note, N2 is Note, N a_faire_par P1, P1 nom 'jphc', N2 a_faire_par P2, P2 nom 'ocy' ;"
        self._compareEquivalent(r, r)

    def test_same_request_comma_and(self):
        r1 = "Any N, N2 where N is Note, N2 is Note, N a_faire_par P1, P1 nom 'jphc', N2 a_faire_par P2, P2 nom 'ocy' ;"
        r2 = "Any N, N2 where N is Note AND N2 is Note AND N a_faire_par P1 AND P1 nom 'jphc' AND N2 a_faire_par P2 AND P2 nom 'ocy' ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_diff_names_complex(self):
        r1 = "Any N, N2 where N is Note, N2 is Note, N a_faire_par P1, P1 nom 'jphc', N2 a_faire_par P2, P2 nom 'ocy' ;"
        r2 = "Any Y, X  where X is Note, Y is Note,  X a_faire_par A1, A1 nom 'ocy',  Y a_faire_par A2,  A2 nom 'jphc' ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_diff_order(self):
        r1 = "Any N, N2 where N is Note, N2 is Note, N a_faire_par P1, P1 nom 'jphc', N2 a_faire_par P2, P2 nom 'ocy' ;"
        r2 = "Any N, N2 where N2 is Note, N is Note, N a_faire_par P1, N2 a_faire_par P2, P2 nom 'ocy', P1 nom 'jphc' ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_diff_order_diff_names(self):
        r1 = "Any N, N2 where N is Note, N2 is Note, N a_faire_par P1, P1 nom 'jphc', N2 a_faire_par P2, P2 nom 'ocy' ;"
        r2 = "Any Y, X  where X is Note, X a_faire_par P1, P1 nom 'ocy', Y is Note,    Y a_faire_par P2,  P2 nom 'jphc' ;"
        self._compareEquivalent(r1, r2)

    def test_same_request_with_comparison(self):
        r1 = "Note N WHERE N creation_date D, N a_faire_par P, P nom 'jphc', D day > today-10;"
        r2 = "Note K WHERE K creation_date D, K a_faire_par Y, D day > today-10, Y nom 'jphc';"
        self._compareEquivalent(r1, r2)

    def test_same_request_in_or(self):
        r1 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'jphc' or P  nom 'ludal';"
        r2 = "Note K WHERE K creation_date D, K a_faire_par Y, D day > today-10, Y nom in ('jphc', 'ludal');"
        self._compareEquivalent(r1, r2)

    def test_same_request_reverse_or(self):
        r1 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'jphc' or P nom 'ludal';"
        r2 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'ludal' or P nom 'jphc';"
        self._compareEquivalent(r1, r2)

    def test_same_request_reverse_or2(self):
        r1 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P prenom 'jphc' or P nom 'ludal';"
        r2 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'ludal' or P prenom 'jphc';"
        self._compareEquivalent(r1, r2)

    def test_same_request_duplicate_expr(self):
        r1 = "Note N WHERE N creation_date D, N creation_date D;"
        r2 = "Note N WHERE N creation_date D;"
        self._compareEquivalent(r1, r2)

    def test_same_request_not_in_or(self):
        r1 = "Note K WHERE K creation_date D, K a_faire_par Y, D day > today-10, not Y nom in ('jphc', 'ludal');"
        r2 = "Note K WHERE K creation_date D, K a_faire_par Y, D day > today-10, not Y nom 'jphc' and not Y nom 'ludal';"
        self._compareEquivalent(r1, r2)

    # non equivalent queries ##################################################

    def test_diff_request(self):
        r1 = "Any N,  N2 where N is Note, N2 is Note, N a_faire_par P1, P1 nom 'jphc', N2 a_faire_par P2, P2 nom 'ocy' ;"
        r2 = "Any X where X is Note ;"
        self._compareNotEquivalent(r1,r2)

    def test_diff_request_and_or(self):
        r1 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'jphc' or P nom 'ludal';"
        r2 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'jphc', P nom 'ludal';"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_and_or2(self):
        r1 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'jphc' or P prenom 'ludal';"
        r2 = "Note N WHERE N creation_date D, D day > today-10, N a_faire_par P, P nom 'jphc', P prenom 'ludal';"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_non_selected_var(self):
        r1 = "Any X, D where X is Note, X creation_date D ;"
        r2 = "Any X where X is Note, X creation_date D ;"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_aggregat(self):
        r1 = "Any X, D where X is Note, X creation_date D ;"
        r2 = "Any X, MAX(D) where X is Note, X creation_date D ;"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_group(self):
        r1 = "Any X where X is Note GROUPBY X ;"
        r2 = "Any X where X is Note;"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_sort(self):
        r1 = "Any X where X is Note ORDERBY X ;"
        r2 = "Any X where X is Note;"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_not(self):
        r1 = "Any X where not X is Note ;"
        r2 = "Any X where X is Note;"
        self._compareNotEquivalent(r1, r2)

    def test_diff_request_not_in_or(self):
        r1 = "Note K WHERE K creation_date D, K a_faire_par Y, D day > today-10, not Y nom in ('jphc', 'ludal');"
        r2 = "Note K WHERE K creation_date D, K a_faire_par Y, D day > today-10, not Y nom 'jphc' or not Y nom 'ludal';"
        self._compareNotEquivalent(r1, r2)

if __name__ == '__main__':
    unittest.main()
