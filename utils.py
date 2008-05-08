"""Miscellaneous utilities for rql

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

UPPERCASE = u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def decompose_b26(index, table=UPPERCASE):
    """return a letter (base-26) decomposition of index"""
    div, mod = divmod(index, 26)
    if div == 0:
        return table[mod]
    return decompose_b26(div-1) + table[mod]

class rqlvar_maker(object):
    """yields consistent RQL variable names
    
    :param stop: optional argument to stop iteration after the Nth variable
                 default is None which means 'never stop'
    :param defined: optional dict of already defined vars
    """
    # NOTE: written a an iterator class instead of a simple generator to be
    #       picklable
    def __init__(self, stop=None, index=0, defined=None):
        self.index = index
        self.stop = stop
        self.defined = defined
        
    def __iter__(self):
        return self
    
    def next(self):
        while self.stop is None or self.index < self.stop:
            var = decompose_b26(self.index)
            self.index += 1
            if self.defined is not None and var in self.defined:
                continue
            return var
        raise StopIteration()
    
KEYWORDS = set(('INSERT', 'SET', 'DELETE',
                'UNION', 'WITH', 'BEING',
                'WHERE', 'AND', 'OR', 'NOT'
                'IN', 'LIKE',
                'TRUE', 'FALSE', 'NULL', 'TODAY',
                'GROUPBY', 'HAVING', 'ORDERBY', 'ASC', 'DESC',
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

_accept = 'lambda self, visitor, *args, **kwargs: visitor.visit_%s(self, *args, **kwargs)' 
_leave = 'lambda self, visitor, *args, **kwargs: visitor.leave_%s(self, *args, **kwargs)' 
def build_visitor_stub(classes):
    for cls in classes:
        cls.accept = eval(_accept % (cls.__name__.lower()))
        cls.leave = eval(_leave % (cls.__name__.lower()))        

class RQLVisitorHandler(object):
    """handler providing a dummy implementation of all callbacks necessary
    to visit a RQL syntax tree
    """
    
    def visit_union(self, union):
        pass
    def visit_insert(self, insert):
        pass
    def visit_delete(self, delete):
        pass
    def visit_set(self, update):
        pass
    
    def visit_select(self, selection):
        pass
    def visit_sortterm(self, sortterm):
        pass
    
    def visit_and(self, et):
        pass
    def visit_or(self, ou):
        pass        
    def visit_not(self, not_):
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


