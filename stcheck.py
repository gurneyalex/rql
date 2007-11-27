"""RQL Syntax tree annotator

:organization: Logilab
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from logilab.common.compat import any

from rql import nodes
from rql._exceptions import BadRQLQuery
from rql.utils import function_description

class GoTo(Exception):
    """exception used to control the visit of the tree"""
    def __init__(self, node):
        self.node = node
        

class RQLSTAnnotator:
    """ check a RQL syntax tree for errors not detected on parsing and annotate
    it on the way to ease further code generation from it. Some simple rewriting
    of the tree may be done too
    
    use assertions for internal error but specific `BadRQLQuery ` exception for
    errors due to a bad rql input
    """

    def __init__(self, schema, special_relations=None):
        self.schema = schema
        self.special_relations = special_relations or {}

    def annotate(self, node, checkselected=True):
        self._checkselected = checkselected
        errors = []
        self.scopes = [node]
        self.set_scope = True
        for i, term in enumerate(node.selected_terms()):
            # selected terms are not included by the default visit,
            # accept manually each of them
            self._visit(term, errors)
            # register the selection column index
            for varref in term.get_nodes(nodes.VariableRef):
                varref.variable.stinfo['selected'].add(i)
        self._visit(node, errors)
        if errors:
            raise BadRQLQuery('\n** %s'%'\n** '.join(errors))                
        #if node.TYPE == 'select' and \
        #       not node.defined_vars and not node.get_restriction():
        #    result = []
        #    for term in node.selected_terms():
        #        result.append(term.eval(kwargs))
            
    def _visit(self, node, errors):
        skipfurther = False
        try:
            node.accept(self, errors)
        except GoTo, ex:
            skipfurther = True
            self._visit(ex.node, errors)
        except AttributeError:
            pass
        if not skipfurther:
            for c in node.children:
                self._visit(c, errors)
            node.leave(self, errors)
                    
    def _check_selected(self, term, termtype, errors):
        """check that variables referenced in the given term are selected"""
        if not self._checkselected:
            return
        for var in term.get_nodes(nodes.VariableRef):
            stinfo = var.variable.stinfo
            if not (stinfo['relations'] or stinfo['typerels']):
                msg = 'variable %s used in %s is not referenced by any relation'
                errors.append(msg % (var.name, termtype))

    # statement nodes #########################################################
    
    def visit_insert(self, insert, errors):
        assert len(insert.children) <= 1

    def visit_delete(self, delete, errors):
        assert len(delete.children) <= 1
        
    def visit_update(self, update, errors):
        assert len(update.children) <= 1        
        
    def leave_select(self, selection, errors):
        assert len(selection.children) <= 3
        selected = selection.selected
        restr = selection.get_restriction()
        # check selected variable are used in restriction
        if restr is not None or len(selected) > 1:
            for term in selected:
                self._check_selected(term, 'selection', errors)
        # XXX check aggregat function
##             if var.TYPE == 'function':
##                 tocheck = 1
##             else:
##                 vars.append(var)
##         if tocheck and vars:
##             groups = selection.get_groups()
##             if groups is None:
##                 return
##             for var in vars:
##                 if not var in groups:
##                     errors.append('Variable %s should be grouped' % var)


    # tree nodes ##############################################################
        
    def visit_group(self, group, errors):
        """check that selected variables are used in groups """
        for var in group.root().selected:
            if isinstance(var, nodes.VariableRef) and not var in group:
                errors.append('variable %s should be grouped' % var)
        self._check_selected(group, 'group', errors)
                
    def visit_sort(self, sort, errors):
        """check that variables used in sort are selected on DISTINCT query
        """
        self._check_selected(sort, 'sort', errors)
    
    def visit_sortterm(self, sortterm, errors):
        if isinstance(sortterm.var, nodes.Constant):
            if len(sortterm.root().selected) < sortterm.var.value:
                errors.append('order column out of bound %s' % sortterm.var.value)
    
    def visit_and(self, et, errors):
        assert len(et.children) == 2, len(et.children)
        
    def visit_or(self, ou, errors):
        assert len(ou.children) == 2, len(ou.children)
        r1, r2 = ou.children[0], ou.children[1]
        r1type = r1.r_type
        r2type = r2.r_type
        # XXX remove variable refs
        # simplify Ored expression of a symetric relation
        if r1type == r2type and self.schema.rschema(r1type).symetric:
            lhs1, rhs1 = r1.get_variable_parts()
            lhs2, rhs2 = r2.get_variable_parts()
            try:
                if (lhs1.variable is rhs2.variable and
                    rhs1.variable is lhs2.variable):
                    ou.parent.replace(ou, r1)
                    raise GoTo(r1)
            except AttributeError:
                pass

    def rewrite_shared_optional(self, exists, var, errors):
        """if variable is shared across multiple scopes, need some tree
        rewriting
        """
        if var.scope is var.root:
            # allocate a new variable
            newvar = var.root.make_variable()
            for vref in var.references():
                if vref.exists_root() is exists:
                    rel = vref.relation()
                    vref.unregister_reference()
                    newvref = nodes.VariableRef(newvar)
                    rel.replace(vref, newvref)
            rel = exists.add_relation(var, 'identity', newvar)
            # we have to force visit of the introduced relation
            self._visit(rel, errors)
            return newvar
        return None
    
    def visit_relation(self, relation, errors):
        if relation.is_types_restriction():
            self.set_scope = False
        if relation.optional is not None:
            lhs, rhs = relation.get_parts()
            try:
                lhsvar = lhs.variable
            except AttributeError:
                # may be a constant once rqlst has been simplified
                lhsvar = None
            try:
                rhsvar = rhs.children[0].variable
            except AttributeError:
                # same here
                rhsvar = None
            exists = relation.exists_root()
            if lhsvar is not None:
                if exists is not None:
                    newvar = self.rewrite_shared_optional(exists, lhsvar, errors)
                    if newvar is not None:
                        lhsvar = newvar
                if relation.optional in ('right', 'both'):
                    lhsvar.stinfo['maybesimplified'] = False
            if rhsvar is not None:
                if exists is not None:
                    newvar = self.rewrite_shared_optional(exists, rhsvar, errors)
                    if newvar is not None:
                        rhsvar = newvar
                if relation.optional in ('left', 'both'):
                    rhsvar.stinfo['maybesimplified'] = False

    def leave_relation(self, relation, errors):
        self.set_scope = True
        lhs, rhs = relation.get_parts()
        #assert isinstance(lhs, nodes.VariableRef), '%s: %s' % (lhs.__class__,
        #                                                       relation)
        assert isinstance(rhs, nodes.Comparison), rhs.__class__
        assert not (relation._not and relation.optional)
        lhs, rhs = relation.get_parts()
        rtype = relation.r_type
        try:
            lhsvar = lhs.variable
        except AttributeError:
            # may be a constant once rqlst has been simplified
            lhsvar = None
        if relation.is_types_restriction():
            assert rhs.operator == '='
            if lhsvar is not None:
                lhsvar.stinfo['typerels'].add(relation)
            return
        if lhsvar is not None:
            lhsvar.stinfo['relations'].add(relation)
        try:
            rschema = self.schema.rschema(rtype)
        except KeyError:
            rschema = None # no schema for "has_text" relation for instance
        if lhsvar is not None:
            if rtype in self.special_relations:
                key = '%srels' % self.special_relations[rtype]
                lhsvar.stinfo.setdefault(key, set()).add(relation)
                if key == 'uidrels':
                    constnode = relation.get_variable_parts()[1]
                    if not (relation._not or relation.operator() != '=') \
                           and isinstance(constnode, nodes.Constant):
                        lhsvar.stinfo['constnode'] = constnode
            elif rschema is not None:
                if rschema.is_final() or rschema.inlined:
                    lhsvar.stinfo['maybesimplified'] = False
        for varref in rhs.get_nodes(nodes.VariableRef):
            var = varref.variable
            var.stinfo['relations'].add(relation)
            var.stinfo['rhsrelations'].add(relation)
            if varref is rhs.children[0] and rschema is not None and rschema.is_final():
                var.stinfo['attrvars'].add( (getattr(lhsvar, 'name', None), relation.r_type) )
                # give priority to variable which is not in an EXISTS as
                # "main" attribute variable
                if var.stinfo['attrvar'] is None or not relation.exists_root():
                    var.stinfo['attrvar'] = lhsvar or lhs
            
    def visit_comparison(self, comparison, errors):
        assert len(comparison.children) == 1, len(comparison.children)
    
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
                       function.descr().aggregat:
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
        if self.set_scope:
            variableref.variable.set_scope(self.scopes[-1])
##         try:
##             assert variableref.variable in variableref.root().defined_vars.values(), \
##                    (variableref.root(), variableref.variable, variableref.root().defined_vars)
##         except AttributeError:
##             raise Exception((variableref.root(), variableref.variable))
        
    def visit_constant(self, constant, errors):
        assert len(constant.children)==0
        if constant.type == 'etype' and constant.relation().r_type != 'is':
            msg ='using an entity type in only allowed with "is" relation'
            errors.append(msg)
        
    def visit_variable(self, node, errors):
        pass

    def leave_constant(self, node, errors):
        pass 
    def leave_variableref(self, node, errors):
        pass
    def leave_comparison(self, node, errors):
        pass
    def leave_mathexpression(self, node, errors):
        pass
    def leave_or(self, node, errors):
        pass
    def leave_and(self, node, errors):
        pass
    
    def visit_exists(self, node, errors):
        self.scopes.append(node)
    def leave_exists(self, node, errors):
        self.scopes.pop(0)

    def leave_group(self, node, errors):
        pass
    def leave_sort(self, node, errors):
        pass
    def leave_sortterm(self, node, errors):
        pass
    def leave_function(self, node, errors):
        pass
    def leave_delete(self, node, errors):
        pass
    def leave_insert(self, node, errors):
        pass
    def leave_update(self, node, errors):
        pass

   
