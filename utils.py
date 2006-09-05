"""Miscellaneous utilities for rql

Copyright (c) 2003-2004 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from __future__ import generators

__revision__ = "$Id: utils.py,v 1.15 2006-02-20 02:06:08 ludal Exp $"

KEYWORDS = ['INSERT', 'SET', 'DELETE',
            'WHERE', 'AND', 'OR', 'NOT'
            'IN', 'LIKE',
            'TRUE', 'FALSE', 'NULL', 'TODAY',
            'GROUPBY', 'ORDERBY', 'ASC', 'DESC',
            'LIMIT', 'OFFSET']
KEYWORDS_DICT = dict(zip(KEYWORDS, [1 for kw in KEYWORDS]))

FUNCTIONS = ['COUNT', 'MIN', 'MAX', 'AVG', 'SUM',
             'UPPER', 'LOWER', 'IN']
FUNCTIONS_DICT = dict(zip(FUNCTIONS, [1 for kw in FUNCTIONS]))
# map function name to type of objects it returns (if known)
F_TYPES = {
    'COUNT': 'Int',
    'UPPER': 'String',
    'LOWER': 'String',
    }

def is_keyword(word):
    """return true if the given word is a RQL keyword"""
    return KEYWORDS_DICT.has_key(word.upper())

def register_function(funcname):
    funcname = funcname.upper()
    assert not funcname in FUNCTIONS
    FUNCTIONS.append(funcname)
    FUNCTIONS_DICT[funcname] = 1
    
def is_function(word):
    """return true if the given word is a RQL function"""
    return word.upper() in FUNCTIONS_DICT

def quote(value):
    """quote a string value"""
    res = ['"']
    for char in value:
        if char == '"':
            res.append('\\')
        res.append(char)
    res.append('"')
    return ''.join(res)

def uquote(value):
    """quote a unicode string value"""
    res = ['"']
    for char in value:
        if char == u'"':
            res.append(u'\\')
        res.append(char)
    res.append(u'"')
    return u''.join(res)

# Visitor #####################################################################

class RQLVisitorHandler:
    """handler providing a dummy implementation of all callbacks necessary
    to visit a RQL syntax tree
    """
    
    def visit_select(self, selection):
        pass
    def visit_insert(self, insert):
        pass
    def visit_delete(self, delete):
        pass
    def visit_update(self, update):
        pass
    
    def visit_group(self, group):
        pass
    def visit_sort(self, sort):
        pass
    def visit_sortterm(self, sortterm):
        pass
    
    def visit_and(self, et):
        pass
    def visit_or(self, ou):
        pass        
    def visit_relation(self, relation):
        pass
    def visit_comparison(self, comparison):
        pass
    def visit_mathexpression(self, mathexpression):
        pass
    def visit_function(self, function):
        pass
    def visit_variableref(self, variable):
        pass
    def visit_constant(self, constant):
        pass

# tree manipulation utilities #################################################

def get_nodes(node, klass):
    """get the list of nodes of a given class in a subtree
    :type node: syntax tree node
    :param node: the node to search in

    :type klass: a node class (Relation, Constant, etc.)
    :param klass: the class of nodes to return

    """
    stack = [ node ]
    result = []
    while stack:
        node = stack.pop(-1)
        if isinstance(node, klass):
            result.append(node)
        if hasattr(node, 'children'):
            stack += node.children
    return result

def get_nodes_filtered(node, klass, filter_func ):
    """get the list of nodes of a given class in a subtree
    :type node: syntax tree node
    :param node: the node to search in

    :type klass: a node class (Relation, Constant, etc.)
    :param klass: the class of nodes to return

    :type filter_func: callable
    :param filter_func: if specified, only yields nodes for which
                        filter_func(klass) returns True
    """
    stack = [ node ]
    result = []
    while stack:
        node = stack.pop(-1)
        if isinstance(node, klass):
            if filter_func(node):
                result.append(node)
        if hasattr(node, 'children'):
            stack += node.children
    return result


def iget_nodes(node, klass, filter_func = bool):
    """Returns an iterator over nodes of a given class under 'node'
    :type node: syntax tree node
    :param node: the node to search in

    :type klass: a node class (Relation, Constant, etc.)
    :param klass: the class of nodes to return

    :type filter_func: callable
    """
    stack = [ node ]
    while stack:
        node = stack.pop(-1)
        if isinstance(node, klass):
            yield node
        if hasattr(node, 'children'):
            stack += node.children



def iget_nodes_filtered(node, klass, filter_func ):
    """Returns an iterator over nodes of a given class under 'node'
    :type node: syntax tree node
    :param node: the node to search in

    :type klass: a node class (Relation, Constant, etc.)
    :param klass: the class of nodes to return

    :type filter_func: callable
    :param filter_func: if specified, only yields nodes for which
                        filter_func(node) returns True
    """
    stack = [ node ]
    while stack:
        node = stack.pop(-1)
        if isinstance(node, klass):
            if filter_func(node):
                yield node
        if hasattr(node, 'children'):
            stack += node.children

iget_nodes = get_nodes
