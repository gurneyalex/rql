
from logilab.common.testlib import TestCase, unittest_main

from rql import parse
from rql.editextensions import *

class RQLBaseTestCase(TestCase):
    def test_get_nodes(self):
        node = Sort()
        node.append(VariableRef(Variable('A')))
        node.append(VariableRef(Variable('B')))
        self.assertEquals(len(get_variable_refs(node)), 2)
        
class RQLUndoTestCase(TestCase):
    
    def test_selected(self):
        rqlst = parse('Person X')
        orig = rqlst.as_string()
        rqlst.save_state()
        var = rqlst.make_variable()
        rqlst.remove_selected(rqlst.selected[0])
        rqlst.add_selected(var)
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any %s WHERE X is Person' % var.name)
        # check references before recovering
        check_relations(rqlst)
        rqlst.recover()
        # check equivalence after recovering
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        check_relations(rqlst)
        
    def test_undefine_1(self):
        rqlst = parse('Person X, Y WHERE X travaille_pour Y')
        orig = rqlst.as_string()
        rqlst.save_state()
        rqlst.undefine_variable(rqlst.defined_vars['Y'])
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any X WHERE X is Person')
        # check references before recovering
        check_relations(rqlst)
        rqlst.recover()
        # check equivalence
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        check_relations(rqlst)
        
    def test_undefine_2(self):
        rqlst = parse('Person X')
        orig = rqlst.as_string()
        rqlst.save_state()
        rqlst.undefine_variable(rqlst.defined_vars['X'])
        var = rqlst.make_variable()
        rqlst.add_selected(var)
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any TMP')
        # check references before recovering
        check_relations(rqlst)
        rqlst.recover()
        # check equivalence
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        check_relations(rqlst)
        
        
if __name__ == '__main__':
    unittest_main()
