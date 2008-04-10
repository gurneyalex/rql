from logilab.common.testlib import TestCase, unittest_main

from rql import RQLHelper, TypeResolverException
from rql.analyze import UnifyingETypeResolver, ETypeResolver

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
        return self.obj_types[0] in ('String', 'Boolean', 'Int', 'Float', 'Date')

class EntitySchema(ERSchema):
    def __init__(self, type):
        self.type = type

    def is_final(self):
        return self.type in ('String', 'Boolean', 'Int', 'Float', 'Date')
    
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
ALL_SOLS = [[{'X': 'Address'}, {'X': 'Company'},
             {'X': 'Eetype'}, {'X': 'Person'}]]


def sort_sols(solss):
    for sols in solss:
        sols.sort()
    return solss

class AnalyzerClassTest(TestCase):
    """check wrong queries arre correctly detected
    """
    eids = {10: 'Eetype'}
    def _type_from_eid(self, eid):
        return self.eids.get(eid, 'Person')
    
    def setUp(self):
        self.helper = RQLHelper(DummySchema(), {'eid': self._type_from_eid})
        
    def test_base_1(self):
        node = self.helper.parse('Any X')
        solss = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        self.assertEqual(solss, [[{'X': 'Address'},
                                  {'X': 'Company'},
                                  {'X': 'Eetype'},
                                  {'X': 'Person'}]])
        
    def test_base_2(self):
        node = self.helper.parse('Person X')
        # check constant type of the is relation inserted
        self.assertEqual(node.children[0].get_restriction().children[1].children[0].type,
                         'etype')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'X': 'Person'}]])
        
    def test_base_3(self):
        node = self.helper.parse('Any X WHERE X eid 1')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'X': 'Person'}]])
        node = self.helper.simplify(node)
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{}]])
    
    def test_base_guess_1(self):
        node = self.helper.parse('Person X WHERE X work_for Y')
        sols = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        self.assertEqual(sols, [[{'X': 'Person', 'Y': 'Company'}]])
    
    def test_base_guess_2(self):
        node = self.helper.parse('Any X WHERE X name "Logilab"')
        sols = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        self.assertEqual(sols, [[{'X': 'Company'}, {'X': 'Person'}]])
    
    def test_is_query(self):
        node = self.helper.parse('Any T WHERE X name "logilab", X is T')
        sols = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        self.assertEqual(sols, [[{'X': 'Company', 'T': 'Eetype'},
                                {'X': 'Person', 'T': 'Eetype'}]])

    def test_is_query_const(self):
        node = self.helper.parse('Any X WHERE X is T, T eid 10')
        sols = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        self.assertEqual(sols, [[{'X': 'Address', 'T': 'Eetype'},
                                {'X': 'Company', 'T': 'Eetype'},
                                {'X': 'Person', 'T': 'Eetype'}]])

    def test_not(self):
        node = self.helper.parse('Any X WHERE not X is Person')
        sols = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        expected = ALL_SOLS[0][:]
        expected.remove({'X': 'Person'})
        self.assertEqual(sols, [expected])

    def test_uid_func_mapping(self):
        h = self.helper
        def type_from_uid(name):
            self.assertEquals(name, "Logilab")
            return 'Company'
        uid_func_mapping = {'name': type_from_uid}
        # constant as rhs of the uid relation
        node = h.parse('Any X WHERE X name "Logilab"')
        sols = h.get_solutions(node, uid_func_mapping, debug=DEBUG)
        self.assertEquals(sols, [[{'X': 'Company'}]])
        # variable as rhs of the uid relation
        node = h.parse('Any N WHERE X name N')
        sols = sort_sols(h.get_solutions(node, uid_func_mapping, debug=DEBUG))
        self.assertEquals(sols, [[{'X': 'Company', 'N': 'String'},
                                {'X': 'Person', 'N': 'String'}]])
        # substitute as rhs of the uid relation
        node = h.parse('Any X WHERE X name %(company)s')
        sols = h.get_solutions(node, uid_func_mapping, {'company': 'Logilab'},
                               debug=DEBUG)
        self.assertEquals(sols, [[{'X': 'Company'}]])


    def test_unusableuid_func_mapping(self):
        h = self.helper
        def type_from_uid(name):
            self.assertEquals(name, "Logilab")
            return 'Company'
        uid_func_mapping = {'name': type_from_uid}
        node = h.parse('Any X WHERE NOT X name %(company)s')
        sols = sort_sols(h.get_solutions(node, uid_func_mapping, {'company': 'Logilab'},
                                         debug=DEBUG))
        self.assertEquals(sols, ALL_SOLS)
        node = h.parse('Any X WHERE X name > %(company)s')
        sols = sort_sols(h.get_solutions(node, uid_func_mapping, {'company': 'Logilab'},
                                         debug=DEBUG))
        self.assertEquals(sols, ALL_SOLS)
        
        
    def test_base_guess_3(self):
        node = self.helper.parse('Any Z WHERE X name Z GROUPBY Z')
        sols = sort_sols(self.helper.get_solutions(node, debug=DEBUG))
        self.assertEqual(sols, [[{'X': 'Company', 'Z': 'String'},
                                 {'X': 'Person', 'Z': 'String'}]])

    def test_var_name(self):
        node = self.helper.parse('Any E1 WHERE E2 is Person, E2 name E1 GROUPBY E1')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'E2': 'Person', 'E1': 'String'}]])

    def test_insert_1(self):
        node = self.helper.parse('INSERT Person X : X name "toto", X work_for Y WHERE Y name "logilab"')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'X': 'Person', 'Y': 'Company'}]])

    def test_relation_eid(self):
        node = self.helper.parse('Any E2 WHERE E2 work_for E1, E2 eid 2')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'E1': 'Company', 'E2': 'Person'}]])
        node = self.helper.simplify(node)
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'E1': 'Company'}]])
        
        node = self.helper.parse('Any E1 WHERE E2 work_for E1, E2 eid 2')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'E1': 'Company', 'E2': 'Person'}]])
        node = self.helper.simplify(node)
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'E1': 'Company'}]])
        
    def test_not_symetric_relation_eid(self):
        node = self.helper.parse('Any P WHERE X eid 0, NOT X connait P')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'P': 'Person', 'X': 'Person'}]])
        node = self.helper.simplify(node)
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'P': 'Person'}]])
        
    def test_union(self):
        node = self.helper.parse('Any P WHERE X eid 0, NOT X connait P UNION Any E1 WHERE E2 work_for E1, E2 eid 2')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'P': 'Person', 'X': 'Person'}], [{'E1': 'Company', 'E2': 'Person'}]])
        node = self.helper.simplify(node)
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'P': 'Person'}], [{'E1': 'Company'}]])
    
    def test_raise(self):
        for rql in UNRESOLVABLE_QUERIES:
            if DEBUG:
                print rql
            node = self.helper.parse(rql)
            self.assertRaises(TypeResolverException,
                              self.helper.get_solutions, node, debug=DEBUG)

        
    def test_nongrer_not_u_ownedby_u(self):
        node = self.helper.parse('Any U WHERE NOT U owned_by U')
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'U': 'Person'}]])
        
    def test_exists(self):
        node = self.helper.parse("Any X WHERE X firstname 'lulu',"
                                 "EXISTS (X owned_by U, U name 'lulufanclub' OR U name 'managers');")
        sols = self.helper.get_solutions(node, debug=DEBUG)
        self.assertEqual(sols, [[{'X': 'Person',
                                 'U': 'Person'}]])


##     def test_raise(self):
##         for rql in UNRESOLVABLE_QUERIES:
##             print rql
##             node = self.helper.parse(rql)
##             try:
##                 sols = self.helper.get_solutions( node )
##                 print sols
##             except TypeResolverException:
##                 print "No sols"

if __name__ == '__main__':
    unittest_main()
