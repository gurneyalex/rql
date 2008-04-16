"""RQL Syntax tree annotator

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from logilab.common.compat import any

from rql import nodes
from rql._exceptions import BadRQLQuery
from rql.utils import function_description
from rql.stmts import Union

class GoTo(Exception):
    """exception used to control the visit of the tree"""
    def __init__(self, node):
        self.node = node
        

class RQLSTChecker(object):
    """ check a RQL syntax tree for errors not detected on parsing and

    Some simple rewriting of the tree may be done too:
    * if a OR is used on a symetric relation
    * IN function with a single child
    
    use assertions for internal error but specific `BadRQLQuery ` exception for
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
        skipfurther = None
        try:
            node.accept(self, errors)
        except GoTo, ex:
            skipfurther = True
            self._visit(ex.node, errors)
        if skipfurther is None:
            for c in node.children:
                self._visit(c, errors)
            node.leave(self, errors)
            
    def _visit_selectedterm(self, node, errors):
        for i, term in enumerate(node.selected_terms()):
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
        nbselected = len(node.children[0].selected)
        for select in node.children[1:]:
            if not len(select.selected) == nbselected:
                errors.append('when using union, all subqueries should have '
                              'the same number of selected terms')
        if node.sortterms:
            self._visit(node.sortterms, errors)
            
    def leave_union(self, node, errors):
        pass
    
    def visit_select(self, node, errors):
        self._visit_selectedterm(node, errors)
        #XXX from should be added to children, no ?
        for subquery in node.from_:
            self.visit_union(subquery, errors)
            
    def leave_select(self, selection, errors):
        assert len(selection.children) <= 4
        selected = selection.selected
        # check selected variable are used in restriction
        if selection.get_restriction() is not None or len(selected) > 1:
            for term in selected:
                self._check_selected(term, 'selection', errors)

    def visit_insert(self, insert, errors):
        self._visit_selectedterm(insert, errors)
        assert len(insert.children) <= 1

    def leave_insert(self, node, errors):
        pass

    def visit_delete(self, delete, errors):
        self._visit_selectedterm(delete, errors)
        assert len(delete.children) <= 1

    def leave_delete(self, node, errors):
        pass
        
    def visit_update(self, update, errors):
        self._visit_selectedterm(update, errors)
        assert len(update.children) <= 1        
        
    def leave_update(self, node, errors):
        pass                

    # tree nodes ##############################################################
    
    def visit_exists(self, node, errors):
        pass
    def leave_exists(self, node, errors):
        pass
        
    def visit_group(self, group, errors):
        """check that selected variables are used in groups """
        # XXX that's not necessarily true, for instance:
        #     Any X, P, MAX(R) WHERE X content_for F, F path P, X revision R GROUPBY P
        for var in group.stmt.selected:
            if isinstance(var, nodes.VariableRef) and not var in group.children:
                errors.append('variable %s should be grouped' % var)
        self._check_selected(group, 'group', errors)
                
    def _check_union_selected(self, term, termtype, errors):
        """check that variables referenced in the given term are selected"""
        union = term.root
        for vref in term.iget_nodes(nodes.VariableRef):
            # no stinfo yet, use references
            for select in union.children:
                try:
                    for ovref in select.defined_vars[vref.name].references():
                        rel = ovref.relation()
                        if rel is not None:
                            break
                    else:
                        msg = 'variable %s used in %s is not referenced by subquery %s'
                        errors.append(msg % (vref.name, termtype, select.as_string()))
                except KeyError:
                    msg = 'variable %s used in %s is not referenced by subquery %s'
                    errors.append(msg % (vref.name, termtype, select.as_string()))
                    
    def visit_having(self, node, errors):
        pass
                
    def visit_sort(self, sort, errors):
        """check that variables used in sort are selected on DISTINCT query"""
        self._check_union_selected(sort, 'sort', errors)
    
    def visit_sortterm(self, sortterm, errors):
        term = sortterm.term
        if isinstance(term, nodes.Constant):
            for select in sortterm.root.children:
                if len(select.selected) < term.value:
                    errors.append('order column out of bound %s' % term.value)
    
    def visit_and(self, et, errors):
        assert len(et.children) == 2, len(et.children)
        
    def visit_or(self, ou, errors):
        assert len(ou.children) == 2, len(ou.children)
        # simplify Ored expression of a symetric relation
        r1, r2 = ou.children[0], ou.children[1]
        try:
            r1type = r1.r_type
            r2type = r2.r_type
        except AttributeError:
            return # can't be
        if r1type == r2type and self.schema.rschema(r1type).symetric:
            lhs1, rhs1 = r1.get_variable_parts()
            lhs2, rhs2 = r2.get_variable_parts()
            try:
                if (lhs1.variable is rhs2.variable and
                    rhs1.variable is lhs2.variable):
                    ou.parent.replace(ou, r1)
                    for vref in r2.get_nodes(nodes.VariableRef):
                        vref.unregister_reference()
                    raise GoTo(r1)
            except AttributeError:
                pass

    def visit_not(self, not_, errors):
        pass
    def leave_not(self, not_, errors):
        pass
    
    def visit_relation(self, relation, errors):
        if relation.optional and relation.neged_rel():
                errors.append("can use optional relation under NOT (%s)"
                              % relation.as_string())
        # special case "X identity Y"
        if relation.r_type == 'identity':
            lhs, rhs = relation.children
            assert not isinstance(relation.parent, nodes.Not)
            assert rhs.operator == '='
        # special case "C is NULL"
        elif relation.r_type == 'is' and relation.children[1].operator == 'IS':
            lhs, rhs = relation.children
            assert isinstance(lhs, nodes.VariableRef), lhs
            assert isinstance(rhs.children[0], nodes.Constant)
            assert rhs.operator == 'IS', rhs.operator
            assert rhs.children[0].type == None
    
    def leave_relation(self, relation, errors):
        pass
        #assert isinstance(lhs, nodes.VariableRef), '%s: %s' % (lhs.__class__,
        #                                                       relation)
        
    def visit_comparison(self, comparison, errors):
        assert len(comparison.children) in (1,2), len(comparison.children)
    
    def visit_mathexpression(self, mathexpr, errors):
        assert len(mathexpr.children) == 2, len(mathexpr.children)
        
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
                if isinstance(function.children[0], nodes.Function) and \
                       function.children[0].descr().aggregat:
                    errors.append('can\'t nest aggregat functions')
            if funcdescr.name == 'IN':
                assert function.parent.operator == '='
                if len(function.children) == 1:
                    function.parent.append(function.children[0])
                    function.parent.remove(function)
                else:
                    assert len(function.children) >= 1

    def visit_variableref(self, variableref, errors):
        assert len(variableref.children)==0
        assert not variableref.parent is variableref
