"""some rql extensions for manipulating syntax trees

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""


from rql.stmts import Select
from rql.nodes import (Constant, Variable, VariableRef, Comparison, AND, 
                       Group, Sort, SortTerm, Relation, make_relation)
from rql.undo import *

            
# variable manipulation methods ###############################################

def undefine_variable(self, var):
    """undefine the given variable and remove all relations where it appears"""
    assert check_relations(self)
    if hasattr(var, 'variable'):
        var = var.variable
    # remove relations where this variable is referenced
    for varref in var.references():
        rel = varref.relation()
        if rel is not None:
            self.remove_node(rel)
            continue
        elif isinstance(varref.parent, SortTerm):
            self.remove_sort_term(varref.parent)
        elif isinstance(varref.parent, Group):
            self.remove_group_variable(varref)
        else: # selected variable
            self.remove_selected(varref)
    # effective undefine operation
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(UndefineVarOperation(var))
    del self.defined_vars[var.name]
    assert check_relations(self)
Select.undefine_variable =  undefine_variable

def remove_selected(self, var):
    """deletes var from selection variable"""
    # XXX it may be a function
    #assert isinstance(var, VariableRef)
    index = var_index(self.selected, var)
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(UnselectVarOperation(var, index))
    for var in self.selected.pop(index).iget_nodes(VariableRef):
        var.unregister_reference()
    assert check_relations(self)
Select.remove_selected = remove_selected

def add_selected(self, term, index=None):
    """override Select.add_selected to memoize modification when needed"""
    if isinstance(term, Variable):
        term = VariableRef(term, noautoref=1)
        term.register_reference()
    else:
        for var in term.iget_nodes(VariableRef):
            var = variable_ref(var)
            var.register_reference()
    if index is not None:
        self.selected.insert(index, term)
    else:
        self.selected.append(term)
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(SelectVarOperation(term))
    assert check_relations(self)
Select.add_selected = add_selected

# basic operations #############################################################

def add_sortvar(self, var, asc=True):
    """add var in 'orderby' constraints
    asc is a boolean indicating the sort order (ascendent or descendent)
    """
    var = variable_ref(var)
    var.register_reference()
    term = SortTerm(var, asc)
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(AddSortOperation(term))
    sort_terms = self.get_sortterms()
    if sort_terms is None:
        sort_terms = Sort()
        self.append(sort_terms)
    sort_terms.append(term)
Select.add_sortvar = add_sortvar


# shortcuts methods ###########################################################

def remove_sort_terms(self):
    """remove a sort term and the sort node if necessary"""
    sortterms = self.get_sortterms()
    if sortterms:
        self.remove_node(sortterms)
Select.remove_sort_terms = remove_sort_terms

def remove_sort_term(self, term):
    """remove a sort term and the sort node if necessary"""
    sortterms = self.get_sortterms()
    assert term in sortterms.children
    if len(sortterms) == 1:
        self.remove_node(sortterms)
    else:
        self.remove_node(term)        
Select.remove_sort_term = remove_sort_term

def remove_group_variable(self, var):
    """remove the group variable and the group node if necessary"""
    groups = self.get_groups()
    assert var in groups.children
    if len(groups.children) == 1:
        self.remove_node(groups)
    else:
        self.remove_node(var)
Select.remove_group_variable = remove_group_variable

# utilities functions #########################################################

def switch_selection(rqlst, new_var, old_var):
    """the select variable switch from old_var (VariableRef instance) to
    new_var (Variable instance)
    """
    rqlst.remove_selected(old_var)
    rqlst.add_selected(new_var, 0)

def add_main_restriction(rqlst, new_type, r_type, direction):
    """the result_tree must represent the same restriction as 'rqlst', plus :
       - 'new_varname' IS <new_type>
       - 'old_main_var' <r_type> 'new_varname' 
    """
    new_var = rqlst.make_variable(new_type)
    # new_var IS new_type
    rqlst.add_restriction(make_relation(new_var, 'is', (new_type, 'etype'),
                                        Constant))
    # new_var REL old_var (ou l'inverse)
    old_var = rqlst.selected[0]
    if direction == 'subject':
        rel_rest = make_relation(old_var.variable, r_type, (new_var, 1),
                                 VariableRef)
    else:
        rel_rest = make_relation(new_var, r_type, (old_var.variable, 1),
                                 VariableRef)
    rqlst.add_restriction(rel_rest)
    return new_var


def remove_has_text_relation(node):
    """remove has_text relation"""
    for rel in node.iget_nodes(Relation):
        if rel.r_type == 'has_text':
            node.remove_node(rel)
            return
        
def get_vars_relations(node):
    """returns a dict with 'var_names' as keys, and the list of relations which
    concern them
    """
    exp_concerns = {}
    for exp in node.iget_nodes(Relation):
        for vref in exp.iget_nodes(VariableRef):
            exp_concerns.setdefault(vref.name, []).append(exp)
    return exp_concerns

def variable_ref(var):
    """get a VariableRef"""
    if isinstance(var, Variable):
        return VariableRef(var, noautoref=1)
    assert isinstance(var, VariableRef)
    return var    

def var_index(list, var):
    """get variable index in the list using identity (Variable and VariableRef
    define __cmp__
    """
    for i in xrange(len(list)):
        if list[i] is var:
            return i
    raise IndexError()

def check_relations(node):
    """test function"""
    varrefs = node.get_nodes(VariableRef)
    varrefs += node.get_selected_variables()
    for n in getattr(node, 'main_relations', ()):
        varrefs += n.iget_nodes(VariableRef)
    refs = {}
    for var in node.defined_vars.values():
        for varref in var.references():
            # be careful, Variable and VariableRef define __cmp__
            if not [v for v in varrefs if v is varref]:
                raise AssertionError('buggy reference %r in %r (actual var: %r)' %
                                         (varref, node, var))
            refs[id(varref)] = 1
    for varref in varrefs:
        if not refs.has_key(id(varref)):
            raise AssertionError('unreferenced varref %r' % varref)
    return True
