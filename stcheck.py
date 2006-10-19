"""Copyright (c) 2003-2006 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
 
RQL Syntax tree checker
"""

from rql import nodes
from rql._exceptions import BadRQLQuery
from rql.utils import is_function, iget_nodes

class RQLSTChecker:
    """ Check a RQL syntax tree for errors not detected on parsing
    
    use assertions for internal error but specific exceptions for errors due to
    a bad rql input
    """

    def __init__(self, schema):
        self.schema = schema

    def visit(self, node):
        errors = []
        self._visit(node, errors)
        if errors:
            raise BadRQLQuery('\n** %s'%'\n** '.join(errors))
        
    def _visit(self, node, errors):
        func = getattr(self, 'visit_%s' % node.__class__.__name__.lower())
        func(node, errors)
        #node.accept(self, errors)
        for c in node.children:
            self._visit(c, errors)


    def visit_insert(self, insert, errors):
        assert len(insert.children) <= 1
        
#        assert insert.insert_variables

    def visit_delete(self, delete, errors):
        assert len(delete.children) <= 1
#        assert delete.delete_variables or delete.delete_relations
        
    def visit_update(self, update, errors):
        assert len(update.children) <= 1
#        assert update.update_relations
        

    def visit_select(self, selection, errors):
        assert len(selection.children) <= 3
        # check aggregat function
##         tocheck = 0
##         vars = []
        selected = selection.selected
        restr = selection.get_restriction()
        for term in selected:
            for var in term.get_nodes(nodes.VariableRef):
                if (restr is not None or len(selected) > 1) and \
                   len(var.variable.references()) == 1:
                    msg = 'Selected variable %s is not referenced by any relation'
                    errors.append(msg % var.name)
                var.accept(self, errors)
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

        
    def visit_group(self, group, errors):
        """check that selected variables are used in groups """
        for var in group.root().selected:
            if isinstance(var, nodes.VariableRef) and not var in group:
                errors.append('Variable %s should be grouped' % var)
        self._check_selected(group, 'group', errors)
                
    def visit_sort(self, sort, errors):
        """check that variables used in sort are selected on DISTINCT query
        """
        def _name(term):
            name = [term.name]
            if term.children:
                # not a variable
                for var in iget_nodes(term, nodes.VariableRef):
                    name.append(var.name)
            return '_'.join(name)
        select = sort.root()
        if select.distinct: # distinct, all variables used in sort must be selected
            selected = [_name(v) for v in select.selected]
            for sortterm in sort:
                if not _name(sortterm.var) in selected:
                    butvariable = False
                    for var in sortterm.var.get_nodes(nodes.VariableRef):
                        if not _name(var) in selected:
                            break
                    else:
                        butvariable = True
                    if not butvariable:
                        msg = 'Orderby expression "%s" should appear in the selected \
variables'
                        errors.append(msg % var)
        else: # check sort variables are defined be selected
            self._check_selected(sort, 'sort', errors)
                    
    def _check_selected(self, term, termtype, errors):
        for var in iget_nodes(term, nodes.VariableRef):
            var = var.variable
            rels = [v for v in var.references() if v.relation() is not None]
            if not rels:
                msg = 'Variable %s used in %s is not defined in the selection'
                errors.append(msg % (var.name, termtype))
    
                    
    def visit_offset(self, offset, errors):
        assert len(offset.children) == 0, len(offset.children)
        #assert int(offset.offset.value)
    
    def visit_limit(self, limit, errors):
        assert len(limit.children) == 1, len(limit.children)
        assert int(limit.limit.value)
    
    def visit_sortterm(self, sortterm, errors):
        pass
    
    def visit_and(self, et, errors):
        assert len(et.children) == 2, len(et.children)
        
    def visit_or(self, ou, errors):
        assert len(ou.children) == 2, len(ou.children)
        r1, r2 = ou.children[0], ou.children[1]
        try:
            r1type = r1.r_type
            r2type = r2.r_type
        except AttributeError:
            return
        if r1type == r2type and self.schema.rschema(r1type).symetric:
            lhs1, rhs1 = r1.get_variable_parts()
            lhs2, rhs2 = r2.get_variable_parts()
            try:
                if (lhs1.variable is rhs2.variable and
                    rhs1.variable is lhs2.variable):
                    pchildren = ou.parent.children
                    pchildren[pchildren.index(ou)] = r1
            except AttributeError:
                pass # XXX
                    
    def visit_relation(self, relation, errors):
        lhs, rhs = relation.get_parts()
        assert isinstance(lhs, nodes.VariableRef), '%s: %s' % (lhs.__class__,
                                                               relation)
        assert isinstance(rhs, nodes.Comparison), rhs.__class__
        
        #assert (isinstance(lhs, nodes.VariableRef)
        #        or isinstance(lhs, nodes.Function))
        r_type = relation.r_type
        if r_type == 'is':
            assert rhs.operator == '='
            for c in iget_nodes(rhs, nodes.Constant):
                c.value = e_type = c.value.capitalize()
                if not self.schema.has_entity(e_type):
                    errors.append('Unkwnown entity\'s type "%s"'% e_type)
        elif self.schema.has_relation(r_type):
            lhs, rhs = relation.get_parts()
            # expand attribute if necessary
            if not lhs.is_variable() and not rhs.is_variable():
                errors.append('No variable in relation : "%s"' % relation)
##             else:
##                 assert rhs.operator == '='
##                 assert isinstance(rhs.children[0], nodes.VariableRef), \
##                        rhs.children[0]
        else:
            errors.append('No relation named "%s"' % r_type)
        
        
    def visit_comparison(self, comparison, errors):
        assert len(comparison.children) == 1, len(comparison.children)
    
    def visit_mathexpression(self, mathexpr, errors):
        assert len(mathexpr.children) == 2, len(mathexpr.children)
        
    def visit_function(self, function, errors):
        if not is_function(function.name):
            errors.append('Unknown function "%s"' % function.name)
        
        if function.name in ("COUNT", "MIN", "MAX", "AVG", "SUM"):
            assert len(function.children) == 1
            #assert function in function.root().selected
            assert function.parent is None
        elif function.name in ('UPPER', 'LOWER'):
            assert len(function.children) == 1
        elif function.name == 'IN':
            assert function.parent.operator == '='
            if len(function.children) == 1:
                function.parent.append(function.children[0])
                function.parent.remove(function)
            else:
                assert len(function.children) >= 1

    def visit_variableref(self, variableref, errors):
        assert len(variableref.children)==0
        
    def visit_constant(self, constant, errors):
        assert len(constant.children)==0
        if constant.type == 'etype' and constant.relation().r_type != 'is':
            msg ='Using an entity type in only allowed with "is" relation'
            errors.append(msg)
        
    def visit_variable(self, variableref, errors):
        pass
