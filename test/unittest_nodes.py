# -*- coding: iso-8859-1 -*-

from datetime import date, datetime

from logilab.common.testlib import TestCase, unittest_main

from rql import nodes, stmts, parse, BadRQLQuery, RQLHelper

from unittest_analyze import DummySchema
schema = DummySchema()
from rql.stcheck import RQLSTAnnotator
annotator = RQLSTAnnotator(schema, {})
helper = RQLHelper(schema, None, {'eid': 'uid'})

def sparse(rql):
    tree = helper.parse(rql)
    helper.compute_solutions(tree)
    return tree

class EtypeFromPyobjTC(TestCase):
    def test_bool(self):
        self.assertEquals(nodes.etype_from_pyobj(True), 'Boolean')
        self.assertEquals(nodes.etype_from_pyobj(False), 'Boolean')

    def test_int(self):
        self.assertEquals(nodes.etype_from_pyobj(0), 'Int')
        self.assertEquals(nodes.etype_from_pyobj(1L), 'Int')

    def test_float(self):
        self.assertEquals(nodes.etype_from_pyobj(0.), 'Float')

    def test_datetime(self):
        self.assertEquals(nodes.etype_from_pyobj(datetime.now()), 'Datetime')
        self.assertEquals(nodes.etype_from_pyobj(date.today()), 'Date')

    def test_string(self):
        self.assertEquals(nodes.etype_from_pyobj('hop'), 'String')
        self.assertEquals(nodes.etype_from_pyobj(u'hop'), 'String')


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

    def test_union_set_limit_1(self):
        tree = self._parse("Any X WHERE X is Person")
        select = tree.children[0]
        self.assertRaises(BadRQLQuery, tree.set_limit, 0)
        self.assertRaises(BadRQLQuery, tree.set_limit, -1)
        self.assertRaises(BadRQLQuery, tree.set_limit, '1')
        tree.save_state()
        tree.set_limit(10)
        self.assertEquals(select.limit, 10)
        self.assertEquals(tree.as_string(), 'Any X LIMIT 10 WHERE X is Person')
        tree.recover()
        self.assertEquals(select.limit, None)
        self.assertEquals(tree.as_string(), 'Any X WHERE X is Person')

    def test_union_set_limit_2(self):
        # not undoable set_limit since a new root has to be introduced
        tree = self._parse("(Any X WHERE X is Person) UNION (Any X WHERE X is Company)")
        tree.save_state()
        tree.set_limit(10)
        self.assertEquals(tree.as_string(), 'Any A LIMIT 10 WITH A BEING ((Any X WHERE X is Person) UNION (Any X WHERE X is Company))')
        select = tree.children[0]
        self.assertEquals(select.limit, 10)
        tree.recover()
        self.assertEquals(tree.as_string(), '(Any X WHERE X is Person) UNION (Any X WHERE X is Company)')

    def test_union_set_offset_1(self):
        tree = self._parse("Any X WHERE X is Person")
        select = tree.children[0]
        self.assertRaises(BadRQLQuery, tree.set_offset, -1)
        self.assertRaises(BadRQLQuery, tree.set_offset, '1')
        tree.save_state()
        tree.set_offset(10)
        self.assertEquals(select.offset, 10)
        tree.recover()
        self.assertEquals(select.offset, 0)
        self.assertEquals(tree.as_string(), 'Any X WHERE X is Person')

    def test_union_set_offset_2(self):
        # not undoable set_offset since a new root has to be introduced
        tree = self._parse("(Any X WHERE X is Person) UNION (Any X WHERE X is Company)")
        tree.save_state()
        tree.set_offset(10)
        select = tree.children[0]
        self.assertEquals(tree.as_string(), 'Any A OFFSET 10 WITH A BEING ((Any X WHERE X is Person) UNION (Any X WHERE X is Company))')
        self.assertEquals(select.offset, 10)
        tree.recover()
        self.assertEquals(tree.as_string(), '(Any X WHERE X is Person) UNION (Any X WHERE X is Company)')

    def test_union_undo_add_rel(self):
        tree = self._parse("Any A WITH A BEING ((Any X WHERE X is Person) UNION (Any X WHERE X is Company))")
        tree.save_state()
        select = tree.children[0]
        var = select.make_variable()
        mainvar = select.selection[0].variable
        select.add_relation(mainvar, 'name', var)
        self.assertEquals(tree.as_string(), 'Any A WHERE A name B WITH A BEING ((Any X WHERE X is Person) UNION (Any X WHERE X is Company))')
        tree.recover()
        self.assertEquals(tree.as_string(), 'Any A WITH A BEING ((Any X WHERE X is Person) UNION (Any X WHERE X is Company))')

    def test_select_set_limit(self):
        tree = self._simpleparse("Any X WHERE X is Person")
        self.assertEquals(tree.limit, None)
        self.assertRaises(BadRQLQuery, tree.set_limit, 0)
        self.assertRaises(BadRQLQuery, tree.set_limit, -1)
        self.assertRaises(BadRQLQuery, tree.set_limit, '1')
        tree.save_state()
        tree.set_limit(10)
        self.assertEquals(tree.limit, 10)
        tree.recover()
        self.assertEquals(tree.limit, None)

    def test_select_set_offset(self):
        tree = self._simpleparse("Any X WHERE X is Person")
        self.assertRaises(BadRQLQuery, tree.set_offset, -1)
        self.assertRaises(BadRQLQuery, tree.set_offset, '1')
        self.assertEquals(tree.offset, 0)
        tree.save_state()
        tree.set_offset(0)
        self.assertEquals(tree.offset, 0)
        tree.set_offset(10)
        self.assertEquals(tree.offset, 10)
        tree.recover()
        self.assertEquals(tree.offset, 0)

    def test_select_add_sort_var(self):
        tree = self._parse('Any X')
        tree.save_state()
        select = tree.children[0]
        select.add_sort_var(select.get_variable('X'))
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X ORDERBY X')
        tree.recover()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X')

    def test_select_remove_sort_terms(self):
        tree = self._parse('Any X,Y ORDERBY X,Y')
        tree.save_state()
        select = tree.children[0]
        select.remove_sort_terms()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X,Y')
        tree.recover()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X,Y ORDERBY X,Y')

    def test_select_set_distinct(self):
        tree = self._parse('DISTINCT Any X')
        tree.save_state()
        select = tree.children[0]
        self.assertEquals(select.distinct, True)
        tree.save_state()
        select.set_distinct(True)
        self.assertEquals(select.distinct, True)
        tree.recover()
        self.assertEquals(select.distinct, True)
        select.set_distinct(False)
        self.assertEquals(select.distinct, False)
        tree.recover()
        self.assertEquals(select.distinct, True)

    def test_select_add_group_var(self):
        tree = self._parse('Any X')
        tree.save_state()
        select = tree.children[0]
        select.add_group_var(select.get_variable('X'))
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X GROUPBY X')
        tree.recover()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X')

    def test_select_remove_group_var(self):
        tree = self._parse('Any X GROUPBY X')
        tree.save_state()
        select = tree.children[0]
        select.remove_group_var(select.groupby[0])
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X')
        tree.recover()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X GROUPBY X')

    def test_select_remove_groups(self):
        tree = self._parse('Any X,Y GROUPBY X,Y')
        tree.save_state()
        select = tree.children[0]
        select.remove_groups()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X,Y')
        tree.recover()
        tree.check_references()
        self.assertEquals(tree.as_string(), 'Any X,Y GROUPBY X,Y')

    def test_select_base_1(self):
        tree = self._parse("Any X WHERE X is Person")
        self.assertIsInstance(tree, stmts.Union)
        select = tree.children[0]
        self.assertEqual(select.limit, None)
        self.assertEqual(select.offset, 0)
        self.assertIsInstance(select, stmts.Select)
        self.assertEqual(select.distinct, False)
        self.assertEqual(len(select.children), 2)
        self.assert_(select.children[0] is select.selection[0])
        self.assert_(select.children[1] is select.where)
        self.assertIsInstance(select.where, nodes.Relation)

    def test_select_base_2(self):
        tree = self._simpleparse("Any X WHERE X is Person")
        self.assertEqual(len(tree.children), 2)
        self.assertEqual(tree.distinct, False)

    def test_select_distinct(self):
        tree = self._simpleparse("DISTINCT Any X WHERE X is Person")
        self.assertEqual(len(tree.children), 2)
        self.assertEqual(tree.distinct, True)

    def test_select_null(self):
        tree = self._simpleparse("Any X WHERE X name NULL")
        constant = tree.where.children[1].children[0]
        self.assertEqual(constant.type, None)
        self.assertEqual(constant.value, None)

    def test_select_true(self):
        tree = self._simpleparse("Any X WHERE X name TRUE")
        constant = tree.where.children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, True)

    def test_select_false(self):
        tree = self._simpleparse("Any X WHERE X name FALSE")
        constant = tree.where.children[1].children[0]
        self.assertEqual(constant.type, 'Boolean')
        self.assertEqual(constant.value, False)

    def test_select_date(self):
        tree = self._simpleparse("Any X WHERE X born TODAY")
        constant = tree.where.children[1].children[0]
        self.assertEqual(constant.type, 'Date')
        self.assertEqual(constant.value, 'TODAY')

    def test_select_int(self):
        tree = self._simpleparse("Any X WHERE X name 1")
        constant = tree.where.children[1].children[0]
        self.assertEqual(constant.type, 'Int')
        self.assertEqual(constant.value, 1)

    def test_select_float(self):
        tree = self._simpleparse("Any X WHERE X name 1.0")
        constant = tree.where.children[1].children[0]
        self.assertEqual(constant.type, 'Float')
        self.assertEqual(constant.value, 1.0)

    def test_select_group(self):
        tree = self._simpleparse("Any X GROUPBY N WHERE X is Person, X name N")
        self.assertEqual(tree.distinct, False)
        self.assertEqual(len(tree.children), 3)
        self.assertIsInstance(tree.where, nodes.And)
        self.assertIsInstance(tree.groupby[0], nodes.VariableRef)
        self.assertEqual(tree.groupby[0].name, 'N')

    def test_select_ord_default(self):
        tree = self._parse("Any X ORDERBY N WHERE X is Person, X name N")
        self.assertEqual(tree.children[0].orderby[0].asc, 1)

    def test_select_ord_desc(self):
        tree = self._parse("Any X ORDERBY N DESC WHERE X is Person, X name N")
        select = tree.children[0]
        self.assertEqual(len(select.children), 3)
        self.assertIsInstance(select.where, nodes.And)
        sort = select.orderby
        self.assertIsInstance(sort[0], nodes.SortTerm)
        self.assertEqual(sort[0].term.name, 'N')
        self.assertEqual(sort[0].asc, 0)
        self.assertEqual(select.distinct, False)

    def test_select_group_ord_asc(self):
        tree = self._parse("Any X GROUPBY N ORDERBY N ASC WHERE X is Person, X name N",
                           "Any X GROUPBY N ORDERBY N WHERE X is Person, X name N")
        select = tree.children[0]
        self.assertEqual(len(select.children), 4)
        group = select.groupby
        self.assertIsInstance(group[0], nodes.VariableRef)
        self.assertEqual(group[0].name, 'N')

    def test_select_limit_offset(self):
        tree = self._parse("Any X LIMIT 10 OFFSET 10 WHERE X name 1.0")
        select = tree.children[0]
        self.assertEqual(select.limit, 10)
        self.assertEqual(select.offset, 10)

    def test_exists(self):
        tree = self._simpleparse("Any X,N WHERE X is Person, X name N, EXISTS(X work_for Y)")

    def test_copy(self):
        tree = self._parse("Any X,LOWER(Y) GROUPBY N ORDERBY N WHERE X is Person, X name N, X date >= TODAY")
        select = stmts.Select()
        restriction = tree.children[0].where
        self.check_equal_but_not_same(restriction, restriction.copy(select))
        group = tree.children[0].groupby[0]
        self.check_equal_but_not_same(group, group.copy(select))
        sort = tree.children[0].orderby[0]
        self.check_equal_but_not_same(sort, sort.copy(select))

    def test_selected_index(self):
        tree = self._simpleparse("Any X ORDERBY N DESC WHERE X is Person, X name N")
        annotator.annotate(tree)
        self.assertEquals(tree.defined_vars['X'].selected_index(), 0)
        self.assertEquals(tree.defined_vars['N'].selected_index(), None)

    def test_get_variable_variables(self):
        dummy = self._simpleparse("Any X")
        dummy.solutions = [{'A': 'String', 'B': 'EUser', 'C': 'EGroup'},
                           {'A': 'String', 'B': 'Personne', 'C': 'EGroup'},
                           {'A': 'String', 'B': 'EUser', 'C': 'Societe'}]
        self.assertEquals(dummy.get_variable_variables(), set(['B', 'C']))

    # insertion tests #########################################################

    def test_insert_base_1(self):
        tree = self._parse("INSERT Person X")
        self.assertIsInstance(tree, stmts.Insert)
        self.assertEqual(len(tree.children), 1)
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
        self.assertEqual(len(tree.children), 4)
        self.assertIsInstance(tree.where, nodes.Relation)
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
        self.assertIsInstance(tree, stmts.Set)
        self.assertEqual(len(tree.children), 2)
        self.assertIsInstance(tree.where, nodes.And)


    # deletion tests #########################################################

    def test_delete_1(self):
        tree = self._parse("DELETE Person X WHERE X name 'toto'")
        self.assertIsInstance(tree, stmts.Delete)
        self.assertEqual(len(tree.children), 2)
        self.assertIsInstance(tree.where, nodes.Relation)

    def test_delete_2(self):
        tree = self._parse("DELETE X friend Y WHERE X name 'toto'")
        self.assertIsInstance(tree, stmts.Delete)
        self.assertEqual(len(tree.children), 2)
        self.assertIsInstance(tree.where, nodes.Relation)

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

    # sub-queries tests #######################################################

    def test_subq_colalias_compat(self):
        tree = sparse('Any X ORDERBY N WHERE X creation_date <NOW WITH X,N BEING ('
                     '(Any X,N WHERE X firstname N) UNION (Any X,N WHERE X name N, X is Company))')
        select = tree.children[0]
        select.save_state()
        select.remove_sort_term(select.orderby[0])
        select.recover()
        X = select.get_variable('X')
        N = select.get_variable('N')
        self.assertEquals(len(X.references()), 3)
        self.assertEquals(len(N.references()), 2)
        tree.schema = schema
        #annotator.annotate(tree)
        # XXX how to choose
        self.assertEquals(X.get_type(), 'Company')
        self.assertEquals(X.get_type({'X': 'Person'}), 'Person')
        #self.assertEquals(N.get_type(), 'String')
        self.assertEquals(X.get_description(0, lambda x:x), 'Company, Person, Student')
        self.assertEquals(N.get_description(0, lambda x:x), 'firstname, name')
        self.assertEquals(X.selected_index(), 0)
        self.assertEquals(N.selected_index(), None)
        self.assertEquals(X.main_relation(), None)

    # non regression tests ####################################################

    def test_get_description_and_get_type(self):
        tree = sparse("Any N,COUNT(X),NOW-D GROUPBY N WHERE X name N, X creation_date D;")
        tree.schema = schema
        self.assertEqual(tree.get_description(), [['name', 'COUNT(Company, Person, Student)', 'creation_date']])
        select = tree.children[0]
        self.assertEqual(select.selection[0].get_type(), 'Any')
        self.assertEqual(select.selection[1].get_type(), 'Int')
        self.assertEqual(select.defined_vars['D'].get_type({'D': 'Datetime'}), 'Datetime')
        self.assertEqual(select.selection[2].get_type({'D': 'Datetime'}), 'Interval')

    def test_get_description_simplified(self):
        tree = sparse('Any X,R,D WHERE X eid 2, X work_for R, R creation_date D')
        self.assertEqual(tree.get_description(), [['work_for', 'work_for_object', 'creation_date']])
        helper.simplify(tree)
        # Any since const.uid_type is used while solutions have not been computed
        self.assertEqual(tree.get_description(), [['Any', 'work_for_object', 'creation_date']])

    def test_repr_encoding(self):
        tree = parse(u'Any N where NOT N has_text "bidüle"')
        repr(tree)

    def test_get_description_mainvar_objrel(self):
        tree = sparse('Any X,R,D,Y WHERE X work_for R, R creation_date D, Y owned_by X')
        self.assertEqual(tree.get_description(0), [['Person', 'work_for', 'creation_date', 'owned_by_object']])

    def test_get_description_mainvar_symrel(self):
        tree = sparse('Any X,R,D,Y WHERE X work_for R, R creation_date D, Y connait X')
        self.assertEqual(tree.get_description(0), [['Person, Student', 'work_for', 'creation_date', 'connait']])


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
        self.assertEquals(len(varrefs), 5)
        for varref in varrefs:
            self.assertIsInstance(varref, nodes.VariableRef)
        self.assertEquals(sorted(x.name for x in varrefs),
                          ['X', 'X', 'X', 'Y', 'Y'])

    def test_iknown_values_1(self):
        tree = parse('Any X where X name "turlututu"').children[0]
        constants = list(tree.iget_nodes(nodes.Constant))
        self.assertEquals(len(constants), 1)
        self.assertEquals(isinstance(constants[0], nodes.Constant), 1)
        self.assertEquals(constants[0].value, 'turlututu')

    def test_iknown_values_2(self):
        tree = parse('Any X where X name "turlututu", Y know X, Y name "chapo pointu"').children[0]
        varrefs = list(tree.iget_nodes(nodes.VariableRef))
        self.assertEquals(len(varrefs), 5)
        for varref in varrefs:
            self.assertIsInstance(varref, nodes.VariableRef)
        self.assertEquals(sorted(x.name for x in varrefs),
                          ['X', 'X', 'X', 'Y', 'Y'])

if __name__ == '__main__':
    unittest_main()
