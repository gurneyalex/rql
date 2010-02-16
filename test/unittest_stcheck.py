from logilab.common.testlib import TestCase, unittest_main
from unittest_analyze import DummySchema
from rql import RQLHelper, BadRQLQuery, stmts, nodes

BAD_QUERIES = (
    'Any X, Y GROUPBY X',

    # this is now a valid query
    #'DISTINCT Any X WHERE X work_for Y ORDERBY Y',

    'Any X WHERE X name Person',

    'Any X WHERE X name nofunction(Y)',

    'Any X WHERE X name nofunction(Y)',

    'Any Y WHERE X name "toto"',

    'Any X WHERE X noattr "toto"',

    'Any X WHERE X is NonExistant',

    'Any UPPER(Y) WHERE X name "toto"',

    'Any C ORDERBY N where C located P, P eid %(x)s', #15066

#    'Any COUNT(X),P WHERE X concerns P', #9726
    'Any X, MAX(COUNT(B)) GROUPBY X WHERE B concerns X;',

    '(Any X WHERE X nom "toto") UNION (Any X,F WHERE X firstname F);',

    'Any X, X/Z WHERE X is Person; WITH Y BEING (Any SUM(X) WHERE X is Person)',

    'Any X WHERE X name "Toto", P is Person',

    # BAD QUERY cant sort on y
    'DISTINCT Any X ORDERBY Y WHERE B work_for X, B name Y',

    "Any X WHERE X eid 0, X eid 1"

    )

OK_QUERIES = (
    '(Any N,COUNT(X) GROUPBY N WHERE X name N)'
    ' UNION '
    '(Any N,COUNT(X) GROUPBY N WHERE X firstname N)',

    'DISTINCT Any X, MAX(Y) GROUPBY X WHERE X is Person, Y is Company',

    # sorting allowed since order variable reachable from a selected
    # variable with only ?1 cardinality
    'DISTINCT Any B ORDERBY Y WHERE B work_for X, B name Y',
    'DISTINCT Any B ORDERBY Y WHERE B work_for X, X name Y',

#    'DISTINCT Any X ORDERBY SN WHERE X in_state S, S name SN',


    )

class CheckClassTest(TestCase):
    """check wrong queries are correctly detected"""

    def setUp(self):
        helper = RQLHelper(DummySchema(), None, {'eid': 'uid'})
        self.parse = helper.parse
        self.simplify = helper.simplify

    def _test(self, rql):
        try:
            self.assertRaises(BadRQLQuery, self.parse, rql)
        except:
            print rql
            raise

    def test_raise(self):
        for rql in BAD_QUERIES:
            yield self._test, rql

    def test_ok(self):
        for rql in OK_QUERIES:
            yield self.parse, rql

    def _test_rewrite(self, rql, expected):
        rqlst = self.parse(rql)
        self.simplify(rqlst)
        self.assertEquals(rqlst.as_string(), expected)

    def test_rewrite(self):
        for rql, expected in (
            ('Person X',
             'Any X WHERE X is Person'),
            ("Any X WHERE X eid IN (12), X name 'toto'",
             "Any X WHERE X eid 12, X name 'toto'"),
            ('Any X WHERE X work_for Y, Y eid 12',
             'Any X WHERE X work_for 12'),
            ('Any X WHERE Y work_for X, Y eid 12',
             'Any X WHERE 12 work_for X'),
            ('Any X WHERE X work_for Y, Y eid IN (12)',
             'Any X WHERE X work_for 12'),
            ('Any X ORDERBY Y WHERE X work_for Y, Y eid IN (12)',
             'Any X WHERE X work_for 12'),
            ('Any X WHERE X eid 12',
             'Any 12'),
            ('Any X WHERE X is Person, X eid 12',
             'Any 12'),
            ('Any X,Y WHERE X eid 0, Y eid 1, X work_for Y',
             'Any 0,1 WHERE 0 work_for 1'),
# no more supported, use outerjoin explicitly
#            ('Any X,Y WHERE X work_for Y OR NOT X work_for Y', 'Any X,Y WHERE X? work_for Y?'),
#            ('Any X,Y WHERE NOT X work_for Y OR X work_for Y', 'Any X,Y WHERE X? work_for Y?'),
            # test symmetric OR rewrite
            ("DISTINCT Any P WHERE P connait S OR S connait P, S name 'chouette'",
             "DISTINCT Any P WHERE P connait S, S name 'chouette'"),
            # queries that should not be rewritten
            ('DELETE Person X WHERE X eid 12',
             'DELETE Person X WHERE X eid 12'),
            ('Any X WHERE X work_for Y, Y eid IN (12, 13)',
             'Any X WHERE X work_for Y, Y eid IN(12, 13)'),
            ('Any X WHERE X work_for Y, NOT Y eid 12',
             'Any X WHERE X work_for Y, NOT Y eid 12'),
            ('Any X WHERE NOT X eid 12',
             'Any X WHERE NOT X eid 12'),
            ('Any N WHERE X eid 12, X name N',
             'Any N WHERE X eid 12, X name N'),

            ('Any X WHERE X eid > 12',
             'Any X WHERE X eid > 12'),

            ('Any X WHERE X eid 12, X connait P?, X work_for Y',
             'Any X WHERE X eid 12, X connait P?, X work_for Y'),
            ('Any X WHERE X eid 12, P? connait X',
             'Any X WHERE X eid 12, P? connait X'),

            ("Any X WHERE X firstname 'lulu',"
             "EXISTS (X owned_by U, U name 'lulufanclub' OR U name 'managers');",
             "Any X WHERE X firstname 'lulu', "
             "EXISTS(X owned_by U, (U name 'lulufanclub') OR (U name 'managers'))"),

            ('Any X WHERE X eid 12, EXISTS(X name "hop" OR X work_for Y?)',
             "Any 12 WHERE EXISTS((A name 'hop') OR (A work_for Y?), 12 identity A)"),

            ('(Any X WHERE X eid 12) UNION (Any X ORDERBY X WHERE X eid 13)',
             '(Any 12) UNION (Any 13)'),

            ('Any X WITH X BEING (Any X WHERE X eid 12)',
             'Any X WITH X BEING (Any 12)'),

            ('Any X GROUPBY X WHERE X eid 12, X connait Y HAVING COUNT(Y) > 10',
             'Any X GROUPBY X WHERE X eid 12, X connait Y HAVING COUNT(Y) > 10'),

            # A eid 12 can be removed since the type analyzer checked its existence
            ('Any X WHERE A eid 12, X connait Y',
             'Any X WHERE X connait Y'),
            ):
            yield self._test_rewrite, rql, expected

    def test_subquery_graphdict(self):
        # test two things:
        # * we get graph information from subquery
        # * we see that we can sort on VCS (eg we have a unique value path from VF to VCD)
        rqlst = self.parse(('DISTINCT Any VF ORDERBY VCD DESC WHERE '
                            'VC work_for S, S name "draft" '
                            'WITH VF, VC, VCD BEING (Any VF, MAX(VC), VCD GROUPBY VF, VCD '
                            '                        WHERE VC connait VF, VC creation_date VCD)'))
        self.assertEquals(rqlst.children[0].vargraph,
                          {'VCD': ['VC'], 'VF': ['VC'], 'S': ['VC'], 'VC': ['S', 'VF', 'VCD'],
                           ('VC', 'S'): 'work_for',
                           ('VC', 'VF'): 'connait',
                           ('VC', 'VCD'): 'creation_date'})
        self.assertEquals(rqlst.children[0].aggregated, set(('VC',)))