##         try:
##             assert variableref.variable in variableref.root().defined_vars.values(), \
##                    (variableref.root(), variableref.variable, variableref.root().defined_vars)
##         except AttributeError:
##             raise Exception((variableref.root(), variableref.variable))
    def leave_variableref(self, node, errors):
        pass

    def visit_constant(self, constant, errors):
        assert len(constant.children)==0
        if constant.type == 'etype' and constant.relation().r_type != 'is':
            msg ='using an entity type in only allowed with "is" relation'
            errors.append(msg)
    def leave_constant(self, node, errors):
        pass 

    def leave_comparison(self, node, errors):
        pass
    def leave_mathexpression(self, node, errors):
        pass
    def leave_or(self, node, errors):
        pass
    def leave_and(self, node, errors):
        pass
    def leave_sortterm(self, node, errors):
        pass
    def leave_function(self, node, errors):
        pass
    def leave_group(self, node, errors):
        pass
    def leave_having(self, node, errors):
        pass
    def leave_sort(self, node, errors):
        pass

        
def variable_refs(node):
    for vref in node.iget_nodes(nodes.VariableRef):
        if isinstance(vref.variable, nodes.Variable):
            yield vref
            
class RQLSTAnnotator(object):
    """ annotate RQL syntax tree to ease further code generation from it.
    
    If an optional variable is shared among multiple scopes, it's rewritten to
    use identity relation.
    """

    def __init__(self, schema, special_relations=None):
        self.schema = schema
        self.special_relations = special_relations or {}

    def annotate(self, node):
        #assert not node.annotated
        if isinstance(node, Union):
            self._annotate_union(node)
        else:
            self._annotate_stmt(node)
        node.annotated = True

    def _annotate_union(self, node):
        for select in node.children:
            for subquery in select.from_:
                self._annotate_union(subquery)
            self._annotate_stmt(select)
            
    def _annotate_stmt(self, node):
        for i, term in enumerate(node.selected_terms()):
            for func in term.iget_nodes(nodes.Function):
                if func.descr().aggregat:
                    node.has_aggregat = True
                    break
            # register the selection column index
            for vref in variable_refs(term):
                vref.variable.stinfo['selected'].add(i)
                vref.variable.set_scope(node)
        restr = node.get_restriction()
        if restr is not None:
            restr.accept(self, node)
        
    def rewrite_shared_optional(self, exists, var):
        """if variable is shared across multiple scopes, need some tree
        rewriting
        """
        if var.scope is var.stmt:
            # allocate a new variable
            newvar = var.stmt.make_variable()
            for vref in var.references():
                if vref.scope is exists:
                    rel = vref.relation()
                    vref.unregister_reference()
                    newvref = nodes.VariableRef(newvar)
                    vref.parent.replace(vref, newvref)
                    # update stinfo structure which may have already been
                    # partially processed
                    if rel in var.stinfo['rhsrelations']:
                        lhs, rhs = rel.get_parts()
                        if vref is rhs.children[0] and \
                               self.schema.rschema(rel.r_type).is_final():
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
            rel = exists.add_relation(var, 'identity', newvar)
            # we have to force visit of the introduced relation
            self.visit_relation(rel, exists)
            return newvar
        return None

    # tree nodes ##############################################################
    
    def visit_exists(self, node, scope):
        node.children[0].accept(self, node)
        
    def visit_not(self, node, scope):
        node.children[0].accept(self, scope)
        
    def visit_and(self, node, scope):
        node.children[0].accept(self, scope)
        node.children[1].accept(self, scope)
    visit_or = visit_and
        
    def visit_relation(self, relation, scope):
        assert relation.parent, repr(relation)
        lhs, rhs = relation.get_parts()
        # may be a constant once rqlst has been simplified
        lhsvar = getattr(lhs, 'variable', None)
        if not isinstance(lhsvar, nodes.Variable):
            lhsvar = None
        if relation.is_types_restriction():
            assert rhs.operator == '='
            assert not relation.optional
            if lhsvar is not None:
                lhsvar.stinfo['typerels'].add(relation)
            return
        if relation.optional is not None:
            exists = relation.scope
            if not isinstance(exists, nodes.Exists):
                exists = None
            if lhsvar is not None:
                if exists is not None:
                    newvar = self.rewrite_shared_optional(exists, lhsvar)
                    if newvar is not None:
                        lhsvar = newvar
                if relation.optional == 'right':
                    lhsvar.stinfo['blocsimplification'].add(relation)
                elif relation.optional == 'both':
                    lhsvar.stinfo['blocsimplification'].add(relation)
                    lhsvar.stinfo['optrelations'].add(relation)
                elif relation.optional == 'left':
                    lhsvar.stinfo['optrelations'].add(relation)
            try:
                rhsvar = rhs.children[0].variable
                if exists is not None:
                    newvar = self.rewrite_shared_optional(exists, rhsvar)
                    if newvar is not None:
                        rhsvar = newvar
                if relation.optional == 'right':
                    rhsvar.stinfo['optrelations'].add(relation)
                elif relation.optional == 'both':
                    rhsvar.stinfo['blocsimplification'].add(relation)
                    rhsvar.stinfo['optrelations'].add(relation)
                elif relation.optional == 'left':
                    rhsvar.stinfo['blocsimplification'].add(relation)
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
            lhsvar.stinfo['relations'].add(relation)
            if rtype in self.special_relations:
                key = '%srels' % self.special_relations[rtype]
                if key == 'uidrels':
                    constnode = relation.get_variable_parts()[1]
                    if not (relation.operator() != '=' or
                            isinstance(relation.parent, nodes.Not)):
                        if isinstance(constnode, nodes.Constant):
                            lhsvar.stinfo['constnode'] = constnode
                        lhsvar.stinfo.setdefault(key, set()).add(relation)
                else:
                    lhsvar.stinfo.setdefault(key, set()).add(relation)
            elif rschema.is_final() or rschema.inlined:
                lhsvar.stinfo['blocsimplification'].add(relation)
        for vref in variable_refs(rhs):
            var = vref.variable
            var.set_scope(scope)
            var.stinfo['relations'].add(relation)
            var.stinfo['rhsrelations'].add(relation)
            if vref is rhs.children[0] and rschema.is_final():
                update_attrvars(var, relation, lhs)

def update_attrvars(var, relation, lhs):
    lhsvar = getattr(lhs, 'variable', None)
    var.stinfo['attrvars'].add( (lhsvar, relation.r_type) )
    # give priority to variable which is not in an EXISTS as
    # "main" attribute variable
    if var.stinfo['attrvar'] is None or not isinstance(relation.scope, nodes.Exists):
        var.stinfo['attrvar'] = lhsvar or lhs
    
