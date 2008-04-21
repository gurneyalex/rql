
from logilab.common.testlib import TestCase, unittest_main

from rql import parse
from rql.editextensions import *

class RQLUndoTestCase(TestCase):
    
    def test_selected(self):
        rqlst = parse('Person X')
        orig = rqlst.as_string()
        rqlst.save_state()
        select = rqlst.children[0]
        var = select.make_variable()
        select.remove_selected(select.selection[0])
        select.add_selected(var)
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any %s WHERE X is Person' % var.name)
        # check references before recovering
        rqlst.check_references()
        rqlst.recover()
        # check equivalence after recovering
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        rqlst.check_references()
    
    def test_selected3(self):
        rqlst = parse('Any lower(N) WHERE X is Person, X name N')
        orig = rqlst.as_string()
        rqlst.save_state()
        select = rqlst.children[0]
        var = select.make_variable()
        select.remove_selected(select.selection[0])
        select.add_selected(var)
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any %s WHERE X is Person, X name N' % var.name)
        # check references before recovering
        rqlst.check_references()
        rqlst.recover()
        # check equivalence after recovering
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        rqlst.check_references()
        
    def test_undefine_1(self):
        rqlst = parse('Person X, Y WHERE X travaille_pour Y')
        orig = rqlst.as_string()
        rqlst.save_state()
        rqlst.children[0].undefine_variable(rqlst.children[0].defined_vars['Y'])
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any X WHERE X is Person')
        # check references before recovering
        rqlst.check_references()
        rqlst.recover()
        # check equivalence
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        rqlst.check_references()
        
    def test_undefine_2(self):
        rqlst = parse('Person X')
        orig = rqlst.as_string()
        rqlst.save_state()
        rqlst.children[0].undefine_variable(rqlst.children[0].defined_vars['X'])
        var = rqlst.children[0].make_variable()
        rqlst.children[0].add_selected(var)
        # check operations
        self.assertEquals(rqlst.as_string(), 'Any A')
        # check references before recovering
        rqlst.check_references()
        rqlst.recover()
        # check equivalence
        self.assertEquals(rqlst.as_string(), orig)
        # check references after recovering
        rqlst.check_references()
        
        
if __name__ == '__main__':
    unittest_main()
