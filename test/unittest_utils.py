
from logilab.common.testlib import TestCase, unittest_main

from rql import utils, nodes, parse

class Visitor(utils.RQLVisitorHandler):
    def visit(self, node):
        node.accept(self)
        for c in node.children:
            self.visit(c)


class RQLHandlerClassTest(TestCase):
    """tests that the default handler implements a method for each possible node
    """
    
    def setUp(self):
        self.visitor = Visitor()
        
    def test_methods_1(self):
        tree = parse('Any X where X name "turlututu", X born <= TODAY - 2 OR X born = NULL', {})
        self.visitor.visit(tree)
        
    def test_methods_2(self):
        tree = parse('Insert Person X', {})
        self.visitor.visit(tree)
        
    def test_methods_3(self):
        tree = parse('Set X nom "yo" WHERE X is Person', {'Person':nodes.Constant('Person', 'etype')})
        self.visitor.visit(tree)
        
    def test_methods_4(self):
        tree = parse('Delete Person X', {})
        self.visitor.visit(tree)


class RQLVarMakerTC(TestCase):

    def test_rqlvar_maker(self):
        varlist = list(utils.rqlvar_maker(27))
        self.assertEquals(varlist, list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ['AA'])
        varlist = list(utils.rqlvar_maker(27*26+1))
        self.assertEquals(varlist[-2], 'ZZ')
        self.assertEquals(varlist[-1], 'AAA')

    def test_rqlvar_maker_dontstop(self):
        varlist = utils.rqlvar_maker()
        self.assertEquals(varlist.next(), 'A')
        self.assertEquals(varlist.next(), 'B')
        for i in range(24):
            varlist.next()
        self.assertEquals(varlist.next(), 'AA')
        self.assertEquals(varlist.next(), 'AB')

        
if __name__ == '__main__':
    unittest_main()
