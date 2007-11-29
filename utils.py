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
    

from logilab.common.adbh import _GenericAdvFuncHelper, FunctionDescr, \
    register_function as db_register_function

def st_description(cls, funcnode):
    return '%s(%s)' % (cls.name,
                       ', '.join(child.get_description()
                                 for child in iter_funcnode_variables(funcnode)))

FunctionDescr.st_description = classmethod(st_description)
FunctionDescr.supported_backends = ()

def iter_funcnode_variables(funcnode):
    for term in funcnode.children:
        try:
            yield term.variable.stinfo['attrvar'] or term
        except AttributeError, ex:
            yield term    


def is_keyword(word):
    """return true if the given word is a RQL keyword"""
    return word.upper() in KEYWORDS

FUNCTIONS = _GenericAdvFuncHelper.FUNCTIONS.copy()

def register_function(funcdef):
    if isinstance(funcdef, basestring) :
        funcdef = FunctionDescr(funcdef.upper())
    assert not funcdef.name in FUNCTIONS, \
           '%s is already registered' % funcdef.name
    FUNCTIONS[funcdef.name] = funcdef
    for driver in  funcdef.supported_backends:
        db_register_function(driver, funcdef)
    
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


