"""some rql extensions for manipulating syntax trees

Copyright (c) 2004-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""


from rql.stmts import Select
from rql.nodes import Constant, Variable, VariableRef, Comparison, AND, \
     Sort, SortTerm, Relation
from rql.utils import get_nodes
from rql.undo import *

orig_init = Select.__init__
def __init__(self, *args, **kwargs):
    """override Select.__init__ to add an undo manager and others necessary
    variables
    """
    orig_init(self, *args, **kwargs)
    self.undo_manager = SelectionManager(self)
    self.memorizing = 0
    # used to prevent from memorizing when undoing !
    self.undoing = False
Select.__init__ = __init__

def save_state(self):
    """save the current tree"""
    self.undo_manager.push_state()
    self.memorizing += 1
Select.save_state = save_state

def recover(self):
    """reverts the tree as it was when save_state() was last called"""
    self.memorizing -= 1
    assert self.memorizing >= 0
    self.undo_manager.recover()    
Select.recover = recover

            
# variable manipulation methods ###############################################

orig_make_variable = Select.make_variable
def make_variable(self, e_type=None):
    """override Select.make_variable to memorize variable creation"""
    var = orig_make_variable(self, e_type)
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(MakeVarOperation(var))
    return var
Select.make_variable = make_variable

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
        elif varref.parent.TYPE == 'sortterm':
            self.remove_sort_term(varref.parent)
        elif varref.parent.TYPE == 'group':
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
    for var in self.selected.pop(index).get_nodes(VariableRef):
        var.unregister_reference()
    assert check_relations(self)
Select.remove_selected = remove_selected

def add_selected(self, term, index=None):
    """override Select.add_selected to memoize modification when needed"""
    if isinstance(term, Variable):
        term = VariableRef(term, noautoref=1)
        term.register_reference()
    else:
        for var in term.get_nodes(VariableRef):
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

def add_restriction(self, relation):
    """override Select.add_restriction to memorize modification when needed"""
    assert isinstance(relation, Relation)
    r = self.get_restriction()
    if r is not None:
        new_node = AND(relation, r)
        self.replace(r, new_node)
        if self.memorizing and not self.undoing:
            self.undo_manager.add_operation(ReplaceNodeOperation(r, new_node))
    else:
        self.insert(0, relation)
        if self.memorizing and not self.undoing:
            self.undo_manager.add_operation(AddNodeOperation(relation))
    # register variable references in the added subtree
    for varref in get_nodes(relation, VariableRef):
        varref.register_reference()
    assert check_relations(self)
Select.add_restriction = add_restriction

def remove_node(self, node):
    """remove the given node from the tree"""
    # unregister variable references in the removed subtree
    for varref in get_nodes(node, VariableRef):
        varref.unregister_reference()
        #if not varref.variable.references():
        #    del node.root().defined_vars[varref.name]
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(RemoveNodeOperation(node))
    node.parent.remove(node)
    assert check_relations(self)
Select.remove_node = remove_node

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

def set_distinct(self, value):
    """mark DISTINCT query"""
    if self.memorizing and not self.undoing:
        self.undo_manager.add_operation(SetDistinctOperation(self.distinct))
    self.distinct = value
    
Select.set_distinct = set_distinct


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
    assert term in sortterms
    if len(sortterms) == 1:
        self.remove_node(sortterms)
    else:
        self.remove_node(term)        
Select.remove_sort_term = remove_sort_term

def remove_group_variable(self, var):
    """remove the group variable and the group node if necessary"""
    groups = self.get_groups()
    assert var in groups
    if len(groups) == 1:
        self.remove_node(groups)
    else:
        self.remove_node(var)
Select.remove_group_variable = remove_group_variable

def add_eid_restriction(self, var, eid): 
    """builds a restriction node to express '<var> eid <eid>'"""
    self.add_restriction(make_relation(var, 'eid', (eid, 'Int'), Constant))
Select.add_eid_restriction = add_eid_restriction

def add_constant_restriction(self, var, r_type, value, v_type=None): 
    """builds a restriction node to express '<var> <r_type><constant value>'"""
    if v_type is None:
        if isinstance(value, int):
            v_type = 'Int'
        # FIXME : other cases
        else:
            v_type = 'String'
    self.add_restriction(make_relation(var, r_type, (value, v_type), Constant))
Select.add_constant_restriction = add_constant_restriction

def add_relation(self, lhs_var, r_type, rhs_var): 
    """builds a restriction node to express '<var> eid <eid>'"""
    self.add_restriction(make_relation(lhs_var, r_type, (rhs_var, 1),
                                       VariableRef))
Select.add_relation = add_relation


# utilities functions #########################################################

def make_relation(var, rel, rhs_args, rhs_class):
    """build an relation equivalent to '<var> rel = <cst>'"""
    comp_cst = Comparison("=")
    comp_cst.append(rhs_class(*rhs_args))
    exp = Relation(rel)
    if hasattr(var, 'variable'):
        var = var.variable
    exp.append(VariableRef(var, noautoref=1))
    exp.append(comp_cst)
    return exp

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
    for rel in get_nodes(node, Relation):
        if rel.r_type == 'has_text':
            node.remove_node(rel)
            return
        
def get_variable_refs(node):
    """get the list of variable references in the subtree """
    return get_nodes(node, VariableRef)

def get_relations(node):
    """returns a list of the Relation nodes of the subtree"""
    return get_nodes(node, Relation)

def get_vars_relations(node):
    """returns a dict with 'var_names' as keys, and the list of relations which
    concern them
    """
    exp_concerns = {}
    for exp in get_relations(node):
        for vref in get_variable_refs(exp):
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
    varrefs = get_nodes(node, VariableRef) + list(node.get_selected_variables())
    for n in getattr(node, 'main_relations', ()):
        varrefs += get_nodes(n, VariableRef)
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
