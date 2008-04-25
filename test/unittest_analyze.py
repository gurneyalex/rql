from logilab.common.testlib import TestCase, unittest_main

from rql import RQLHelper, TypeResolverException
from rql.analyze import UnifyingETypeResolver, ETypeResolver

FINAL_ETYPES = ('String', 'Boolean', 'Int', 'Float', 'Date', 'Datetime')

class ERSchema:

    def __cmp__(self, other):
        other = getattr(other, 'type', other)
        return cmp(self.type, other)
            
    def __hash__(self):
        return hash(self.type)
    
    def __str__(self):
        return self.type
    

class RelationSchema(ERSchema):
    def __init__(self, assoc_types, symetric=False):
        self.assoc_types = assoc_types
        self.subj_types = [e_type[0] for e_type in assoc_types]
        d = {}
        for e_type, dest_types in assoc_types:
            for e_type in dest_types:
                d[e_type] = 1
        self.obj_types = d.keys()
        self.symetric = symetric
        self.inlined = False
        
    def associations(self):
        return self.assoc_types
    
    def subjects(self, etype=None):
        return self.subj_types
    
    def objects(self, etype=None):
        return self.obj_types

    def is_final(self):
        return self.obj_types[0] in FINAL_ETYPES

class EntitySchema(ERSchema):
    def __init__(self, type):
        self.type = type

    def is_final(self):
        return self.type in FINAL_ETYPES
    
class DummySchema:
    _types = {}
    for type in ['String', 'Boolean', 'Int', 'Float', 'Date',
                 'Eetype', 'Person', 'Company', 'Address']:
        _types[type] = EntitySchema(type)
        
    _relations = {
        'eid' : RelationSchema( ( ('Person', ('Int',) ),
                                  ('Company', ('Int',) ),
                                  ('Address', ('Int',) ),
                                  ('Eetype', ('Int',) ),
                                  )
                                ),
        'creation_date' : RelationSchema( ( ('Person', ('Datetime',) ),
                                            ('Company', ('Datetime',) ),
                                            ('Address', ('Datetime',) ),
                                            ('Eetype', ('Datetime',) ),
                                            )
                                ),
        'name' : RelationSchema( ( ('Person', ('String',) ),
                                  ('Company', ('String',) ),
                                  )
                                ),
        'firstname' : RelationSchema( ( ('Person', ('String',) ),
                                       )
                                ),
        'work_for' : RelationSchema( ( ('Person', ('Company',) ),
                                      )
                                    ),
        'is' : RelationSchema( ( ('Person', ('Eetype',) ),
                                 ('Company', ('Eetype',) ),
                                 ('Address', ('Eetype',) ),
                                 )
                               ),
        'connait' : RelationSchema( (('Person', ('Person',) ),
                                     ),
                                    symetric=True),
        'located' : RelationSchema( ( ('Person', ('Address',) ),
                                     ('Company', ('Address',) ),
                                     )
                                   ),
        'owned_by' : RelationSchema( ( ('Person', ('Person',) ),
                                       ('Company', ('Person',) ),
                                       ('Eetype', ('Person',) ),
                                       )
                                     ),
        'identity' : RelationSchema( ( ('Person', ('Person',) ),
                                       ('Company', ('Company',) ),
                                       ('Address', ('Address',) ),
                                       ('Eetype', ('Eetype',) ),
                                  )
                                ),
        }
    def entities(self):
        return self._types.values()
        
    def relations(self):
        return self._relations.keys()

    def has_entity(self, e_type):
        return self._types.has_key(e_type)
    
    def has_relation(self, r_type):
        return self._relations.has_key(r_type)
    
    def __contains__(self, ertype):
        return self.has_entity(ertype) or self.has_relation(ertype)
    
    def relation_schema(self, r_type):
        return self._relations[r_type]
    rschema = relation_schema
        
        
UNRESOLVABLE_QUERIES = (
    'Person X WHERE Y work_for X',
    'Person X WHERE X work_for Y, Y is Address',
    'Insert Company X : X name "toto", X work_for Y WHERE Y name "logilab"',
    )

DEBUG = 0
ALL_SOLS = [{'X': 'Address'}, {'X': 'Company'},
            {'X': 'Eetype'}, {'X': 'Person'}]


