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
    
    'Any UPPER(Y) WHERE X name "toto"',

    'Any C where C located P, P eid %(x)s ORDERBY N', #15066

#    'Any COUNT(X),P WHERE X concerns P', #9726
    'Any X, MAX(COUNT(B)) WHERE B concerns X GROUPBY X;',

    'Any X WHERE X nom "toto" UNION Any X,F WHERE X firstname F;',

    'Any Y WHERE X eid 12, X concerns Y UNION Any Y WHERE X eid 13, X located Y ORDERBY X',
    
    )

OK_QUERIES = (
    'Any N,COUNT(X) WHERE X name N GROUPBY N'
    ' UNION '
    'Any N,COUNT(X) WHERE X firstname N GROUPBY N'
    ' ORDERBY 2',
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
        self.assertEquals(self.simplify(self.parse(rql)).as_string(),
                          expected)
        
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
            ('Any X WHERE X work_for Y, Y eid IN (12) ORDERBY Y',
             'Any X WHERE X work_for 12 ORDERBY 12'),
            ('Any X WHERE X eid 12',
             'Any 12'),
            ('Any X WHERE X is Person, X eid 12',
             'Any 12'),
            ('Any X,Y WHERE X eid 0, Y eid 1, X work_for Y', 'Any 0,1 WHERE 0 work_for 1'),
# no more supported, use outerjoin explicitly
#            ('Any X,Y WHERE X work_for Y OR NOT X work_for Y', 'Any X,Y WHERE X? work_for Y?'),
#            ('Any X,Y WHERE NOT X work_for Y OR X work_for Y', 'Any X,Y WHERE X? work_for Y?'),
            # test symetric OR rewrite
            ("DISTINCT Any P WHERE P connait S OR S connait P, S name 'chouette'",
             "DISTINCT Any P WHERE P connait S, S name 'chouette'"),
            # queries that should not be rewritten
            ('DELETE Person X WHERE X eid 12', 'DELETE Person X WHERE X eid 12'),
            ('Any X WHERE X work_for Y, Y eid IN (12, 13)', 'Any X WHERE X work_for Y, Y eid IN(12, 13)'),
            ('Any X WHERE X work_for Y, NOT Y eid 12', 'Any X WHERE X work_for Y, NOT Y eid 12'),
            ('Any X WHERE NOT X eid 12', 'Any X WHERE NOT X eid 12'),
            ('Any N WHERE X eid 12, X name N', 'Any N WHERE X eid 12, X name N'),

            ('Any X WHERE X eid > 12', 'Any X WHERE X eid > 12'),
            
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
            
            ('Any X WHERE X eid 12 UNION Any X WHERE X eid 13 ORDERBY X',
             'Any 12 UNION Any 13 ORDERBY 1'),
            ):
            yield self._test_rewrite, rql, expected

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
        self.simplify(tree, needcopy=False)
        copy = tree.copy()
        exists = copy.get_nodes(nodes.Exists)[0]
        self.failUnless(exists.children[0].parent is exists)
        self.failUnless(exists.parent)
        
    def test_copy_internals(self):
        stmt = self.parse('Any X,U WHERE C owned_by U, NOT X owned_by U, X eid 1, C eid 2')
        self.simplify(stmt, needcopy=False)
        self.assertEquals(stmt.defined_vars['U'].valuable_references(), 3)
        copy = stmts.Select(stmt.e_types)
        copy.append_selected(stmt.selected[0].copy(copy))
        copy.append_selected(stmt.selected[1].copy(copy))
        copy.append(stmt.get_restriction().copy(copy))
        self.annotate(copy)
        self.simplify(copy, needcopy=False)
        self.assertEquals(copy.as_string(), 'Any 1,U WHERE 2 owned_by U, NOT 1 owned_by U')
        self.assertEquals(copy.defined_vars['U'].valuable_references(), 3)


class AnnotateTest(TestCase):
    
    def setUp(self):
        helper = RQLHelper(DummySchema(), None, {'eid': 'uid'})
        self.parse = helper.parse
        self.simplify = helper.simplify

#     def test_simplified(self):
#         rqlst = self.parse('Any L WHERE 5 name L')
#         self.annotate(rqlst)
#         self.failUnless(rqlst.defined_vars['L'].stinfo['attrvar'])

    def test_is_rel_no_scope(self):
        """is relation used as type restriction should not affect variable's scope,
        and should not be included in stinfo['relations']"""
        rqlst = self.parse('Any X WHERE C is Company, EXISTS(X work_for C)')
        C = rqlst.defined_vars['C']
        self.failIf(C.scope is rqlst, C.scope)
        self.assertEquals(len(C.stinfo['relations']), 1)
        rqlst = self.parse('Any X, ET WHERE C is ET, EXISTS(X work_for C)')
        C = rqlst.defined_vars['C']
        self.failUnless(C.scope is rqlst, C.scope)
        self.assertEquals(len(C.stinfo['relations']), 2)
        
if __name__ == '__main__':
    unittest_main()
