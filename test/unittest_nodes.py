# -*- coding: iso-8859-1 -*-

from logilab.common.testlib import TestCase, unittest_main

from rql import nodes, stmts, parse

from unittest_analyze import DummySchema
schema = DummySchema()
from rql.stcheck import RQLSTAnnotator
annotator = RQLSTAnnotator(schema, {})

class NodesTest(TestCase):
    def _parse(self, rql, normrql=None):
        tree = parse(rql + ';')
        tree.check_references()
        if normrql is None:
            normrql = rql
        self.assertEquals(tree.as_string(), normrql)
        # just check repr() doesn't raise an exception
        repr(tree)
        copy = tree.copy()
        self.assertEquals(copy.as_string(), normrql)
        copy.check_references()
        return tree

    def _simpleparse(self, rql):
        return self._parse(rql).children[0]
        
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
    
    # selection tests #########################################################
    
    def test_select_base_1(self):
        tree = self._parse("Any X WHERE X is Person")
        self.assertIsInstance(tree, stmts.Union)
        self.assertEqual(tree.distinct, False)
        self.assertEqual(tree.limit, None)
        self.assertEqual(tree.offset, 0)
        select = tree.children[0]
        self.assertIsInstance(select, stmts.Select)
        self.assertEqual(len(select.children), 1)
        self.assertIsInstance(select.children[0], nodes.Relation)
        
    def test_select_base_2(self):
        tree = self._simpleparse("Any X WHERE X is Person")
        self.assertEqual(len(tree.children), 1)
        self.assertEqual(tree.distinct, False)
        
    def test_select_distinct(self):
        tree = self._simpleparse("DISTINCT Any X WHERE X is Person")
        self.assertEqual(len(tree.children), 1)
        self.assertEqual(tree.distinct, True)
        
    def test_select_null(self):
        tree = self._simpleparse("Any X WHERE X name NULL")
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, None)
        self.assertEqual(constant.value, None)
        
    def test_select_true(self):
        tree = self._simpleparse("Any X WHERE X name TRUE")
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, True)
        
    def test_select_false(self):
        tree = self._simpleparse("Any X WHERE X name FALSE")
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, False)
        
    def test_select_date(self):
        tree = self._simpleparse("Any X WHERE X born TODAY")
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Date')
        self.assertEqual(constant.value, 'TODAY')
        
    def test_select_int(self):
        tree = self._simpleparse("Any X WHERE X name 1")
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Int')
        self.assertEqual(constant.value, 1)
        
    def test_select_float(self):
        tree = self._simpleparse("Any X WHERE X name 1.0")
        constant = tree.children[0].children[1].children[0]
        self.assertEqual(constant.type, 'Float')
        self.assertEqual(constant.value, 1.0)
        
    def test_select_group(self):
        tree = self._simpleparse("Any X WHERE X is Person, X name N GROUPBY N")
        self.assertEqual(tree.distinct, False)
        self.assertEqual(len(tree.children), 2)
        self.assertIsInstance(tree.children[0], nodes.AND)
        self.assertIsInstance(tree.children[1], nodes.Group)
        self.assertIsInstance(tree.children[1].children[0], nodes.VariableRef)
        self.assertEqual(tree.children[1].children[0].name, 'N')

    def test_select_ord_default(self):
        tree = self._parse("Any X WHERE X is Person, X name N ORDERBY N")
        self.assertEqual(tree.sortterms.children[0].asc, 1)

    def test_select_ord_desc(self):
        tree = self._parse("Any X WHERE X is Person, X name N ORDERBY N DESC")
        select = tree.children[0]
        self.assertEqual(len(select.children), 1)
        self.assertIsInstance(select.children[0], nodes.AND)
        sort = tree.sortterms
        self.assertIsInstance(sort, nodes.Sort)
        self.assertIsInstance(sort.children[0], nodes.SortTerm)
        self.assertEqual(sort.children[0].term.name, 'N')
        self.assertEqual(sort.children[0].asc, 0)
        self.assertEqual(select.distinct, False)

    def test_select_group_ord_asc(self):
        tree = self._parse("Any X WHERE X is Person, X name N GROUPBY N ORDERBY N ASC",
                           "Any X WHERE X is Person, X name N GROUPBY N ORDERBY N")
        select = tree.children[0]
        self.assertEqual(len(select.children), 2)
        group = select.children[1]
        self.assertIsInstance(group, nodes.Group)
        self.assertIsInstance(group.children[0], nodes.VariableRef)
        self.assertEqual(group.children[0].name, 'N')

    def test_select_limit_offset(self):
        tree = self._parse("Any X WHERE X name 1.0 LIMIT 10 OFFSET 10")
        self.assertEqual(tree.limit, 10)
        self.assertEqual(tree.offset, 10)
        
    def test_copy(self):
        tree = self._parse("Any X,LOWER(Y) WHERE X is Person, X name N, X date >= TODAY GROUPBY N ORDERBY N")
        select = stmts.Select()
        restriction = tree.children[0].get_restriction()
        self.check_equal_but_not_same(restriction, restriction.copy(select))
        groups = tree.children[0].get_groups()
        self.check_equal_but_not_same(groups, groups.copy(select))
        sorts = tree.sortterms
        self.check_equal_but_not_same(sorts, sorts.copy(select))

    def test_selected_index(self):
        tree = self._simpleparse("Any X WHERE X is Person, X name N ORDERBY N DESC")
        self.assertEquals(tree.defined_vars['X'].selected_index(), 0)
        self.assertEquals(tree.defined_vars['N'].selected_index(), None)
            
    # insertion tests #########################################################

    def test_insert_base_1(self):
        tree = self._parse("INSERT Person X")
        self.assertIsInstance(tree, stmts.Insert)
        self.assertEqual(tree.children, [])
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 0)
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[0][1].name, 'X')
        
    def test_insert_base_2(self):
        tree = self._parse("INSERT Person X : X name 'bidule'")
        # test specific attributes
        self.assertEqual(len(tree.main_relations), 1)
        self.assertIsInstance(tree.main_relations[0], nodes.Relation)
        self.assertEqual(len(tree.main_variables), 1)
        self.assertEqual(tree.main_variables[0][0], 'Person')
        self.assertIsInstance(tree.main_variables[0][1], nodes.VariableRef)
        self.assertEqual(tree.main_variables[0][1].name, 'X')

    def test_insert_multi(self):
        tree = self._parse("INSERT Person X, Person Y : X name 'bidule', Y name 'chouette', X friend Y")
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
        
    def test_insert_where(self):
        tree = self._parse("INSERT Person X : X name 'bidule', X friend Y WHERE Y name 'chouette'")
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
        
    # update tests ############################################################
    
    def test_update_1(self):
        tree = self._parse("SET X name 'toto' WHERE X is Person, X name 'bidule'")
        self.assertIsInstance(tree, stmts.Update)
        self.assertEqual(len(tree.children), 1)
        self.assertIsInstance(tree.children[0], nodes.AND)

        
    # deletion tests #########################################################
    
    def test_delete_1(self):
        tree = self._parse("DELETE Person X WHERE X name 'toto'")
        self.assertIsInstance(tree, stmts.Delete)
        self.assertEqual(len(tree.children), 1)
        self.assertIsInstance(tree.children[0], nodes.Relation)
        
    def test_delete_2(self):
        tree = self._parse("DELETE X friend Y WHERE X name 'toto'")
        self.assertIsInstance(tree, stmts.Delete)
        self.assertEqual(len(tree.children), 1)
        self.assertIsInstance(tree.children[0], nodes.Relation)
        
    # as_string tests ####################################################
    
    def test_as_string(self):
        tree = parse("SET X know Y WHERE X friend Y;")
        self.assertEquals(tree.as_string(), 'SET X know Y WHERE X friend Y')
        
        tree = parse("Person X")
        self.assertEquals(tree.as_string(),
                          'Any X WHERE X is Person')
        
        tree = parse(u"Any X WHERE X has_text 'héhé'")
        self.assertEquals(tree.as_string('utf8'),
                          u'Any X WHERE X has_text "héhé"'.encode('utf8'))
        tree = parse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string('utf8', {'text': u'héhé'}),
                          u'Any X WHERE X has_text "héhé"'.encode('utf8'))
        tree = parse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string('utf8', {'text': u'hé"hé'}),
                          u'Any X WHERE X has_text "hé\\"hé"'.encode('utf8'))
        tree = parse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string('utf8', {'text': u'hé"\'hé'}),
                          u'Any X WHERE X has_text "hé\\"\'hé"'.encode('utf8'))

    def test_as_string_no_encoding(self):
        tree = parse(u"Any X WHERE X has_text 'héhé'")
        self.assertEquals(tree.as_string(),
                          u'Any X WHERE X has_text "héhé"')
        tree = parse(u"Any X WHERE X has_text %(text)s")
        self.assertEquals(tree.as_string(kwargs={'text': u'héhé'}),
                          u'Any X WHERE X has_text "héhé"')

    def test_as_string_now_today_null(self):
        tree = parse(u"Any X WHERE X name NULL")
        self.assertEquals(tree.as_string(), 'Any X WHERE X name NULL')
        tree = parse(u"Any X WHERE X creation_date NOW")
        self.assertEquals(tree.as_string(), 'Any X WHERE X creation_date NOW')
        tree = parse(u"Any X WHERE X creation_date TODAY")
        self.assertEquals(tree.as_string(), 'Any X WHERE X creation_date TODAY')
        
    # non regression tests ####################################################
    
    def test_get_description_aggregat(self):
        tree = parse("Any COUNT(N) WHERE X name N GROUPBY N;")
        annotator.annotate(tree)
        self.assertEqual(tree.get_description(), [['COUNT(name)']])
        self.assertEqual(tree.children[0].selected[0].get_type(), 'Int')


class GetNodesFunctionTest(TestCase):
    def test_known_values_1(self):
        tree = parse('Any X where X name "turlututu"').children[0]
        constants = tree.get_nodes(nodes.Constant)
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')
    
    def test_known_values_2(self):
        tree = parse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"').children[0]
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
        tree = parse('Any X where X name "turlututu"').children[0]
        constants = list(tree.iget_nodes(nodes.Constant))
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')
    
    def test_iknown_values_2(self):
        tree = parse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"').children[0]
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