##     def test_rewriten_as_string(self):
##         rqlst = self.parse('Any X WHERE X eid 12')
##         self.assertEquals(rqlst.as_string(), 'Any X WHERE X eid 12')
##         rqlst = rqlst.copy()
##         self.annotate(rqlst)
##         self.assertEquals(rqlst.as_string(), 'Any X WHERE X eid 12')

class CopyTest(TestCase):

    def setUp(self):
        helper = RQLHelper(DummySchema(), None, {'eid': 'uid'})
        self.parse = helper.parse
        self.simplify = helper.simplify
        self.annotate = helper.annotate

    def test_copy_exists(self):
        tree = self.parse("Any X WHERE X firstname 'lulu',"
                          "EXISTS (X owned_by U, U work_for G, G name 'lulufanclub' OR G name 'managers');")
        self.simplify(tree)
        copy = tree.copy()
        exists = copy.get_nodes(nodes.Exists)[0]
        self.failUnless(exists.children[0].parent is exists)
        self.failUnless(exists.parent)

    def test_copy_internals(self):
        root = self.parse('Any X,U WHERE C owned_by U, NOT X owned_by U, X eid 1, C eid 2')
        self.simplify(root)
        stmt = root.children[0]
        self.assertEquals(stmt.defined_vars['U'].valuable_references(), 3)
        copy = stmts.Select()
        copy.append_selected(stmt.selection[0].copy(copy))
        copy.append_selected(stmt.selection[1].copy(copy))
        copy.set_where(stmt.where.copy(copy))
        newroot = stmts.Union()
        newroot.append(copy)
        self.annotate(newroot)
        self.simplify(newroot)
        self.assertEquals(newroot.as_string(), 'Any 1,U WHERE 2 owned_by U, NOT 1 owned_by U')
        self.assertEquals(copy.defined_vars['U'].valuable_references(), 3)


class AnnotateTest(TestCase):

    def setUp(self):
        helper = RQLHelper(DummySchema(), None, {'eid': 'uid'})
        self.parse = helper.parse

#     def test_simplified(self):
#         rqlst = self.parse('Any L WHERE 5 name L')
#         self.annotate(rqlst)
#         self.failUnless(rqlst.defined_vars['L'].stinfo['attrvar'])

    def test_is_rel_no_scope(self):
        """is relation used as type restriction should not affect variable's scope,
        and should not be included in stinfo['relations']"""
        rqlst = self.parse('Any X WHERE C is Company, EXISTS(X work_for C)').children[0]
        C = rqlst.defined_vars['C']
        self.failIf(C.scope is rqlst, C.scope)
        self.assertEquals(len(C.stinfo['relations']), 1)
        rqlst = self.parse('Any X, ET WHERE C is ET, EXISTS(X work_for C)').children[0]
        C = rqlst.defined_vars['C']
        self.failUnless(C.scope is rqlst, C.scope)
        self.assertEquals(len(C.stinfo['relations']), 2)

    def test_subquery_annotation(self):
        rqlst = self.parse('Any X WITH X BEING (Any X WHERE C is Company, EXISTS(X work_for C))').children[0]
        C = rqlst.with_[0].query.children[0].defined_vars['C']
        self.failIf(C.scope is rqlst, C.scope)
        self.assertEquals(len(C.stinfo['relations']), 1)
        rqlst = self.parse('Any X,ET WITH X,ET BEING (Any X, ET WHERE C is ET, EXISTS(X work_for C))').children[0]
        C = rqlst.with_[0].query.children[0].defined_vars['C']
        self.failUnless(C.scope is rqlst.with_[0].query.children[0], C.scope)
        self.assertEquals(len(C.stinfo['relations']), 2)

if __name__ == '__main__':
    unittest_main()
