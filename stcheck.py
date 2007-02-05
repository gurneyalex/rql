"""RQL Syntax tree annotator

:organization: Logilab
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from rql import nodes
from rql._exceptions import BadRQLQuery
from rql.utils import function_description

class GoTo(Exception):
    """exception used to control the visit of the tree"""
    def __init__(self, node):
        self.node = node
        
def is_outer_join(ornode):
    """return True if the given OR node is actually a left outer join
    (constructs like 'NOT X travaille S OR X travaille S')
    """
    if len(ornode.children) == 2:
        rel1, rel2 = ornode.children
        if (rel1.r_type == rel2.r_type and rel1._not == (not rel2._not) and
            rel1.children[0].name == rel2.children[0].name and
            rel1.children[1].children[0].name == rel2.children[1].children[0].name):
            # this is a left outer join
            return True
    return False


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
        self._checkselected = checkselected # XXX thread safety
        errors = []
        for i, term in enumerate(node.selected_terms()):
            # selected terms are not included by the default visit,
            # accept manually each of them
            term.accept(self, errors)
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
            try:
                node.leave(self, errors)
            except AttributeError:
                pass
                    
    def _check_selected(self, term, termtype, errors):
        """check that variables referenced in the given term are selected"""
        for var in term.get_nodes(nodes.VariableRef):
            var = var.variable
            rels = [v for v in var.references() if v.relation() is not None]
            if not rels:
                msg = 'variable %s used in %s is not defined in the selection'
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
        if not self._checkselected:
            return
        restr = selection.get_restriction()
        # check selected variable are used in restriction
        if restr is not None or len(selected) > 1:
            for term in selected:
                for varref in term.get_nodes(nodes.VariableRef):
                    if len(varref.variable.references()) == 1:
                        msg = 'selected variable %s is not referenced by any relation'
                        errors.append(msg % varref.name)
                    varref.accept(self, errors)
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
        for term in group.children:
            for varref in term.get_nodes(nodes.VariableRef):
                varref.variable.stinfo['group'] = group
                
    def visit_sort(self, sort, errors):
        """check that variables used in sort are selected on DISTINCT query
        """
        def _name(term):
            name = [term.name]
            if term.children:
                # not a variable
                for var in term.get_nodes(nodes.VariableRef):
                    name.append(var.name)
            return '_'.join(name)
        select = sort.root()
        if select.distinct: # distinct, all variables used in sort must be selected
            selected = [_name(v) for v in select.selected]
            for sortterm in sort:
                for varref in sortterm.var.get_nodes(nodes.VariableRef):
                    varref.variable.stinfo['sort'] = sort
                        
        else: # check sort variables are selected
            self._check_selected(sort, 'sort', errors)
    
    def visit_sortterm(self, sortterm, errors):
        if isinstance(sortterm.var, nodes.Constant):
            if len(sortterm.root().selected) < sortterm.var.value:
                errors.append('order column out of bound %s' % sortterm.var.value)
            
    
                    
    def visit_offset(self, offset, errors):
        assert len(offset.children) == 0, len(offset.children)
        #assert int(offset.offset.value)
    
    def visit_limit(self, limit, errors):
        assert len(limit.children) == 1, len(limit.children)
        assert int(limit.limit.value)
    
    def visit_and(self, et, errors):
        assert len(et.children) == 2, len(et.children)
        
    def visit_or(self, ou, errors):
        assert len(ou.children) == 2, len(ou.children)
        r1, r2 = ou.children[0], ou.children[1]
        r1type = r1.r_type
        r2type = r2.r_type
        # XXX remove variable refs
        # simplify left outer join expression
        if is_outer_join(ou):
            r1.optional = 'both'
            r1._not = False
            ou.parent.replace(ou, r1)
            raise GoTo(r1)
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
        
    def leave_relation(self, relation, errors):
        lhs, rhs = relation.get_parts()
        #assert isinstance(lhs, nodes.VariableRef), '%s: %s' % (lhs.__class__,
        #                                                       relation)
        assert isinstance(rhs, nodes.Comparison), rhs.__class__
        assert not (relation._not and relation.optional)
        lhs, rhs = relation.get_parts()
        rtype = relation.r_type
        lhsvar = lhs.variable
        if relation.is_types_restriction():
            assert rhs.operator == '='
            lhsvar.stinfo['typerels'].add(relation)
            for c in rhs.get_nodes(nodes.Constant):
                c.value = etype = c.value.capitalize()
                if not self.schema.has_entity(etype):
                    errors.append('unkwnown entity\'s type "%s"' % etype)
            return
        lhsvar.stinfo['relations'].add(relation)
        lhsvar.stinfo['lhsrelations'].add(relation)
        try:
            rschema = self.schema.rschema(rtype)
        except KeyError:
            rschema = None # no schema for "has_text" relation for instance
        if rtype in self.special_relations:
            key = '%srels' % self.special_relations[rtype]
            lhsvar.stinfo.setdefault(key, set()).add(relation)
            if key == 'uidrels':
                constnode = relation.get_variable_parts()[1]
                if not (relation._not or relation.operator() != '=') \
                       and isinstance(constnode, nodes.Constant):
                    lhsvar.stinfo['constnode'] = constnode
        else:
            if rschema.is_final() or rschema.physical_mode() == 'subjectinline':
                lhsvar.stinfo['finalrels'].add(relation)
        for varref in rhs.get_nodes(nodes.VariableRef):
            varref.variable.stinfo['relations'].add(relation)
            varref.variable.stinfo['rhsrelations'].add(relation)
            if rschema and rschema.is_final():
                varref.variable.stinfo['attrvar'] = lhsvar
                #varref.variable.stinfo['finalrels'].add(relation)
            
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
        
    def visit_constant(self, constant, errors):
        assert len(constant.children)==0
        if constant.type == 'etype' and constant.relation().r_type != 'is':
            msg ='using an entity type in only allowed with "is" relation'
            errors.append(msg)
        
    def visit_variable(self, variableref, errors):
        pass
