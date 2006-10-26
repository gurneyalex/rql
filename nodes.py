"""Copyright (c) 2004-2006 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
 
This module defines all the nodes we can find in a RQL Syntax tree, except
root nodes, defined in the stmts module.
"""


from logilab.common import cached
from logilab.common.tree import VNode as Node, BinaryNode, ListNode, \
     post_order_list
from logilab.common.visitor import VisitedMixIn

from rql.utils import F_TYPES, quote, uquote

def get_visit_name(self):
    """
    return the visit name for the mixed class. When calling 'accept', the
    method <'visit_' + name returned by this method> will be called on the
    visitor
    """
    return self.__class__.__name__.lower()
Node.get_visit_name = get_visit_name
BinaryNode.get_visit_name = get_visit_name
ListNode.get_visit_name = get_visit_name


FUNC_TYPES_MAP = {
    'COUNT' : 'Int',
    'MIN' : 'Int',
    'MAX' : 'Int',
    'SUM' : 'Int',
    'LOWER' : 'String',
    'UPPER' : 'String',
    }

# base objects ################################################################

class HSMixin(object):
    """mixin class for classes which may be the lhs or rhs of an expression
    """    
    def relation(self):
        """return the parent relation where self occurs or None"""
        parent = self.parent
        while parent is not None and not parent.TYPE == 'relation':
            parent = parent.parent
        return parent
    #relation = cached(relation)
    
    def is_variable(self):
        """check if this node contains a reference to one ore more variables"""
        for c in post_order_list(self):
            if isinstance(c, VariableRef):
                return 1
        return 0
    
    def __str__(self):
        return self.as_string()


# add a new "copy" method to the Node base class
def deepcopy(self, stmt):
    """create and return a copy of this node and its descendant

    stmt is the root node, which should be use to get new variables
    """
    new = self.__class__(*self.initargs(stmt))
    for child in self.children:
        new.append(child.copy(stmt))
    return new
Node.copy = deepcopy

def initargs(self, stmt):
    """return list of arguments to give to __init__ to clone this node
    
    I don't use __getinitargs__ because I'm not sure it should interfer with
    copy/pickle
    """
    return ()
Node.initargs = initargs

def is_equivalent(self, other):
    if other.TYPE != self.TYPE:
        return False
    for i, child in enumerate(self.children):
        try:
            if not child.is_equivalent(other.children[i]):
                print 'grrrr', repr(child), '|', repr(other.children[i])
                return False
        except IndexError:
            print 'grr', self
            return False
    return True
Node.is_equivalent = is_equivalent

# RQL base nodes ##############################################################