class AnalyzerClassTest(TestCase):
    """check wrong queries arre correctly detected
    """
    eids = {10: 'Eetype'}
    def _type_from_eid(self, eid):
        return self.eids.get(eid, 'Person')
    
    def setUp(self):
        self.helper = RQLHelper(DummySchema(), {'eid': self._type_from_eid})

    def test_raise(self):
        for rql in UNRESOLVABLE_QUERIES:
            if DEBUG:
                print rql
            node = self.helper.parse(rql)
            self.assertRaises(TypeResolverException,
                              self.helper.compute_solutions, node, debug=DEBUG)
        
    def test_base_1(self):
        node = self.helper.parse('Any X')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Address'},
                                {'X': 'Company'},
                                {'X': 'Eetype'},
                                {'X': 'Person'}])
        
    def test_base_2(self):
        node = self.helper.parse('Person X')
        # check constant type of the is relation inserted
        self.assertEqual(node.children[0].where.children[1].children[0].type,
                         'etype')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = node.children[0].solutions
        self.assertEqual(sols, [{'X': 'Person'}])
        
    def test_base_3(self):
        node = self.helper.parse('Any X WHERE X eid 1')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = node.children[0].solutions
        self.assertEqual(sols, [{'X': 'Person'}])
        node = self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = node.children[0].solutions
        self.assertEqual(sols, [{}])
    
    def test_base_guess_1(self):
        node = self.helper.parse('Person X WHERE X work_for Y')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'}])
    
    def test_base_guess_2(self):
        node = self.helper.parse('Any X WHERE X name "Logilab"')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Company'}, {'X': 'Person'}])
    
    def test_is_query(self):
        node = self.helper.parse('Any T WHERE X name "logilab", X is T')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Company', 'T': 'Eetype'},
                                {'X': 'Person', 'T': 'Eetype'}])

    def test_is_query_const(self):
        node = self.helper.parse('Any X WHERE X is T, T eid 10')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Address', 'T': 'Eetype'},
                                {'X': 'Company', 'T': 'Eetype'},
                                {'X': 'Person', 'T': 'Eetype'}])

    def test_not(self):
        node = self.helper.parse('Any X WHERE not X is Person')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        expected = ALL_SOLS[:]
        expected.remove({'X': 'Person'})
        self.assertEqual(sols, expected)

    def test_uid_func_mapping(self):
        h = self.helper
        def type_from_uid(name):
            self.assertEquals(name, "Logilab")
            return 'Company'
        uid_func_mapping = {'name': type_from_uid}
        # constant as rhs of the uid relation
        node = h.parse('Any X WHERE X name "Logilab"')
        h.compute_solutions(node, uid_func_mapping, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEquals(sols, [{'X': 'Company'}])
        # variable as rhs of the uid relation
        node = h.parse('Any N WHERE X name N')
        h.compute_solutions(node, uid_func_mapping, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEquals(sols, [{'X': 'Company', 'N': 'String'},
                                {'X': 'Person', 'N': 'String'}])
        # substitute as rhs of the uid relation
        node = h.parse('Any X WHERE X name %(company)s')
        h.compute_solutions(node, uid_func_mapping, {'company': 'Logilab'},
                        debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEquals(sols, [{'X': 'Company'}])


    def test_unusableuid_func_mapping(self):
        h = self.helper
        def type_from_uid(name):
            self.assertEquals(name, "Logilab")
            return 'Company'
        uid_func_mapping = {'name': type_from_uid}
        node = h.parse('Any X WHERE NOT X name %(company)s')
        h.compute_solutions(node, uid_func_mapping, {'company': 'Logilab'},
                        debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEquals(sols, ALL_SOLS)
        node = h.parse('Any X WHERE X name > %(company)s')
        h.compute_solutions(node, uid_func_mapping, {'company': 'Logilab'},
                        debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEquals(sols, ALL_SOLS)
        
        
    def test_base_guess_3(self):
        node = self.helper.parse('Any Z GROUPBY Z WHERE X name Z')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Company', 'Z': 'String'},
                                 {'X': 'Person', 'Z': 'String'}])

    def test_var_name(self):
        node = self.helper.parse('Any E1 GROUPBY E1 WHERE E2 is Person, E2 name E1')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E2': 'Person', 'E1': 'String'}])

    def test_relation_eid(self):
        node = self.helper.parse('Any E2 WHERE E2 work_for E1, E2 eid 2')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company', 'E2': 'Person'}])
        node = self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company'}])
        
        node = self.helper.parse('Any E1 WHERE E2 work_for E1, E2 eid 2')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company', 'E2': 'Person'}])
        node = self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company'}])
        
    def test_not_symetric_relation_eid(self):
        node = self.helper.parse('Any P WHERE X eid 0, NOT X connait P')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person', 'X': 'Person'}])
        node = self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person'}])
        
    def test_union(self):
        node = self.helper.parse('(Any P WHERE X eid 0, NOT X connait P) UNION (Any E1 WHERE E2 work_for E1, E2 eid 2)')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person', 'X': 'Person'}], [{'E1': 'Company', 'E2': 'Person'}])
        node = self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person'}], [{'E1': 'Company'}])
        
    def test_exists(self):
        node = self.helper.parse("Any X WHERE X firstname 'lulu',"
                                 "EXISTS (X owned_by U, U name 'lulufanclub' OR U name 'managers');")
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Person',
                                 'U': 'Person'}])

    def test_subqueries(self):
        node = self.helper.parse('Any L, Y, F WHERE Y located L '
                                 'WITH Y,F BEING ((Any X,F WHERE X is Person, X firstname F) '
                                 'UNION (Any X,F WHERE X is Company, X name F))')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(node.children[0].with_[0].query.children[0].solutions, [{'X': 'Person',
                                                                            'F': 'String'}])
        self.assertEqual(node.children[0].with_[0].query.children[1].solutions, [{'X': 'Company',
                                                                            'F': 'String'}])
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'Y': 'Company', 'L': 'Address',
                                 'F': 'String'},
                                {'Y': 'Person', 'L': 'Address',
                                 'F': 'String'}])

    def test_subqueries_aggregat(self):
        node = self.helper.parse('Any L, SUM(X)*100/Y GROUPBY L '
                                 'WHERE X is Person, X located L '
                                 'WITH Y BEING (Any SUM(X) WHERE X is Person)')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(node.children[0].with_[0].query.children[0].solutions, [{'X': 'Person'}])
        self.assertEqual(node.children[0].solutions, [{'X': 'Person', 'Y': 'Person',
                                                       'L': 'Address'}])

    def test_insert(self):
        node = self.helper.parse('INSERT Person X : X name "toto", X work_for Y WHERE Y name "logilab"')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.solutions)
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'}])

    def test_delete(self):
        node = self.helper.parse('DELETE Person X WHERE X name "toto", X work_for Y')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.solutions)
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'}])

    def test_set(self):
        node = self.helper.parse('SET X name "toto", X work_for Y WHERE Y name "logilab"')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.solutions)
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'}])

        
    def test_nongrer_not_u_ownedby_u(self):
        node = self.helper.parse('Any U WHERE NOT U owned_by U')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'U': 'Person'}])
        

if __name__ == '__main__':
    unittest_main()
