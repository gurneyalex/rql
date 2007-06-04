"""Miscellaneous utilities for rql

Copyright (c) 2003-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from rql._exceptions import BadRQLQuery


UPPERCASE = u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def decompose_b26(index, table=UPPERCASE):
    """return a letter (base-26) decomposition of index"""
    div, mod = divmod(index, 26)
    if div == 0:
        return table[mod]
    return decompose_b26(div-1) + table[mod]

def rqlvar_maker(stop=None, index=0, defined=None):
    """yields consistent RQL variable names
    
    :param stop: optional argument to stop iteration after the Nth variable
                 default is None which means 'never stop'
    :param defined: optional dict of already defined vars
    """
    index = index
    while stop is None or index < stop:
        var = decompose_b26(index)
        index += 1
        if defined is not None and var in defined:
            continue
        yield var

KEYWORDS = set(('INSERT', 'SET', 'DELETE',
                'WHERE', 'AND', 'OR', 'NOT'
                'IN', 'LIKE',
                'TRUE', 'FALSE', 'NULL', 'TODAY',
                'GROUPBY', 'ORDERBY', 'ASC', 'DESC',
                'LIMIT', 'OFFSET'))
class metafunc(type):
    def __new__(mcs, name, bases, dict):
        dict['name'] = name
        return type.__new__(mcs, name, bases, dict)
    

class FunctionDescr(object):
    __metaclass__ = metafunc
    rtype = None
    aggregat = False
    minargs = 1
    maxargs = 1
    def __init__(self, name=None, rtype=rtype, aggregat=aggregat):
        self.name = name
        self.rtype = rtype
        self.aggregat = aggregat
        
    @classmethod
    def check_nbargs(cls, nbargs):
        if cls.minargs is not None and \
               nbargs < cls.minargs:
            raise BadRQLQuery('not enough argument for function %s' % cls.name)
        if cls.maxargs is not None and \
               nbargs < cls.maxargs:
            raise BadRQLQuery('too many arguments for function %s' % cls.name)

class AggrFunctionDescr(FunctionDescr):
    aggregat = True
    rtype = 'Int' # XXX if the orig type is a final type, returned type should be the same
    
class MAX(AggrFunctionDescr): pass
class MIN(AggrFunctionDescr): pass
class SUM(AggrFunctionDescr): pass
class COUNT(AggrFunctionDescr): 
    rtype = 'Int'
class AVG(AggrFunctionDescr):
    rtype = 'Float'

class UPPER(FunctionDescr):
    rtype = 'String'
class LOWER(FunctionDescr):
    rtype = 'String'
class IN(FunctionDescr):
    """this is actually a 'keyword' function..."""
    maxargs = None
class LENGTH(FunctionDescr):
    rtype = 'Int'
    
FUNCTIONS = {
    # aggregat functions
    'MIN': MIN, 'MAX': MAX,
    'SUM': SUM,
    'COUNT':COUNT,
    'AVG': AVG,
    # transformation functions
    'UPPER': UPPER, 'LOWER': LOWER,
    'LENGTH': LENGTH,
    # keyword function
    'IN': IN
    }

def is_keyword(word):
    """return true if the given word is a RQL keyword"""
    return word.upper() in KEYWORDS

def register_function(funcdef):
    if isinstance(funcdef, basestring) :
        funcdef = FunctionDescr(funcdef.upper())
    assert not funcdef.name in FUNCTIONS, \
           '%s is already registered' % funcdef.name
    FUNCTIONS[funcdef.name] = funcdef
    
def function_description(funcname):
    """return the description (`FunctionDescription`) for a RQL function"""
    return FUNCTIONS[funcname.upper()]

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

def get_nodes_filtered(node, klass, filter_func):
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