class AND(BinaryNode):
    """a logical AND node (binary)
    """
    TYPE = 'and'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_and( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_and( self, *args, **kwargs )
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '%s, %s' % (self.children[0].as_string(encoding, kwargs),
                           self.children[1].as_string(encoding, kwargs))
    def __repr__(self):
        return '%s AND %s' % (repr(self.children[0]),
                              repr(self.children[1]))

    
class OR(BinaryNode):
    """a logical OR node (binary)
    """
    TYPE = 'or'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_or( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_or( self, *args, **kwargs )
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '%s OR %s' % (self.children[0].as_string(encoding, kwargs),
                             self.children[1].as_string(encoding, kwargs))
    def __repr__(self):
        return '%s OR %s' % (repr(self.children[0]),
                             repr(self.children[1]))

    
class Relation(Node):
    """a single RQL relation
    """
    TYPE = 'relation'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_relation( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_relation( self, *args, **kwargs )
    
    def __init__(self, r_type, _not=0, optional=False):
        Node.__init__(self)
        self.r_type = r_type.encode()
        self._not = _not
        self.optional = optional

    def is_equivalent(self, other):
        if not is_equivalent(self, other):
            return False
        if self.r_type != other.r_type:
            return False
        if self._not != other._not:
            return False
        return True
    
    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return self.r_type, self._not, self.optional
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        if self.optional:
            rtype = '?%s' % self.r_type
        else:
            rtype = self.r_type
        try:
            if not self._not:
                return '%s %s %s' % (self.children[0].as_string(encoding, kwargs),
                                     rtype,
                                     self.children[1].as_string(encoding, kwargs))
            return 'NOT %s %s %s' % (self.children[0].as_string(encoding, kwargs),
                                     rtype,
                                     self.children[1].as_string(encoding, kwargs))
        except IndexError:
            return repr(self)

    def __repr__(self, indent=0):
        if self.optional:
            rtype = '?%s' % self.r_type
        else:
            rtype = self.r_type
        try:
            if not self._not:
                return '%sRelation(%r %s %r)' % (' '*indent, self.children[0],
                                                 rtype, self.children[1])
            return '%sRelation(not %r %s %r)' % (' '*indent, self.children[0],
                                                 rtype, self.children[1])
        except IndexError:
            return '%sRelation(%s)' % (' '*indent, self.r_type)
            
    def __str__(self):
        return self.as_string('ascii')
            
       
    def get_parts(self):
        """return the left hand side and the right hand side of this relation
        """
        lhs = self.children[0]
        rhs = self.children[1]
        return lhs, rhs

    def get_variable_parts(self):
        """return the left hand side and the right hand side of this relation,
        ignoring comparison
        """
        lhs = self.children[0]
        rhs = self.children[1].children[0]
        return lhs, rhs
    
class Comparison(HSMixin, Node):
    """handle comparisons:

     <, <=, =, >=, > and LIKE operator have a unique children.    
    """
    TYPE = 'comparison'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_comparison( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_comparison( self, *args, **kwargs )

    def __init__(self, operator, value=None):
        Node.__init__(self)
        if operator == '~=':
            operator = 'LIKE'
        elif operator == '=' and isinstance(value, Constant) and \
                 value.type is None:
            operator = 'IS'            
        assert operator in ('<', '<=', '=', '>=', '>', 'LIKE', 'IS')
        self.operator = operator
        if value is not None:
            self.append(value)

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.operator,)
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        if len(self.children)==0:
            return self.operator
        if self.operator in ('=', 'IS'):
            return self.children[0].as_string(encoding, kwargs)
        else:
            return '%s %s' % (self.operator.encode(),
                              self.children[0].as_string(encoding, kwargs))

    def __repr__(self, indent=0):
        return '%s%s %s' % (' '*indent, self.operator,
                            ', '.join([repr(c) for c in self.children]))

    

class MathExpression(HSMixin, BinaryNode):
    """+, -, *, /
    """
    TYPE = 'mathexpression'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_mathexpression(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_mathexpression(self, *args, **kwargs)

    def __init__(self, operator, lhs=None, rhs=None):
        BinaryNode.__init__(self, lhs, rhs)
        self.operator = operator

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.operator,)
                
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '(%s %s %s)' % (self.children[0].as_string(encoding, kwargs),
                               self.operator.encode(),
                               self.children[1].as_string(encoding, kwargs))

    def __repr__(self, indent=0):
        return '(%r %s %r)' % (self.children[0], self.operator,
                               self.children[1])

    def is_equivalent(self, other):
        if not is_equivalent(self, other):
            return False
        return self.operator == other.operator


class Function(HSMixin, Node):
    """Class used to deal with aggregat functions (sum, min, max, count, avg)
    and latter upper(), lower() and other RQL transformations functions
    """
    
    TYPE = 'function'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_function(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_function(self, *args, **kwargs)

    def __init__(self, name):
        Node.__init__(self)
        self.name = name.strip().upper().encode()

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.name,)

    def get_type(self):
        """return the type of object returned by this function if known"""
        try:
            return F_TYPES[self.name]
        except KeyError:
            # FIXME: e_type defined by the sql generator
            return self.children[0].e_type
        
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '%s(%s)' % (self.name, ', '.join([c.as_string(encoding, kwargs)
                                                 for c in self.children]))

    def __repr__(self, indent=0):
        return '%s%s(%s)' % (' '*indent, self.name,
                             ', '.join([repr(c) for c in self.children]))

    def is_equivalent(self, other):
        if not is_equivalent(self, other):
            return False
        return self.name == other.name



class Constant(HSMixin,Node):
    """see String, Int, TRUE, FALSE, TODAY, NULL
    """
    TYPE = 'constant'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_constant(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_constant(self, *args, **kwargs)
    
    def __init__(self, value, c_type, _uid=False, _uidtype=None):
        assert c_type in (None, 'Date', 'Datetime', 'Boolean', 'Float', 'Int',
                          'String', 'Substitute', 'etype'), "Error got c_type="+repr(c_type)
        Node.__init__(self)
        self.value = value
        self.type = c_type
        # updated by the annotator/analyzer if necessary
        self.uid = _uid
        self.uidtype = _uidtype
        
    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.value, self.type, self.uid, self.uidtype)

    def is_variable(self):
        """check if this node contains a reference to one ore more variables"""
        return 0

    def eval(self, kwargs):
        if self.type == 'Substitute':
            return kwargs[self.value]
        return self.value
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string (an unicode string is
        returned if encoding is None)
        """
        if self.type is None or self.type == 'Date':
            return self.value
        if self.type == 'etype':
            return self.value.encode()
        if self.type == 'Boolean':
            return self.value
        if self.type == 'Substitute':
            if kwargs is not None:
                value = kwargs.get(self.value, '???')
                if isinstance(value, unicode):
                    value = quote(value.encode(encoding))
                elif not isinstance(value, str):
                    return repr(value)
                return value
        if isinstance(self.value, unicode):
            if encoding is not None:
                return quote(self.value.encode(encoding))
            return uquote(self.value)
        return repr(self.value)
        
    def __repr__(self, indent=0):
        return '%s%s' % (' '*indent, self.as_string())

    def is_equivalent(self, other):
        if not is_equivalent(self, other):
            return False
        return self.type == other.type and self.value == other.value


class VariableRef(HSMixin, Node):
    """a reference to a variable in the syntax tree
    """
    TYPE = 'variableref'

    __slots__ = ('variable', 'name')
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_variableref(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_variableref(self, *args, **kwargs)

    def __init__(self, variable, noautoref=None):
        Node.__init__(self)
        self.variable = variable
        self.name = variable.name#.encode()
        if noautoref is None:
            self.register_reference()
    
    def __repr__(self, indent=0):
        return '%sVarRef(%#X) to %r' % (' '*indent, id(self), self.variable)

    def __cmp__(self, other):
        return not(self.is_equivalent(other))

    def is_equivalent(self, other):
        return self.TYPE == other.TYPE and self.name == other.name

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (stmt.get_variable(self.name),)
        
    def register_reference(self):
        self.variable.register_reference(self)

    def unregister_reference(self):
        self.variable.unregister_reference(self)

    def is_variable(self):
        """check if this node contains a reference to one ore more variables"""
        return 1

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return self.name
    
# group and sort nodes ########################################################

class Group(ListNode): 
    """a group (GROUPBY) node
    """
    TYPE = 'group'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_group(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_group(self, *args, **kwargs)
    
    def as_string(self, encoding=None, kwargs=None):
        return 'GROUPBY %s' % ', '.join([child.as_string(encoding, kwargs)
                                         for child in self.children])

    def __repr__(self):
        return 'GROUPBY %s' % ', '.join([repr(child) for child in self.children])
    
class Sort(ListNode):
    """a sort (ORDERBY) node
    """
    TYPE = 'sort'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sort(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sort(self, *args, **kwargs)
    
    def as_string(self, encoding=None, kwargs=None):
        return 'ORDERBY %s' % ', '.join([child.as_string(encoding, kwargs)
                                         for child in self.children])
    

class SortTerm(HSMixin, Node):
    """a sort term bind a variable to the boolean <asc>
    if <asc> ascendant sort
    else descendant sort
    """
    TYPE = 'sortterm'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sortterm(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sortterm(self, *args, **kwargs)

    def __init__(self, variable, asc=1, copy=None):
        Node.__init__(self)
        self.asc = asc
        self.var = variable
        if copy is None:
            self.append(variable)

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.var.copy(stmt), self.asc)
    
    def __repr__(self, indent=0):
        if self.asc:
            return '%r' % self.var
        return '%r DESC' % self.var

    def as_string(self, encoding=None, kwargs=None):
        if self.asc:
            return '%s' % self.var
        return '%s DESC' % self.var
    
    def __str__(self):
        return self.as_string()

    def is_equivalent(self, other):
        if not is_equivalent(self, other):
            return False
        return self.asc == other.asc



###############################################################################
    
class Variable(object):
    """
    a variable definition, should not be directly added to the syntax tree (use
    VariableRef instead)
    
    collects information about a variable use in a syntax tree
    """
    TYPE = 'variable'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_variable(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_variable(self, *args, **kwargs)
        
    def __init__(self, name):
        self.name = name.strip().encode()
        # reference to the selection
        self.root = None
        # used to collect some gloabl information about the syntax tree
        self.stinfo = {
            # link to VariableReference objects in the syntax tree
            'references': set(),
            # relations where this variable is used on the lhs/rhs
            'relations': set(),
            'lhsrelations': set(),
            'rhsrelations': set(),
            # final relations where this variable is used on the lhs
            'finalrels': set(),
            # type relations (e.g. "is") where this variable is used on the lhs
            'typerels': set(),
            # uid relations (e.g. "eid") where this variable is used on the lhs
            'uidrels': set(),
            # is this variable used in group and/or sort ?
            'group': None,
            'sort': None,
            # selection indexes if any
            'selected': set(),
            # if this variable is an attribute variable (ie final entity),
            # link to the attribute owner variable
            'attrvar': None,
            # constant node linked to an uid variable if any
            'constnode': None,
            }

    def register_reference(self, varref):
        """add a reference to this variable"""
        assert not [v for v in self.stinfo['references'] if v is varref]
        self.stinfo['references'].add(varref)
        
    def unregister_reference(self, varref):
        """remove a reference to this variable"""
        self.stinfo['references'].remove(varref)

    def references(self):
        """return all references on this variable"""
        return tuple(self.stinfo['references'])

    def valuable_references(self):
        """return the number of "valuable" references :
        references is in selection or in a non type (is) relations
        """
        stinfo = self.stinfo
        return len(stinfo['selected']) + len(stinfo['relations'])
    
##     def linked_variable(self):
##         """return the first relation where this variable
##         appears on the rhs
##         """
##         return self.stinfo['attrvar']

    def relation_names(self):
        """return an iterator on relations (as string) where this variable
        appears.
        """
        for reference in self.stinfo['references']:
            rel = reference.relation()
            if rel is not None:
                yield rel.r_type
                
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return self.name
    
    def __repr__(self, indent=0):
        return '%s%s(%#X)' % (' '*indent, self.name, id(self))

    def __str__(self):
        return self.name
