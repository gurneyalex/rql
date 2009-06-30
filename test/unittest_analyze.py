from logilab.common.testlib import TestCase, unittest_main

from rql import RQLHelper, TypeResolverException

FINAL_ETYPES = ('String', 'Boolean', 'Int', 'Float', 'Date', 'Datetime')

class ERSchema(object):

    def __cmp__(self, other):
        other = getattr(other, 'type', other)
        return cmp(self.type, other)

    def __hash__(self):
        return hash(self.type)

    def __str__(self):
        return self.type


class RelationSchema(ERSchema):
    def __init__(self, assoc_types, symetric=False, card=None):
        self.assoc_types = assoc_types
        self.subj_types = [e_type[0] for e_type in assoc_types]
        self.final = False
        d = {}
        for e_type, dest_types in assoc_types:
            for e_type in dest_types:
                d[e_type] = 1
                if e_type in ('Int', 'Datetime', 'String'):
                    self.final = True
        self.obj_types = d.keys()
        self.symetric = symetric
        self.inlined = False
        if card is None:
            if self.final:
                card = '?*'
            else:
                card = '**'
        self.card = card

    def associations(self):
        return self.assoc_types

    def subjects(self, etype=None):
        return self.subj_types

    def objects(self, etype=None):
        return self.obj_types

    def is_final(self):
        return self.obj_types[0] in FINAL_ETYPES

    def iter_rdefs(self):
        for subjtype, dest_types in self.assoc_types:
            for objtype in dest_types:
                yield subjtype, objtype

    def rproperty(self, subj, obj, rprop):
        assert rprop == 'cardinality'
        return self.card

class EntitySchema(ERSchema):
    def __init__(self, type, specialized_by=None):
        self.type = type
        self._specialized_by = specialized_by or ()

    def is_final(self):
        return self.type in FINAL_ETYPES

    def specialized_by(self):
        return self._specialized_by

class DummySchema(object):

    def __init__(self):
        self._types = {}
        for etype in ['String', 'Boolean', 'Int', 'Float', 'Date', 'Datetime',
                      'Eetype', 'Person', 'Company', 'Address', 'Student']:
            self._types[etype] = EntitySchema(etype)
        self._types['Person']._specialized_by = [self._types['Student']]
        self._relations  = {
            'eid' : RelationSchema( ( ('Person', ('Int',) ),
                                      ('Student', ('Int',) ),
                                      ('Company', ('Int',) ),
                                      ('Address', ('Int',) ),
                                      ('Eetype', ('Int',) ),
                                      )
                                    ),
            'creation_date' : RelationSchema( ( ('Person', ('Datetime',) ),
                                                ('Student', ('Datetime',) ),
                                                ('Company', ('Datetime',) ),
                                                ('Address', ('Datetime',) ),
                                                ('Eetype', ('Datetime',) ),
                                                )
                                    ),
            'name' : RelationSchema( ( ('Person', ('String',) ),
                                       ('Student', ('String',) ),
                                       ('Company', ('String',) ),
                                      )
                                    ),
            'firstname' : RelationSchema( ( ('Person', ('String',) ),
                                            ('Student', ('String',) ),
                                           )
                                    ),
            'work_for' : RelationSchema( ( ('Person', ('Company',) ),
                                           ('Student', ('Company',) ),
                                           ),
                                         card='?*'),
            'is' : RelationSchema( ( ('Person', ('Eetype',) ),
                                     ('Student', ('Eetype',) ),
                                     ('Company', ('Eetype',) ),
                                     ('Address', ('Eetype',) ),
                                     )
                                   ),
            'is_instance_of' : RelationSchema( ( ('Person', ('Eetype',) ),
                                              ('Student', ('Eetype',) ),
                                              ('Company', ('Eetype',) ),
                                              ('Address', ('Eetype',) ),
                                              )
                                            ),
            'connait' : RelationSchema( (('Person', ('Person',) ),
                                         ('Student', ('Person',) ),
                                         ('Student', ('Student',) ),
                                         ('Person', ('Student',) ),
                                         ),
                                        symetric=True),
            'located' : RelationSchema( ( ('Person', ('Address',) ),
                                          ('Student', ('Address',) ),
                                          ('Company', ('Address',) ),
                                         )
                                       ),
            'owned_by' : RelationSchema( ( ('Person', ('Person',) ),
                                           ('Student', ('Person',) ),
                                           ('Company', ('Person',) ),
                                           ('Eetype', ('Person',) ),
                                           )
                                         ),
            'identity' : RelationSchema( ( ('Person', ('Person',) ),
                                           ('Student', ('Student',) ),
                                           ('Company', ('Company',) ),
                                           ('Address', ('Address',) ),
                                           ('Eetype', ('Eetype',) ),
                                      )
                                    ),
            'number' : RelationSchema( ( ('Person', ('Int',) ),
                                         ('Student', ('Int',) ),
                                         ('Company', ('Float',) ),
                                      )
                                    ),
            }
        for rtype, rschema in self._relations.iteritems():
            rschema.type = rtype

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

    def rschema(self, r_type):
        return self._relations[r_type]
    def eschema(self, e_type):
        return self._types[e_type]

UNRESOLVABLE_QUERIES = (
    'Person X WHERE Y work_for X',
    'Person X WHERE X work_for Y, Y is Address',
    'Insert Company X : X name "toto", X work_for Y WHERE Y name "logilab"',
    )

