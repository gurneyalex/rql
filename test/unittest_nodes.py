# -*- coding: iso-8859-1 -*-

from logilab.common.testlib import TestCase, unittest_main

from rql import nodes, stmts, parse

def simpleparse(rql):
    return parse(rql).children[0]

from unittest_analyze import DummySchema
schema = DummySchema()
from rql.stcheck import RQLSTAnnotator
annotator = RQLSTAnnotator(schema, {})

class NodesTest(TestCase):
        
    # selection tests #########################################################
    
    def test_select_base_1(self):
        tree = parse("Person X;")
        self.assertIsInstance(tree, stmts.Union)
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X is Person")
        # test limit offset
        self.assertEqual(tree.limit, None)
        self.assertEqual(tree.offset, 0)
        select = tree.children[0]
        self.assertIsInstance(select, stmts.Select)
        # test children
        self.assertEqual(len(select.children), 1)
        self.assertIsInstance(select.children[0], nodes.Relation)
        
    def test_select_base_2(self):
        tree = simpleparse("Any X WHERE X is Person;")
        # test the root node
        self.assertIsInstance(tree, stmts.Select)
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assertIsInstance(tree.children[0], nodes.Relation)
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X is Person")
        
    def test_select_base_3(self):
        tree = simpleparse("DISTINCT Any X WHERE X is Person;")
        # test the root node
        self.assertIsInstance(tree, stmts.Select)
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assertIsInstance(tree.children[0], nodes.Relation)
        # test specific attributes
        self.assertEqual(tree.distinct, 1)
        # test serializing
        self.assertEqual(tree.as_string(), "DISTINCT Any X WHERE X is Person")
        
    def test_select_null(self):
        tree = simpleparse("Any X WHERE X name NULL;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name NULL")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, None)
        self.assertEqual(constant.value, None)
        
    def test_select_bool(self):
        tree = simpleparse("Any X WHERE X name False;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name false")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, False)
        tree = simpleparse("Any X WHERE X name TRUE;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name true")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, True)
        
    def test_select_date(self):
        tree = simpleparse("Any X WHERE X born TODAY;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X born TODAY")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Date')
        self.assertEqual(constant.value, 'TODAY')
        
    def test_select_int(self):
        tree = simpleparse("Any X WHERE X name 1;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name 1")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Int')
        self.assertEqual(constant.value, 1)
        
    def test_select_float(self):
        tree = simpleparse("Any X WHERE X name 1.0;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name 1.0")
        # test constant
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Float')
        self.assertEqual(constant.value, 1.0)
        
    def test_select_group(self):
        tree = simpleparse("Any X WHERE X is Person, X name N GROUPBY N;")
        # test the root node
        self.assertIsInstance(tree, stmts.Select)
        # test children
        self.assertEqual(len(tree.children), 2)
        self.assertIsInstance(tree.children[0], nodes.AND)
        self.assertIsInstance(tree.children[1], nodes.Group)
        self.assertIsInstance(tree.children[1].children[0], nodes.VariableRef)
        self.assertEqual(tree.children[1].children[0].name, 'N')
        # test specific attributes
        self.assertEqual(tree.distinct, False)
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X is Person, X name N GROUPBY N")

    def test_select_ord_default(self):
        tree = parse("Any X WHERE X is Person, X name N ORDERBY N;")
        sort = tree.sortterms
        self.assertEqual(sort.children[0].asc, 1)

    def test_select_ord_desc(self):
        tree = parse("Any X WHERE X is Person, X name N ORDERBY N DESC;")
        self.assertIsInstance(tree, stmts.Union)
        self.assertEqual(len(tree.children), 1)
        self.assertEqual(tree.as_string(),
                         "Any X WHERE X is Person, X name N ORDERBY N DESC")
        select = tree.children[0]
        self.assertIsInstance(select, stmts.Select)
        self.assertEqual(len(select.children), 1)
        self.assertIsInstance(select.children[0], nodes.AND)
        sort = tree.sortterms
        self.assertIsInstance(sort, nodes.Sort)
        self.assertIsInstance(sort.children[0], nodes.SortTerm)
        self.assertEqual(sort.children[0].term.name, 'N')
        self.assertEqual(sort.children[0].asc, 0)
        self.assertEqual(select.distinct, False)

    def test_select_group_ord_asc(self):
        tree = parse("Any X WHERE X is Person, X name N GROUPBY N ORDERBY N ASC;")
        select = tree.children[0]
        # test children
        self.assertEqual(len(select.children), 2)
        group = select.children[1]
        self.assertIsInstance(group, nodes.Group)
        self.assertIsInstance(group.children[0], nodes.VariableRef)
        self.assertEqual(group.children[0].name, 'N')
        self.assertEqual(tree.as_string(),
                         "Any X WHERE X is Person, X name N GROUPBY N ORDERBY N")
        # just check repr() doesn't raise an exception
        repr(tree)

    def test_select_limit_offset(self):
        tree = parse("Any X WHERE X name 1.0 LIMIT 10 OFFSET 10;")
        # test serializing
        self.assertEqual(tree.as_string(), "Any X WHERE X name 1.0 LIMIT 10 OFFSET 10")
        self.assertEqual(tree.limit, 10)
        self.assertEqual(tree.offset, 10)
        
    def test_copy(self):
        tree = parse("Any X, lower(Y) WHERE X is Person, X name N, X date >= today GROUPBY N ORDERBY N ASC;")
        select = stmts.Select()
        restriction = tree.children[0].get_restriction()
        self.check_equal_but_not_same(restriction, restriction.copy(select))
        groups = tree.children[0].get_groups()
        self.check_equal_but_not_same(groups, groups.copy(select))
        sorts = tree.sortterms
        self.check_equal_but_not_same(sorts, sorts.copy(select))
        # just check repr() doesn't raise an exception
        repr(tree)

    def test_selected_index(self):
        tree = simpleparse("Any X WHERE X is Person, X name N ORDERBY N DESC;")
        self.assertEquals(tree.defined_vars['X'].selected_index(), 0)
        self.assertEquals(tree.defined_vars['N'].selected_index(), None)
        
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
        tree = parse("INSERT Person X;")
        # test the root node
        self.assertIsInstance(tree, stmts.Insert)
        # test children
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 0)
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        # test serializing
        self.assertEqual(str(tree), "INSERT Person X")
        
    def test_insert_base_2(self):
        tree = parse("INSERT Person X: X name 'bidule';")
        # test the root node
        self.assertIsInstance(tree, stmts.Insert)
        # test children
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 1)
        self.assertIsInstance(tree.main_relations[0], nodes.Relation)
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        # test serializing
        self.assertEqual(str(tree), "INSERT Person X : X name 'bidule'")

    def test_insert_multi(self):
        tree = parse("INSERT Person X, Person Y: X name 'bidule', Y name 'chouette', X friend Y;")
        # test the root node
        self.assertIsInstance(tree, stmts.Insert)
        # test children
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 3)
        for relation in tree.main_relations:
            self.assertIsInstance(relation, nodes.Relation)
        self.assertEqual(len(tree.main_variables), 2)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        self.assertEqual(tree.main_variables[1][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[1][1].name, 'Y')
        # test serializing
        self.assertEqual(str(tree),
                         "INSERT Person X, Person Y : X name 'bidule', Y name 'chouette', X friend Y")
        
    def test_insert_where(self):
        tree = parse("INSERT Person X: X name 'bidule', X friend Y WHERE Y name 'chouette';")
        # test the root node
        self.assertIsInstance(tree, stmts.Insert)
        # test children
        self.assertEqual(len(tree.children), 1)
        self.assertIsInstance(tree.children[0], nodes.Relation)
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 2)
        for relation in tree.main_relations:
            self.assertIsInstance(relation, nodes.Relation)
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        # test serializing
        self.assertEqual(str(tree),
                         "INSERT Person X : X name 'bidule', X friend Y WHERE Y name 'chouette'")
        # just check repr() doesn't raise an exception
        repr(tree)
        
    # update tests ############################################################
    
    def test_update_1(self):
        tree = parse("SET X name 'toto' WHERE X is Person, X name 'bidule';")
        # test the root node
        self.assertIsInstance(tree, stmts.Update)
        # test serializing
        self.assertEqual(tree.as_string(), "SET X name 'toto' WHERE X is Person, X name 'bidule'")
        # just check repr() doesn't raise an exception
        repr(tree)

    def test_update_2(self):
        tree = parse("SET X know Y WHERE X friend Y;")
        # test the root node
        self.assertIsInstance(tree, stmts.Update)
        # test serializing
        self.assertEqual(tree.as_string(), 'SET X know Y WHERE X friend Y')

        
    # deletion tests #########################################################
    
    def test_delete_1(self):
        tree = parse("DELETE Person X WHERE X name 'toto';")
        # test the root node
        self.assertIsInstance(tree, stmts.Delete)
        # test serializing
        self.assertEqual(tree.as_string(), 
                         "DELETE Person X WHERE X name 'toto'")
        # just check repr() doesn't raise an exception
        repr(tree)
        
    def test_delete_2(self):
        tree = parse("DELETE X friend Y WHERE X name 'toto';")
        # test the root node
        self.assertIsInstance(tree, stmts.Delete)
        # test serializing
        self.assertEqual(tree.as_string(), 
                         "DELETE X friend Y WHERE X name 'toto'")
        
    # as_string tests ####################################################
    
    def test_as_string(self):
        tree = parse("SET X know Y WHERE X friend Y;")
        self.assertEquals(tree.as_string(), 'SET X know Y WHERE X friend Y')
        
        tree = simpleparse("Person X")
        self.assertEquals(tree.as_string(),
                          'Any X WHERE X is Person')
        
        tree = simpleparse(u"Any X WHERE X has_text 'héhé'")
        self.assertEquals(tree.as_string('utf8'),
                          u'Any X WHERE X has_text "héhé"'.encode('utf8'))
        tree = simpleparse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string('utf8', {'text': u'héhé'}),
                          u'Any X WHERE X has_text "héhé"'.encode('utf8'))
        tree = simpleparse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string('utf8', {'text': u'hé"hé'}),
                          u'Any X WHERE X has_text "hé\\"hé"'.encode('utf8'))
        tree = simpleparse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string('utf8', {'text': u'hé"\'hé'}),
                          u'Any X WHERE X has_text "hé\\"\'hé"'.encode('utf8'))

    def test_as_string_no_encoding(self):
        tree = simpleparse(u"Any X WHERE X has_text 'héhé'")
        self.assertEquals(tree.as_string(),
                          u'Any X WHERE X has_text "héhé"')
        tree = simpleparse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string(kwargs={'text': u'héhé'}),
                          u'Any X WHERE X has_text "héhé"')

    def test_as_string_now_today_null(self):
        tree = simpleparse(u"Any X WHERE X name NULL")
        self.assertEquals(tree.as_string(), 'Any X WHERE X name NULL')
        tree = simpleparse(u"Any X WHERE X creation_date NOW")
        self.assertEquals(tree.as_string(), 'Any X WHERE X creation_date NOW')
        tree = simpleparse(u"Any X WHERE X creation_date TODAY")
        self.assertEquals(tree.as_string(), 'Any X WHERE X creation_date TODAY')
        
    # non regression tests ####################################################
    
    def test_get_description_aggregat(self):
        tree = parse("Any COUNT(N) WHERE X name N GROUPBY N;")
        annotator.annotate(tree)
        self.assertEqual(tree.get_description(), [['COUNT(name)']])
        self.assertEqual(tree.children[0].selected[0].get_type(), 'Int')


class GetNodesFunctionTest(TestCase):
    def test_known_values_1(self):
        tree = simpleparse('Any X where X name "turlututu"')
        constants = tree.get_nodes(nodes.Constant)
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')
    
    def test_known_values_2(self):
        tree = simpleparse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"')
        varrefs = tree.get_nodes(nodes.VariableRef)
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
        tree = simpleparse('Any X where X name "turlututu"')
        constants = list(tree.iget_nodes(nodes.Constant))
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')
    
    def test_iknown_values_2(self):
        tree = simpleparse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"')
        varrefs = list(tree.iget_nodes(nodes.VariableRef))
        self.assertEquals(len(varrefs), 4)
        for varref in varrefs:
            self.assertEquals(isinstance(varref, nodes.VariableRef), 1)
        names = [ x.name for x in varrefs ]
        names.sort()
        self.assertEquals(names[0], 'X')
        self.assertEquals(names[1], 'X')
        self.assertEquals(names[2], 'Y')
        self.assertEquals(names[3], 'Y')    
    
if __name__ == '__main__':
    unittest_main()
