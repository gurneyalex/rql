""" Copyright (c) 2000-2003 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: unittest_utils.py,v 1.5 2006-02-20 02:06:09 ludal Exp $"

from logilab.common.testlib import TestCase, unittest_main

from rql import utils, nodes, parse

class Visitor(utils.RQLVisitorHandler):
    def visit(self, node):
        node.accept(self)
        for c in node.children:
            self.visit(c)

class GetNodesFunctionTest(TestCase):
    def test_known_values_1(self):
        tree = parse('Any X where X name "turlututu"', {})
        constants = utils.get_nodes(tree, nodes.Constant)
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')
    
    def test_known_values_2(self):
        tree = parse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"', {})
        varrefs = utils.get_nodes(tree, nodes.VariableRef)
        self.assertEquals(len(varrefs), 4)
        for varref in varrefs:
            self.assertEquals(isinstance(varref, nodes.VariableRef), 1)
        names = [ x.name for x in varrefs ]
        names.sort()
        self.assertEquals(names[0], 'X')
        self.assertEquals(names[1], 'X')
        self.assertEquals(names[2], 'Y')
        self.assertEquals(names[3], 'Y')

    def test_iknown_values_1(self):
        tree = parse('Any X where X name "turlututu"', {})
        constants = list(utils.iget_nodes(tree, nodes.Constant))
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')
    
    def test_iknown_values_2(self):
        tree = parse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"', {})
        varrefs = list(utils.iget_nodes(tree, nodes.VariableRef))
        self.assertEquals(len(varrefs), 4)
        for varref in varrefs:
            self.assertEquals(isinstance(varref, nodes.VariableRef), 1)
        names = [ x.name for x in varrefs ]
        names.sort()
        self.assertEquals(names[0], 'X')
        self.assertEquals(names[1], 'X')
        self.assertEquals(names[2], 'Y')
        self.assertEquals(names[3], 'Y')

    def test_iknown_values_3(self):
        tree = parse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"', {})
        rels = list(utils.iget_nodes_filtered(tree, nodes.Relation, lambda n:n.r_type == 'name'))
        self.assertEquals(len(rels), 2)
        self.assertEquals(isinstance(rels[0], nodes.Relation), 1)
        self.assertEquals(isinstance(rels[1], nodes.Relation), 1)
        self.assertEquals(rels[0].r_type, 'name')
        self.assertEquals(rels[1].r_type, 'name')
        names = [ x.children[0].name for x in rels ]
        names.sort()        
        self.assertEquals(names, [ 'X', 'Y' ])
        
    


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
        
if __name__ == '__main__':
    unittest_main()
