"""RQL Syntax tree annotator.

:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from itertools import chain
from logilab.common.compat import any
from logilab.common.graph import has_path

from rql._exceptions import BadRQLQuery
from rql.utils import function_description
from rql.nodes import (VariableRef, Constant, Not, Exists, Function,
                       Variable, variable_refs)
from rql.stmts import Union


def _var_graphid(subvarname, trmap, select):
    try:
        return trmap[subvarname]
    except KeyError:
        return subvarname + str(id(select))


class GoTo(Exception):
    """Exception used to control the visit of the tree."""
    def __init__(self, node):
        self.node = node


class RQLSTChecker(object):
    """Check a RQL syntax tree for errors not detected on parsing.

    Some simple rewriting of the tree may be done too:
    * if a OR is used on a symmetric relation
    * IN function with a single child

    use assertions for internal error but specific `BadRQLQuery` exception for
    errors due to a bad rql input
    """

    def __init__(self, schema):
        self.schema = schema

    def check(self, node):
        errors = []
        self._visit(node, errors)
        if errors:
            raise BadRQLQuery('%s\n** %s' % (node, '\n** '.join(errors)))
        #if node.TYPE == 'select' and \
        #       not node.defined_vars and not node.get_restriction():
        #    result = []
        #    for term in node.selected_terms():
        #        result.append(term.eval(kwargs))

    def _visit(self, node, errors):
        try:
            node.accept(self, errors)
        except GoTo, ex:
            self._visit(ex.node, errors)
        else:
            for c in node.children:
                self._visit(c, errors)
            node.leave(self, errors)

    def _visit_selectedterm(self, node, errors):
        for i, term in enumerate(node.selection):
            # selected terms are not included by the default visit,
            # accept manually each of them
            self._visit(term, errors)

    def _check_selected(self, term, termtype, errors):
        """check that variables referenced in the given term are selected"""
        for vref in variable_refs(term):
            # no stinfo yet, use references
            for ovref in vref.variable.references():
                rel = ovref.relation()
                if rel is not None:
                    break
            else:
                msg = 'variable %s used in %s is not referenced by any relation'
                errors.append(msg % (vref.name, termtype))

    # statement nodes #########################################################

    def visit_union(self, node, errors):
        nbselected = len(node.children[0].selection)
        for select in node.children[1:]:
            if not len(select.selection) == nbselected:
                errors.append('when using union, all subqueries should have '
                              'the same number of selected terms')
    def leave_union(self, node, errors):
        pass

    def visit_select(self, node, errors):
        node.vargraph = {} # graph representing links between variable
        node.aggregated = set()
        self._visit_selectedterm(node, errors)

    def leave_select(self, node, errors):
        selected = node.selection
        # check selected variable are used in restriction
        if node.where is not None or len(selected) > 1:
            for term in selected:
                self._check_selected(term, 'selection', errors)
        if node.groupby:
            # check that selected variables are used in groups
            for var in node.selection:
                if isinstance(var, VariableRef) and not var in node.groupby:
                    errors.append('variable %s should be grouped' % var)
            for group in node.groupby:
                self._check_selected(group, 'group', errors)
        if node.distinct and node.orderby:
            # check that variables referenced in the given term are reachable from
            # a selected variable with only ?1 cardinalityselected
            selectidx = frozenset(vref.name for term in selected for vref in term.get_nodes(VariableRef))
            schema = self.schema
            for sortterm in node.orderby:
                for vref in sortterm.term.get_nodes(VariableRef):
                    if vref.name in selectidx:
                        continue
                    for vname in selectidx:
                        try:
                            if self.has_unique_value_path(node, vname, vref.name):
                                break
                        except KeyError:
                            continue # unlinked variable (usually from a subquery)
                    else:
                        msg = ('can\'t sort on variable %s which is linked to a'
                               ' variable in the selection but may have different'
                               ' values for a resulting row')
                        errors.append(msg % vref.name)

    def has_unique_value_path(self, select, fromvar, tovar):
        graph = select.vargraph
        path = has_path(graph, fromvar, tovar)
        if path is None:
            return False
        for tovar in path:
            try:
                rtype = graph[(fromvar, tovar)]
                cardidx = 0
            except KeyError:
                rtype = graph[(tovar, fromvar)]
                cardidx = 1
            rschema = self.schema.rschema(rtype)
            for rdef in rschema.rdefs.itervalues():
                # XXX aggregats handling needs much probably some enhancements...
                if not (tovar in select.aggregated
                        or rdef.cardinality[cardidx] in '?1'):
                    return False
            fromvar = tovar
        return True


    def visit_insert(self, insert, errors):
        self._visit_selectedterm(insert, errors)
    def leave_insert(self, node, errors):
        pass

    def visit_delete(self, delete, errors):
        self._visit_selectedterm(delete, errors)
    def leave_delete(self, node, errors):
        pass

    def visit_set(self, update, errors):
        self._visit_selectedterm(update, errors)
    def leave_set(self, node, errors):
        pass

    # tree nodes ##############################################################

    def visit_exists(self, node, errors):
        pass
    def leave_exists(self, node, errors):
        pass

    def visit_subquery(self, node, errors):
        pass

    def leave_subquery(self, node, errors):
        # copy graph information we're interested in
        pgraph = node.parent.vargraph
        for select in node.query.children:
            # map subquery variable names to outer query variable names
            trmap = {}
            for i, vref in enumerate(node.aliases):
                try:
                    subvref = select.selection[i]
                except IndexError:
                    errors.append('subquery "%s" has only %s selected terms, needs %s'
                                  % (select, len(select.selection), len(node.aliases)))
                    continue
                if isinstance(subvref, VariableRef):
                    trmap[subvref.name] = vref.name
                elif (isinstance(subvref, Function) and subvref.descr().aggregat
                      and len(subvref.children) == 1
                      and isinstance(subvref.children[0], VariableRef)):
                    # XXX ok for MIN, MAX, but what about COUNT, AVG...
                    trmap[subvref.children[0].name] = vref.name
                    node.parent.aggregated.add(vref.name)
            for key, val in select.vargraph.iteritems():
                if isinstance(key, tuple):
                    key = (_var_graphid(key[0], trmap, select),
                           _var_graphid(key[1], trmap, select))
                    pgraph[key] = val
                else:
                    values = pgraph.setdefault(_var_graphid(key, trmap, select), [])
                    values += [_var_graphid(v, trmap, select) for v in val]

    def visit_sortterm(self, sortterm, errors):
        term = sortterm.term
        if isinstance(term, Constant):
            for select in sortterm.root.children:
                if len(select.selection) < term.value:
                    errors.append('order column out of bound %s' % term.value)
        else:
            stmt = term.stmt
            for tvref in variable_refs(term):
                for vref in tvref.variable.references():
                    if vref.relation() or vref in stmt.selection:
                        break
                else:
                    msg = 'sort variable %s is not referenced any where else'
                    errors.append(msg % tvref.name)

    def leave_sortterm(self, node, errors):
        pass

    def visit_and(self, et, errors):
        pass #assert len(et.children) == 2, len(et.children)
    def leave_and(self, node, errors):
        pass

    def visit_or(self, ou, errors):
        #assert len(ou.children) == 2, len(ou.children)
        # simplify Ored expression of a symmetric relation
        r1, r2 = ou.children[0], ou.children[1]
        try:
            r1type = r1.r_type
            r2type = r2.r_type
        except AttributeError:
            return # can't be
        if r1type == r2type and self.schema.rschema(r1type).symmetric:
            lhs1, rhs1 = r1.get_variable_parts()
            lhs2, rhs2 = r2.get_variable_parts()
            try:
                if (lhs1.variable is rhs2.variable and
                    rhs1.variable is lhs2.variable):
                    ou.parent.replace(ou, r1)
                    for vref in r2.get_nodes(VariableRef):
                        vref.unregister_reference()
                    raise GoTo(r1)
            except AttributeError:
                pass
    def leave_or(self, node, errors):
        pass

    def visit_not(self, not_, errors):
        pass
    def leave_not(self, not_, errors):
        pass

    def visit_relation(self, relation, errors):
        if relation.optional and relation.neged():
            errors.append("can use optional relation under NOT (%s)"
                          % relation.as_string())
        # special case "X identity Y"
        if relation.r_type == 'identity':
            lhs, rhs = relation.children
            #assert not isinstance(relation.parent, Not)
            #assert rhs.operator == '='
        elif relation.r_type == 'is':
            # special case "C is NULL"
            if relation.children[1].operator == 'IS':
                lhs, rhs = relation.children
                #assert isinstance(lhs, VariableRef), lhs
                #assert isinstance(rhs.children[0], Constant)
                #assert rhs.operator == 'IS', rhs.operator
                #assert rhs.children[0].type == None
        else:
            try:
                rschema = self.schema.rschema(relation.r_type)
            except KeyError:
                errors.append('unknown relation `%s`' % relation.r_type)
            else:
                if relation.optional and rschema.final:
                    errors.append("shouldn't use optional on final relation `%s`"
                                  % relation.r_type)
        try:
            vargraph = relation.stmt.vargraph
            rhsvarname = relation.children[1].children[0].variable.name
            lhsvarname = relation.children[0].name
        except AttributeError:
            pass
        else:
            vargraph.setdefault(lhsvarname, []).append(rhsvarname)
            vargraph.setdefault(rhsvarname, []).append(lhsvarname)
            vargraph[(lhsvarname, rhsvarname)] = relation.r_type

    def leave_relation(self, relation, errors):
        pass
        #assert isinstance(lhs, VariableRef), '%s: %s' % (lhs.__class__,
        #                                                       relation)

    def visit_comparison(self, comparison, errors):
        pass #assert len(comparison.children) in (1,2), len(comparison.children)
    def leave_comparison(self, node, errors):
        pass

    def visit_mathexpression(self, mathexpr, errors):
        pass #assert len(mathexpr.children) == 2, len(mathexpr.children)
    def leave_mathexpression(self, node, errors):
        pass

    def visit_function(self, function, errors):
        try:
            funcdescr = function_description(function.name)
        except KeyError:
            errors.append('unknown function "%s"' % function.name)
        else:
            try:
                funcdescr.check_nbargs(len(function.children))
            except BadRQLQuery, ex:
                errors.append(str(ex))
            if funcdescr.aggregat:
                if isinstance(function.children[0], Function) and \
                       function.children[0].descr().aggregat:
                    errors.append('can\'t nest aggregat functions')
            if funcdescr.name == 'IN':
                #assert function.parent.operator == '='
                if len(function.children) == 1:
                    function.parent.append(function.children[0])
                    function.parent.remove(function)
                #else:
                #    assert len(function.children) >= 1
    def leave_function(self, node, errors):
        pass

    def visit_variableref(self, variableref, errors):
        #assert len(variableref.children)==0
        #assert not variableref.parent is variableref
##         try:
##             assert variableref.variable in variableref.root().defined_vars.values(), \
##                    (variableref.root(), variableref.variable, variableref.root().defined_vars)
##         except AttributeError:
##             raise Exception((variableref.root(), variableref.variable))
        pass

    def leave_variableref(self, node, errors):
        pass

    def visit_constant(self, constant, errors):
        #assert len(constant.children)==0
        if constant.type == 'etype':
            if constant.relation().r_type not in ('is', 'is_instance_of'):
                msg ='using an entity type in only allowed with "is" relation'
                errors.append(msg)
            if not constant.value in self.schema:
                errors.append('unknown entity type %s' % constant.value)

    def leave_constant(self, node, errors):
        pass



class RQLSTAnnotator(object):
    """Annotate RQL syntax tree to ease further code generation from it.

    If an optional variable is shared among multiple scopes, it's rewritten to
    use identity relation.
    """

    def __init__(self, schema, special_relations=None):
        self.schema = schema
        self.special_relations = special_relations or {}

    def annotate(self, node):
        #assert not node.annotated
        node.accept(self)
        node.annotated = True

    def _visit_stmt(self, node):
        for var in node.defined_vars.itervalues():
            var.prepare_annotation()
        for i, term in enumerate(node.selection):
            for func in term.iget_nodes(Function):
                if func.descr().aggregat:
                    node.has_aggregat = True
                    break
            # register the selection column index
            for vref in term.get_nodes(VariableRef):
                vref.variable.stinfo['selected'].add(i)
                vref.variable.set_scope(node)
                vref.variable.set_sqlscope(node)
        if node.where is not None:
            node.where.accept(self, node, node)

    visit_insert = visit_delete = visit_set = _visit_stmt

    def visit_union(self, node):
        for select in node.children:
            self.visit_select(select)

    def visit_select(self, node):
        for var in node.aliases.itervalues():
            var.prepare_annotation()
        if node.with_ is not None:
            for subquery in node.with_:
                self.visit_union(subquery.query)
                subquery.query.schema = node.root.schema
        node.has_aggregat = False
        self._visit_stmt(node)
        if node.having:
            # if there is a having clause, bloc simplification of variables used in GROUPBY
            for term in node.groupby:
                for vref in term.get_nodes(VariableRef):
                    vref.variable.stinfo['blocsimplification'].add(term)
        for var in node.defined_vars.itervalues():
            if not var.stinfo['relations'] and var.stinfo['typerels'] and not var.stinfo['selected']:
                raise BadRQLQuery('unbound variable %s (%s)' % (var.name, var.stmt.root))
            if len(var.stinfo['uidrels']) > 1:
                uidrels = iter(var.stinfo['uidrels'])
                val = getattr(uidrels.next().get_variable_parts()[1], 'value', object())
                for uidrel in uidrels:
                    if getattr(uidrel.get_variable_parts()[1], 'value', None) != val:
                        # XXX should check OR branch and check simplify in that case as well
                        raise BadRQLQuery('conflicting eid values for %s' % var.name)

    def rewrite_shared_optional(self, exists, var):
        """if variable is shared across multiple scopes, need some tree
        rewriting
        """
        if var.scope is var.stmt:
            # allocate a new variable
            newvar = var.stmt.make_variable()
            newvar.prepare_annotation()
            for vref in var.references():
                if vref.scope is exists:
                    rel = vref.relation()
                    vref.unregister_reference()
                    newvref = VariableRef(newvar)
                    vref.parent.replace(vref, newvref)
                    # update stinfo structure which may have already been
                    # partially processed
                    if rel in var.stinfo['rhsrelations']:
                        lhs, rhs = rel.get_parts()
                        if vref is rhs.children[0] and \
                               self.schema.rschema(rel.r_type).final:
                            update_attrvars(newvar, rel, lhs)
                            lhsvar = getattr(lhs, 'variable', None)
                            var.stinfo['attrvars'].remove( (lhsvar, rel.r_type) )
                            if var.stinfo['attrvar'] is lhsvar:
                                if var.stinfo['attrvars']:
                                    var.stinfo['attrvar'] = iter(var.stinfo['attrvars']).next()
                                else:
                                    var.stinfo['attrvar'] = None
                        var.stinfo['rhsrelations'].remove(rel)
                        newvar.stinfo['rhsrelations'].add(rel)
                    for stinfokey in ('blocsimplification','typerels', 'uidrels',
                                      'relations', 'optrelations'):
                        try:
                            var.stinfo[stinfokey].remove(rel)
                            newvar.stinfo[stinfokey].add(rel)
                        except KeyError:
                            continue
            # shared references
            newvar.stinfo['constnode'] = var.stinfo['constnode']
            if newvar.stmt.solutions: # solutions already computed
                newvar.stinfo['possibletypes'] = var.stinfo['possibletypes']
                for sol in newvar.stmt.solutions:
                    sol[newvar.name] = sol[var.name]
            rel = exists.add_relation(var, 'identity', newvar)
            # we have to force visit of the introduced relation
            self.visit_relation(rel, exists, exists)
            return newvar
        return None

    # tree nodes ##############################################################

    def visit_exists(self, node, scope, sqlscope):
        node.children[0].accept(self, node, node)

    def visit_not(self, node, scope, sqlscope):
        node.children[0].accept(self, scope, node)

    def visit_and(self, node, scope, sqlscope):
        node.children[0].accept(self, scope, sqlscope)
        node.children[1].accept(self, scope, sqlscope)
    visit_or = visit_and

    def visit_relation(self, relation, scope, sqlscope):
        #assert relation.parent, repr(relation)
        lhs, rhs = relation.get_parts()
        # may be a constant once rqlst has been simplified
        lhsvar = getattr(lhs, 'variable', None)
        if relation.is_types_restriction():
            #assert rhs.operator == '='
            #assert not relation.optional
            if lhsvar is not None:
                lhsvar.stinfo['typerels'].add(relation)
            return
        if relation.optional is not None:
            exists = relation.scope
            if not isinstance(exists, Exists):
                exists = None
            if lhsvar is not None:
                if exists is not None:
                    newvar = self.rewrite_shared_optional(exists, lhsvar)
                    if newvar is not None:
                        lhsvar = newvar
                lhsvar.stinfo['blocsimplification'].add(relation)
                if relation.optional == 'both':
                    lhsvar.stinfo['optrelations'].add(relation)
                elif relation.optional == 'left':
                    lhsvar.stinfo['optrelations'].add(relation)
            try:
                rhsvar = rhs.children[0].variable
                if exists is not None:
                    newvar = self.rewrite_shared_optional(exists, rhsvar)
                    if newvar is not None:
                        rhsvar = newvar
                rhsvar.stinfo['blocsimplification'].add(relation)
                if relation.optional == 'right':
                    rhsvar.stinfo['optrelations'].add(relation)
                elif relation.optional == 'both':
                    rhsvar.stinfo['optrelations'].add(relation)
            except AttributeError:
                # may have been rewritten as well
                pass
        rtype = relation.r_type
        try:
            rschema = self.schema.rschema(rtype)
        except KeyError:
            raise BadRQLQuery('no relation %s' % rtype)
        if lhsvar is not None:
            lhsvar.set_scope(scope)
            lhsvar.set_sqlscope(sqlscope)
            lhsvar.stinfo['relations'].add(relation)
            if rtype in self.special_relations:
                key = '%srels' % self.special_relations[rtype]
                if key == 'uidrels':
                    constnode = relation.get_variable_parts()[1]
                    if not (relation.operator() != '=' or
                            isinstance(relation.parent, Not)):
                        if isinstance(constnode, Constant):
                            lhsvar.stinfo['constnode'] = constnode
                        lhsvar.stinfo.setdefault(key, set()).add(relation)
                else:
                    lhsvar.stinfo.setdefault(key, set()).add(relation)
            elif rschema.final or rschema.inlined:
                lhsvar.stinfo['blocsimplification'].add(relation)
        for vref in rhs.get_nodes(VariableRef):
            var = vref.variable
            var.set_scope(scope)
            var.set_sqlscope(sqlscope)
            var.stinfo['relations'].add(relation)
            var.stinfo['rhsrelations'].add(relation)
            if vref is rhs.children[0] and rschema.final:
                update_attrvars(var, relation, lhs)


def update_attrvars(var, relation, lhs):
    lhsvar = getattr(lhs, 'variable', None)
    var.stinfo['attrvars'].add( (lhsvar, relation.r_type) )
    # give priority to variable which is not in an EXISTS as
    # "main" attribute variable
    if var.stinfo['attrvar'] is None or not isinstance(relation.scope, Exists):
        var.stinfo['attrvar'] = lhsvar or lhs

