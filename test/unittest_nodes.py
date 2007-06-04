# -*- coding: iso-8859-1 -*-

from logilab.common.testlib import TestCase, unittest_main

from rql import nodes, stmts, parse

E_TYPES = {"Person" : 'Person'}

class NodesTest(TestCase):
        
    # selection tests #########################################################
    
    def test_select_base_1(self):
        tree = parse("Person X;", E_TYPES)
        # test the root node
        self.assertEqual(isinstance(tree, stmts.Select), 1)
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assert_(isinstance(tree.children[0], nodes.Relation))
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X is Person")
        # test limit offset
        self.assertEqual(tree.limit, None)
        self.assertEqual(tree.offset, 0)
        
    def test_select_base_2(self):
        tree = parse("Any X WHERE X is Person;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Select))
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assert_(isinstance(tree.children[0], nodes.Relation))
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X is Person")
        
    def test_select_base_3(self):
        tree = parse("DISTINCT Any X WHERE X is Person;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Select))
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assert_(isinstance(tree.children[0], nodes.Relation))
        # test specific attributes
        self.assertEqual(tree.distinct, 1)
        # test serializing
        self.assertEqual(tree.as_string(), "DISTINCT Any X WHERE X is Person")
        
    def test_select_null(self):
        tree = parse("Any X WHERE X name NULL;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name NULL")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, None)
        self.assertEqual(constant.value, 'NULL')
        
    def test_select_bool(self):
        tree = parse("Any X WHERE X name False;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name false")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, 'false')
        tree = parse("Any X WHERE X name TRUE;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name true")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, 'true')
        
    def test_select_date(self):
        tree = parse("Any X WHERE X born TODAY;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X born TODAY")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Date')
        self.assertEqual(constant.value, 'TODAY')
        
    def test_select_int(self):
        tree = parse("Any X WHERE X name 1;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name 1")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Int')
        self.assertEqual(constant.value, 1)
        
    def test_select_float(self):
        tree = parse("Any X WHERE X name 1.0;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name 1.0")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Float')
        self.assertEqual(constant.value, 1.0)
        
    def test_select_group(self):
        tree = parse("Any X WHERE X is Person, X name N GROUPBY N;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Select))
        # test children
        self.assertEqual(len(tree.children), 2)
        self.assert_(isinstance(tree.children[0], nodes.AND))
        self.assert_(isinstance(tree.children[1], nodes.Group))
        self.assert_(isinstance(tree.children[1][0], nodes.VariableRef))
        self.assertEqual(tree.children[1][0].name, 'N')
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X is Person, X name N GROUPBY N")

    def test_select_ord(self):
        tree = parse("Any X WHERE X is Person, X name N ORDERBY N;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Select))
        # test children
        self.assertEqual(len(tree.children), 2)
        self.assert_(isinstance(tree.children[0], nodes.AND))
        self.assert_(isinstance(tree.children[1], nodes.Sort))
        self.assert_(isinstance(tree.children[1][0], nodes.SortTerm))
        self.assertEqual(tree.children[1][0].var.name, 'N')
        self.assertEqual(tree.children[1][0].asc, 1)
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(),
                         "Any X WHERE X is Person, X name N ORDERBY N")

    def test_selected_index(self):
        tree = parse("Any X WHERE X is Person, X name N ORDERBY N DESC;", E_TYPES)
        self.assertEquals(tree.defined_vars['X'].selected_index(), 0)
        self.assertEquals(tree.defined_vars['N'].selected_index(), None)

    def test_select_ord_desc(self):
        tree = parse("Any X WHERE X is Person, X name N ORDERBY N DESC;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Select))
        # test children
        self.assertEqual(len(tree.children), 2)
        self.assert_(isinstance(tree.children[0], nodes.AND))
        self.assert_(isinstance(tree.children[1], nodes.Sort))
        self.assert_(isinstance(tree.children[1][0], nodes.SortTerm))
        self.assertEqual(tree.children[1][0].var.name, 'N')
        self.assertEqual(tree.children[1][0].asc, 0)
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(),
                         "Any X WHERE X is Person, X name N ORDERBY N DESC")

    def test_select_group_ord_asc(self):
        tree = parse("Any X WHERE X is Person, X name N GROUPBY N ORDERBY N ASC;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Select))
        # test children
        self.assertEqual(len(tree.children), 3)
        self.assert_(isinstance(tree.children[0], nodes.AND))
        self.assert_(isinstance(tree.children[1], nodes.Group))
        self.assert_(isinstance(tree.children[1][0], nodes.VariableRef))
        self.assertEqual(tree.children[1][0].name, 'N')
        self.assert_(isinstance(tree.children[2], nodes.Sort))
        self.assert_(isinstance(tree.children[2][0], nodes.SortTerm))
        self.assertEqual(tree.children[2][0].var.name, 'N')
        self.assertEqual(tree.children[2][0].asc, 1)
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(),
                         "Any X WHERE X is Person, X name N GROUPBY N ORDERBY N")
        # just check repr() doesn't raise an exception
        repr(tree)

    def test_select_limit_offset(self):
        tree = parse("Any X WHERE X name 1.0 LIMIT 10 OFFSET 10;", E_TYPES)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name 1.0 LIMIT 10 OFFSET 10")
        self.assertEqual(tree.limit, 10)
        self.assertEqual(tree.offset, 10)
        
    def test_copy(self):
        tree = parse("Any X, lower(Y) WHERE X is Person, X name N, X date >= today GROUPBY N ORDERBY N ASC;", E_TYPES)
        select = stmts.Select({})
        restriction = tree.get_restriction()
        self.check_equal_but_not_same(restriction, restriction.copy(select))
        groups = tree.get_groups()
        self.check_equal_but_not_same(groups, groups.copy(select))
        sorts = tree.get_sortterms()
        self.check_equal_but_not_same(sorts, sorts.copy(select))
        # just check repr() doesn't raise an exception
        repr(tree)
        
    def check_equal_but_not_same(self, tree1, tree2):
        #d1 = tree1.__dict__.copy()
        #del d1['parent']; del d1['children'] # parent and children are slots now
        #d2 = tree2.__dict__.copy()
        #del d2['parent']; del d2['children']
        self.assertNotEquals(id(tree1), id(tree2))
        self.assert_(tree1.is_equivalent(tree2))
        #self.assertEquals(len(tree1.children), len(tree2.children))
        #for i in range(len(tree1.children)):
        #    self.check_equal_but_not_same(tree1.children[i], tree2.children[i])
            
    # insertion tests #########################################################

    def test_insert_base_1(self):
        tree = parse("INSERT Person X;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Insert))
        # test children
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 0)
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assert_(isinstance(tree.main_variables[0][1], nodes.VariableRef))
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        # test serializing
        self.assertEqual(str(tree), "INSERT Person X")
        
    def test_insert_base_2(self):
        tree = parse("INSERT Person X: X name 'bidule';", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Insert))
        # test children
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 1)
        self.assert_(isinstance(tree.main_relations[0], nodes.Relation))
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assert_(isinstance(tree.main_variables[0][1], nodes.VariableRef))
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        # test serializing
        self.assertEqual(str(tree), "INSERT Person X : X name 'bidule'")

    def test_insert_multi(self):
        tree = parse("INSERT Person X, Person Y: X name 'bidule', Y name 'chouette', X friend Y;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Insert))
        # test children
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 3)
        for relation in tree.main_relations:
            self.assert_(isinstance(relation, nodes.Relation))
        self.assertEqual(len(tree.main_variables), 2)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assert_(isinstance(tree.main_variables[0][1], nodes.VariableRef))
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        self.assertEqual(tree.main_variables[1][0], 'Person')
        self.assert_(isinstance(tree.main_variables[0][1], nodes.VariableRef))
        self.assertEqual(tree.main_variables[1][1].name, 'Y')
        # test serializing
        self.assertEqual(str(tree),
                         "INSERT Person X, Person Y : X name 'bidule', Y name 'chouette', X friend Y")
        
    def test_insert_where(self):
        tree = parse("INSERT Person X: X name 'bidule', X friend Y WHERE Y name 'chouette';", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Insert))
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assert_(isinstance(tree.children[0], nodes.Relation))
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 2)
        for relation in tree.main_relations:
            self.assert_(isinstance(relation, nodes.Relation))
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assert_(isinstance(tree.main_variables[0][1], nodes.VariableRef))
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        # test serializing
        self.assertEqual(str(tree),
                         "INSERT Person X : X name 'bidule', X friend Y WHERE Y name 'chouette'")
        # just check repr() doesn't raise an exception
        repr(tree)
        
    # update tests ############################################################
    
    def test_update_1(self):
        tree = parse("SET X name 'toto' WHERE X is Person, X name 'bidule';", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Update))
        # test serializing
        self.assertEqual(tree.as_string(), "SET X name 'toto' WHERE X is Person, X name 'bidule'")
        # just check repr() doesn't raise an exception
        repr(tree)

    def test_update_2(self):
        tree = parse("SET X know Y WHERE X friend Y;", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Update))
        # test serializing
        self.assertEqual(tree.as_string(), 'SET X know Y WHERE X friend Y')

        
    # deletion tests #########################################################
    
    def test_delete_1(self):
        tree = parse("DELETE Person X WHERE X name 'toto';", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Delete))
        # test serializing
        self.assertEqual(tree.as_string(), 
                         "DELETE Person X WHERE X name 'toto'")
        # just check repr() doesn't raise an exception
        repr(tree)
        
    def test_delete_2(self):
        tree = parse("DELETE X friend Y WHERE X name 'toto';", E_TYPES)
        # test the root node
        self.assert_(isinstance(tree, stmts.Delete))
        # test serializing
        self.assertEqual(tree.as_string(), 
                         "DELETE X friend Y WHERE X name 'toto'")
        
    # as_string tests ####################################################
    
    def test_as_string(self):
        tree = parse("SET X know Y WHERE X friend Y;", E_TYPES)
        self.assertEquals(tree.as_string(), 'SET X know Y WHERE X friend Y')
        
        tree = parse("Person X", E_TYPES)
        self.assertEquals(tree.as_string(),
                          'Any X WHERE X is Person')
        
        tree = parse(u"Any X WHERE X has_text 'héhé'")
        self.assertEquals(tree.as_string('utf8'),
                          u'Any X WHERE X has_text "héhé"'.encode('utf8'))
        tree = parse(u"Any X WHERE X has_text %(text)s", E_TYPES)
        self.assertEquals(tree.as_string('utf8', {'text': u'héhé'}),
                          u'Any X WHERE X has_text "héhé"'.encode('utf8'))
        tree = parse(u"Any X WHERE X has_text %(text)s", E_TYPES)
        self.assertEquals(tree.as_string('utf8', {'text': u'hé"hé'}),
                          u'Any X WHERE X has_text "hé\\"hé"'.encode('utf8'))
        tree = parse(u"Any X WHERE X has_text %(text)s", E_TYPES)
        self.assertEquals(tree.as_string('utf8', {'text': u'hé"\'hé'}),
                          u'Any X WHERE X has_text "hé\\"\'hé"'.encode('utf8'))

    def test_as_string_no_encoding(self):
        tree = parse(u"Any X WHERE X has_text 'héhé'", E_TYPES)
        self.assertEquals(tree.as_string(),
                          u'Any X WHERE X has_text "héhé"')
        tree = parse(u"Any X WHERE X has_text %(text)s", E_TYPES)
        self.assertEquals(tree.as_string(kwargs={'text': u'héhé'}),
                          u'Any X WHERE X has_text "héhé"')

    def test_as_string_now_today_null(self):
        tree = parse(u"Any X WHERE X name NULL", E_TYPES)
        self.assertEquals(tree.as_string(), 'Any X WHERE X name NULL')
        tree = parse(u"Any X WHERE X creation_date NOW", E_TYPES)
        self.assertEquals(tree.as_string(), 'Any X WHERE X creation_date NOW')
        tree = parse(u"Any X WHERE X creation_date TODAY", E_TYPES)
        self.assertEquals(tree.as_string(), 'Any X WHERE X creation_date TODAY')
        
    # non regression tests ####################################################
    
    def test_get_description_aggregat(self):
        tree = parse("Any COUNT(N) WHERE X name N GROUPBY N;", E_TYPES)
        self.assertEqual(tree.get_description(), ['COUNT(name)'])
        self.assertEqual(tree.selected[0].get_type(), 'Int')

    
if __name__ == '__main__':
    unittest_main()