DEBUG = 0
ALL_SOLS = [{'X': 'Address'}, {'X': 'Company'},
            {'X': 'Eetype'}, {'X': 'Person'}, {'X': 'Student'}]


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
                                {'X': 'Person'},
                                {'X': 'Student'}])

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
        self.helper.simplify(node)
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
        self.assertEqual(sols, [{'X': 'Company'}, {'X': 'Person'}, {'X': 'Student'}])

    def test_is_instance_of_1(self):
        node = self.helper.parse('Any X WHERE X is_instance_of Person')
        # check constant type of the is relation inserted
        self.assertEqual(node.children[0].where.children[1].children[0].type,
                         'etype')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = node.children[0].solutions
        self.assertEqual(sols, [{'X': 'Person'}, {'X': 'Student'}])

    def test_is_instance_of_2(self):
        node = self.helper.parse('Any X WHERE X is_instance_of Student')
        # check constant type of the is relation inserted
        self.assertEqual(node.children[0].where.children[1].children[0].type,
                         'etype')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = node.children[0].solutions
        self.assertEqual(sols, [{'X': 'Student'}])

    def test_is_query(self):
        node = self.helper.parse('Any T WHERE X name "logilab", X is T')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Company', 'T': 'Eetype'},
                                {'X': 'Person', 'T': 'Eetype'},
                                {'X': 'Student', 'T': 'Eetype'}])

    def test_is_query_const(self):
        node = self.helper.parse('Any X WHERE X is T, T eid 10')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Address', 'T': 'Eetype'},
                                {'X': 'Company', 'T': 'Eetype'},
                                {'X': 'Person', 'T': 'Eetype'},
                                {'X': 'Student', 'T': 'Eetype'}])

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
                                 {'X': 'Person', 'N': 'String'},
                                 {'X': 'Student', 'N': 'String'}])
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
                                {'X': 'Person', 'Z': 'String'},
                                {'X': 'Student', 'Z': 'String'}])

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
        self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company'}])

        node = self.helper.parse('Any E1 WHERE E2 work_for E1, E2 eid 2')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company', 'E2': 'Person'}])
        self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'E1': 'Company'}])

    def test_not_symetric_relation_eid(self):
        node = self.helper.parse('Any P WHERE X eid 0, NOT X connait P')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person', 'X': 'Person'},
                                {'P': 'Student', 'X': 'Person'}])
        self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person'}, {'P': 'Student'}])

    def test_union(self):
        node = self.helper.parse('(Any P WHERE X eid 0, X is Person, NOT X connait P) UNION (Any E1 WHERE E2 work_for E1, E2 eid 2)')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person', 'X': 'Person'}, {'P': 'Student', 'X': 'Person'}])
        sols = sorted(node.children[1].solutions)
        self.assertEqual(sols, [{'E1': 'Company', 'E2': 'Person'}])
        self.helper.simplify(node)
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'P': 'Person'}, {'P': 'Student'}],)
        sols = sorted(node.children[1].solutions)
        self.assertEqual(sols, [{'E1': 'Company'}])

    def test_exists(self):
        node = self.helper.parse("Any X WHERE X firstname 'lulu',"
                                 "EXISTS (X owned_by U, U name 'lulufanclub' OR U name 'managers');")
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'X': 'Person',
                                 'U': 'Person'},
                                {'X': 'Student',
                                 'U': 'Person'}])

    def test_subqueries_base(self):
        node = self.helper.parse('Any L, Y, F WHERE Y located L '
                                 'WITH Y,F BEING ((Any X,F WHERE X is Person, X firstname F) '
                                 'UNION (Any X,F WHERE X is Company, X name F))')
        self.helper.compute_solutions(node, debug=DEBUG)
        self.assertEqual(node.children[0].with_[0].query.children[0].solutions,
                         [{'X': 'Person', 'F': 'String'}])
        self.assertEqual(node.children[0].with_[0].query.children[1].solutions,
                         [{'X': 'Company', 'F': 'String'}])
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

    def test_subqueries_outer_filter_type(self):
        # this kind of query may be generated by erudi's facettes box
        node = self.helper.parse('Any L, Y, F WHERE Y located L, Y is Person '
                                 'WITH Y,F BEING ((Any X,F WHERE X is Person, X firstname F) '
                                 'UNION (Any X,F WHERE X is Company, X name F))')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'Y': 'Person', 'L': 'Address',
                                 'F': 'String'}])
        self.assertEqual(node.children[0].with_[0].query.children[0].solutions,
                         [{'X': 'Person', 'F': 'String'}])
        # auto-simplification
        self.assertEqual(len(node.children[0].with_[0].query.children), 1)
        self.assertEquals(node.as_string(), 'Any L,Y,F WHERE Y located L, Y is Person WITH Y,F BEING (Any X,F WHERE X is Person, X firstname F)')
        self.assertEqual(node.children[0].with_[0].query.children[0].solutions,
                         [{'X': 'Person', 'F': 'String'}])

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
        self.assertEqual(sols, [{'X': 'Person', 'Y': 'Company'},
                                {'X': 'Student', 'Y': 'Company'}])

    def test_set_mathexpr(self):
        node = self.helper.parse('SET S number N/4 WHERE P work_for S, P number N')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.solutions)
        self.assertEqual(sols, [{'P': 'Person', 'S': 'Company', 'N': 'Int'},
                                {'P': 'Student', 'S': 'Company', 'N': 'Int'}])


    def test_nongrer_not_u_ownedby_u(self):
        node = self.helper.parse('Any U WHERE NOT U owned_by U')
        self.helper.compute_solutions(node, debug=DEBUG)
        sols = sorted(node.children[0].solutions)
        self.assertEqual(sols, [{'U': 'Person'}])


if __name__ == '__main__':
    unittest_main()
