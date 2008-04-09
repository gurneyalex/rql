"""some rql utilities functions for manipulating syntax trees

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from rql.nodes import Constant, Variable, VariableRef, Relation, make_relation


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
