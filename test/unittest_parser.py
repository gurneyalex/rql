# -*- coding: ISO-8859-1 -*-
""" Copyright (c) 2004-2006 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from logilab.common.testlib import TestCase, unittest_main

from yapps.runtime import print_error, SyntaxError
from rql.parser import Hercule, HerculeScanner
from rql import BadRQLQuery, RQLSyntaxError, nodes, stmts, parse
from rql import parse

BAD_SYNTAX_QUERIES = (
    'ANY X WHERE X name Nulll;',
    'ANY X WHERE (X name NULL or X name "chouette";',
    'INSERT Person X : X name "bidule" or X name "chouette";',
    'Any X WHERE "YO" related "UPI";',
    # FIXME: why should those raise a syntax error ?
#    'Any X groupby X;',
#    'Any X orderby X;',
    # FIXME: incorrect because X/Y are not bound, not a syntax error
#    'SET X travaille Y;',
    "Personne P WHERE OFFSET 200;",
    )

BAD_QUERIES = (
    'Person Marcou;',
    'INSERT Any X : X name "bidule";',
    'DELETE Any X;',
    'Person Marcou',
    'INSERT Person X : Y name "bidule" WHERE X work_for Y;',
    'Any X LIMIT -1;',
    'Any X OFFSET -1;',
    )

# FIXME: this shoud be generated from the spec file
SPEC_QUERIES = (
    'Any X WHERE X eid 53;',
    'Any X WHERE X eid -53;',
    "Document X WHERE X occurence_of F, F class C, C name 'Bande dessinée', X owned_by U, U login 'syt', X available true;",
    "Personne P WHERE P travaille_pour S, S nom 'Eurocopter', P interesse_par T, T nom 'formation';",
    "Note N WHERE N ecrit_le D, D day > (today -10), N ecrit_par P, P nom 'jphc' or P nom 'ocy';",
    "Personne P WHERE (P interesse_par T, T nom 'formation') or (P ville 'Paris');",
    "Any X where X is Person, X firstname 'Anne', X surname S ORDERBY S DESC;",
    "Personne P WHERE P nom N LIMIT 100;",
    "Personne P WHERE P nom N LIMIT 100 OFFSET 200;",
    "INSERT Personne X: X nom 'bidule';",
    "INSERT Personne X, Personne Y: X nom 'bidule', Y nom 'chouette', X ami Y;",
    "INSERT Person X: X nom 'bidule', X ami Y WHERE Y nom 'chouette';",
    "SET X nom 'toto', X prenom 'original' WHERE X is Person, X nom 'bidule';",
    "SET X know Y WHERE X ami Y;",
    "DELETE Person X WHERE X nom 'toto';",
    "DELETE X ami Y WHERE X is Person, X nom 'toto';",

    # some additional cases
    'INSERT Person X : X name "bidule", Y workfor X WHERE Y name "logilab";',
    'DISTINCT Any X,A,B,C,D WHERE P eid 41, X concerns P, P is Project, X is Story,X title A,X state B,X priority C,X cost D ORDERBY A ASC;',
    'Any X WHERE X has_text "2.12.0";',
    'Any X,A,B,C,D WHERE X concerns 41,X title A,X state B,X priority C,X cost D ORDERBY A ASC;',

    "Any X, COUNT(B) where B concerns X GROUPBY X ORDERBY 1;"

    'Any X, MAX(COUNT(B)) WHERE B concerns X GROUPBY X;', # syntaxically correct

    'Any X WHERE X eid > 12;',
    'DELETE Any X WHERE X eid > 12;',
    
    # optional relation support (left|right outer join)
    'Any X,Y,A WHERE X? concerns Y, Y title A;',
    'Any X,Y,A WHERE X concerns Y?, Y title A;',
    'Any X,Y,A WHERE X? concerns Y?, Y title A;',
    
    )

E_TYPES = {"Person" : 'Person',
           "Project" : 'Project',
           "Story" : 'Story'}

class ParserHercule(TestCase):
    _syntaxerr = SyntaxError

    def parse(self, string, print_errors=False):
        try:
            parser = Hercule(HerculeScanner(string))
            return parser.goal(E_TYPES)
        except SyntaxError, ex:
            if print_errors:
                # try to get error message from yapps
                print_error(ex, parser._scanner)
                print
            raise

    def test_precedence_1(self):
        tree = self.parse("Any X WHERE X firstname 'lulu' AND X name 'toto' OR X name 'tutu';")
        base = tree.children[0]
        self.assertEqual(isinstance(base, nodes.OR), 1)
        self.assertEqual(isinstance(base.children[0], nodes.AND), 1)
        self.assertEqual(isinstance(base.children[1], nodes.Relation), 1)

    def test_precedence_2(self):
        tree = self.parse("Any X WHERE X firstname 'lulu', X name 'toto' OR X name 'tutu';")
        base = tree.children[0]
        self.assertEqual(isinstance(base, nodes.AND), 1)
        self.assertEqual(isinstance(base.children[0], nodes.Relation), 1)
        self.assertEqual(isinstance(base.children[1], nodes.OR), 1)
        self.assertEqual(str(tree), "Any X WHERE X firstname 'lulu', X name 'toto' OR X name 'tutu'")

    def test_precedence_3(self):
        tree = self.parse("Any X WHERE X firstname 'lulu' AND (X name 'toto' or X name 'tutu');")
        base = tree.children[0]
        self.assertEqual(isinstance(base, nodes.AND), 1)
        self.assertEqual(isinstance(base.children[0], nodes.Relation), 1)
        self.assertEqual(isinstance(base.children[1], nodes.OR), 1)
        self.assertEqual(str(tree), "Any X WHERE X firstname 'lulu', X name 'toto' OR X name 'tutu'")

    def test_precedence_4(self):
        tree = self.parse("Any X WHERE X firstname 'lulu' OR X name 'toto' AND X name 'tutu';")
        base = tree.children[0]
        self.assertEqual(isinstance(base, nodes.OR), 1)
        self.assertEqual(isinstance(base.children[0], nodes.Relation), 1)
        self.assertEqual(isinstance(base.children[1], nodes.AND), 1)

    def test_string_1(self):
        tree = self.parse(r"Any X WHERE X firstname 'lu\"lu';")
        const = tree.children[0].children[1].children[0]
        self.assertEqual(const.value, r'lu\"lu')

    def test_string_2(self):
        tree = self.parse(r"Any X WHERE X firstname 'lu\'lu';")
        const = tree.children[0].children[1].children[0]
        self.assertEqual(const.value, 'lu\'lu')

    def test_string_3(self):
        tree = self.parse(r'Any X WHERE X firstname "lu\'lu";')
        const = tree.children[0].children[1].children[0]
        self.assertEqual(const.value, r"lu\'lu")

    def test_string_4(self):
        tree = self.parse(r'Any X WHERE X firstname "lu\"lu";')
        const = tree.children[0].children[1].children[0]
        self.assertEqual(const.value, "lu\"lu")

    def test_math_1(self):
        tree = self.parse(r'Any X WHERE X date (TODAY + 1);')
        math = tree.children[0].children[1].children[0]
        self.assert_(isinstance(math, nodes.MathExpression))
        self.assertEqual(math.operator, '+')

    def test_math_2(self):
        tree = self.parse(r'Any X WHERE X date (TODAY + 1 * 2);')
        math = tree.children[0].children[1].children[0]
        self.assert_(isinstance(math, nodes.MathExpression))
        self.assertEqual(math.operator, '+')
        math2 = math.children[1]
        self.assert_(isinstance(math2, nodes.MathExpression))
        self.assertEqual(math2.operator, '*')

    def test_math_3(self):
        tree = self.parse(r'Any X WHERE X date (TODAY + 1) * 2;')
        math = tree.children[0].children[1].children[0]
        self.assert_(isinstance(math, nodes.MathExpression))
        self.assertEqual(math.operator, '*')
        math2 = math.children[0]
        self.assert_(isinstance(math2, nodes.MathExpression))
        self.assertEqual(math2.operator, '+')

    def test_substitute(self):
        tree = self.parse("Any X WHERE X firstname %(firstname)s;")
        cste = tree.children[0].children[1].children[0]
        self.assert_(isinstance(cste, nodes.Constant))
        self.assertEquals(cste.type, 'Substitute')
        self.assertEquals(cste.value, 'firstname')

    def test_optional_relation(self):
        tree = self.parse(r'Any X WHERE X related Y;')
        related = tree.children[0]
        self.assertEquals(related.optional, None)
        tree = self.parse(r'Any X WHERE X? related Y;')
        related = tree.children[0]
        self.assertEquals(related.optional, 'left')
        tree = self.parse(r'Any X WHERE X related Y?;')
        related = tree.children[0]
        self.assertEquals(related.optional, 'right')
        tree = self.parse(r'Any X WHERE X? related Y?;')
        related = tree.children[0]
        self.assertEquals(related.optional, 'both')

    def test_spec(self):
        """test all RQL string found in the specification and test they are well parsed"""
        for rql in SPEC_QUERIES:
#            print "Orig:", rql
#            print "Resu:", rqltree
            yield self.assert_, self.parse(rql)

    def test_raise_badsyntax_error(self):
        for rql in BAD_SYNTAX_QUERIES:
            yield self.assertRaises, self._syntaxerr, self.parse, rql

    def test_raise_badrqlquery(self):
        BAD_QUERIES = ('Person Marcou;',)
        for rql in BAD_QUERIES:
            yield self.assertRaises, BadRQLQuery, self.parse, rql


class ParserRQLHelper(ParserHercule):
    _syntaxerr = RQLSyntaxError

    def parse(self, string, print_errors=False):
        try:
            return parse(string, E_TYPES, print_errors)
        except:
            raise

     
if __name__ == '__main__':
    unittest_main()
