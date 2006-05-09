"""Copyright (c) 2004-2006 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
 
This module defines all the nodes we can find in a RQL Syntax tree, except
root nodes, defined in the stmts module.
"""

__revision__ = "$Id: nodes.py,v 1.33 2006-05-02 12:25:39 syt Exp $"

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
        return self.as_string(None)


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

# RQL base nodes ##############################################################


class AND(BinaryNode):
    """a logical AND node (binary)
    """
    TYPE = 'and'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_and( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_and( self, *args, **kwargs )
    
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        return '%s, %s' % (self.children[0].as_string(encoding),
                           self.children[1].as_string(encoding))
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
    
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        return '%s OR %s' % (self.children[0].as_string(encoding),
                             self.children[1].as_string(encoding))
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
    
    def __init__(self, r_type, _not=0):
        Node.__init__(self)
        self.r_type = r_type.encode()
        self._not = _not

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return self.r_type, self._not
    
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        try:
            if not self._not:
                return '%s %s %s' % (self.children[0].as_string(encoding),
                                     self.r_type,
                                     self.children[1].as_string(encoding))
            return 'not %s %s %s' % (self.children[0].as_string(encoding),
                                     self.r_type,
                                     self.children[1].as_string(encoding))
        except IndexError:
            return repr(self)

    def __repr__(self, indent=0):
        try:
            if not self._not:
                return '%sRelation(%r %s %r)' % (' '*indent, self.children[0],
                                                 self.r_type, self.children[1])
            return '%sRelation(not %r %s %r)' % (' '*indent, self.children[0],
                                                 self.r_type, self.children[1])
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
    
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        if len(self.children)==0:
            return self.operator
        if self.operator in ('=', 'IS'):
            return self.children[0].as_string(encoding)
        else:
            return '%s %s' % (self.operator.encode(),
                              self.children[0].as_string(encoding))

    def __repr__(self, indent=0):
        return '%s%s %s' % (' '*indent, self.operator,
                            ', '.join([repr(c) for c in self.children]))

    

class MathExpression(HSMixin, BinaryNode):
    """+, -, *, /
    """
    TYPE = 'mathexpression'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_mathexpression( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_mathexpression( self, *args, **kwargs )

    def __init__(self, operator, lhs=None, rhs=None):
        BinaryNode.__init__(self, lhs, rhs)
        self.operator = operator

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.operator,)
                
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        return '(%s %s %s)' % (self.children[0].as_string(encoding),
                               self.operator.encode(),
                               self.children[1].as_string(encoding))

    def __repr__(self, indent=0):
        return '(%r %s %r)' % (self.children[0], self.operator,
                               self.children[1])

    def __cmp__(self, other):
        if isinstance(other, MathExpression):
            if self.operator == other.operator:
                return cmp(self.children, other.children)
        return 1


class Function(HSMixin, Node):
    """Class used to deal with aggregat functions (sum, min, max, count, avg)
    and latter upper(), lower() and other RQL transformations functions
    """
    
    TYPE = 'function'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_function( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_function( self, *args, **kwargs )

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
        
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        return '%s(%s)' % (self.name, ', '.join([c.as_string(encoding)
                                                 for c in self.children]))

    def __repr__(self, indent=0):
        return '%s%s(%s)' % (' '*indent, self.name,
                             ', '.join([repr(c) for c in self.children]))

    def __cmp__(self, other):
        if isinstance(other, Function):
            if self.name == other.name:
                return cmp(self.children, other.children)
        return 1



class Constant(HSMixin,Node):
    """see String, Int, TRUE, FALSE, TODAY, NULL
    """
    TYPE = 'constant'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_constant( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_constant( self, *args, **kwargs )
    
    def __init__(self, value, c_type):
        assert c_type in (None, 'Date', 'Datetime', 'Boolean', 'Float', 'Int',
                          'String', 'Substitute', 'etype'), "Error got c_type="+repr(c_type)
        Node.__init__(self)
        self.value = value
        self.type = c_type

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.value, self.type)

    def is_variable(self):
        """check if this node contains a reference to one ore more variables"""
        return 0
        
    def as_string(self, encoding=None):
        """return the tree as an encoded rql string (an unicode string is
        returned if encoding is None)
        """
        if self.type is None or self.type == 'Date':
            return self.value
        if self.type == 'etype':
            return self.value.encode()
        if self.type == 'Boolean':
            return self.value
        if isinstance(self.value, unicode):
            if encoding is not None:
                return quote(self.value.encode(encoding))
            return uquote(self.value)
        return repr(self.value)
        
    def __repr__(self, indent=0):
        return '%s%s' % (' '*indent, self.as_string(None))

    def __cmp__(self, other):
        if isinstance(other, Constant) and self.type == other.type:
            return cmp(self.value, other.value)
        return 1


class VariableRef(HSMixin, Node):
    """a reference to a variable in the syntax tree
    """
    TYPE = 'variableref'

    __slots__ = ('variable', 'name')
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_variableref( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_variableref( self, *args, **kwargs )

    def __init__(self, variable, noautoref=None):
        Node.__init__(self)
        self.variable = variable
        self.name = variable.name#.encode()
        if noautoref is None:
            self.register_reference()

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

    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        return self.name
    
    def __repr__(self, indent=0):
        return '%sVarRef(%#X) to %r' % (' '*indent, id(self), self.variable)

    def __cmp__(self, other):
        if isinstance(other, VariableRef):
            return cmp(self.name, other.name)
        return 1
    
    def __hash__(self):
        return self.name.__hash__()


class Variable(object):
    """
    a variable definition (should not be directly added to the syntax tree, use
    VariableRef !)
    """
    TYPE = 'variable'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_variable( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_variable( self, *args, **kwargs )
        
    def __init__(self, name):
        self.name = name.strip().encode()
        # reference to the selection
        self.root = None
        # link to VariableReference objects in the syntax tree
        self._references = []

    def register_reference(self, varref):
        """add a reference to this variable"""
        assert not [v for v in self._references if v is varref]
        self._references.append(varref)
        
    def unregister_reference(self, varref):
        """remove a reference to this variable"""
        for i in range(len(self._references)):
            if self._references[i] is varref:
                self._references.pop(i)
                break
        assert not [v for v in self._references if v is varref]

    def references(self):
        """return all references on this variable"""
        return tuple(self._references)
            
    def linked_variable(self):
        """return the lhs variable of the left most expression where this
        variable appears.
        """
        for reference in self.references():
            rel = reference.relation()
            if rel is not None:
                return rel.get_parts()[0]

    def as_string(self, encoding=None):
        """return the tree as an encoded rql string"""
        return self.name
    
    def __repr__(self, indent=0):
        return '%s%s(%#X)' % (' '*indent, self.name, id(self))

    def __str__(self):
        return self.name

    def __cmp__(self, other):
        if isinstance(other, Variable):
            return cmp(self.name, other.name)
        return 1
    
    def __hash__(self):
        return self.name.__hash__()

    
# group and sort nodes ########################################################

class Group(ListNode): 
    """a group (GROUPBY) node
    """
    TYPE = 'group'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_group( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_group( self, *args, **kwargs )

    def __cmp__(self, other):
        if isinstance(other, Group) and len(self) == len(other):
            for i in range(len(self)):
                if cmp(self[i], other[i]):
                    return 1
            return 0
        return 1

    def __repr__(self):
        return 'GROUPBY %s' % ', '.join([repr(child) for child in self.children])
    
class Sort(ListNode):
    """a sort (ORDERBY) node
    """
    TYPE = 'sort'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sort( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sort( self, *args, **kwargs )

    def __cmp__(self, other):
        if isinstance(other, Sort) and len(self) == len(other):
            for i in range(len(self)):
                if cmp(self[i], other[i]):
                    return 1
            return 0
        return 1

    def __repr__(self):
        return 'ORDERBY %s' % ', '.join([repr(child) for child in self.children])
    

class SortTerm(HSMixin, Node):
    """a sort term bind a variable to the boolean <asc>
    if <asc> ascendant sort
    else descendant sort
    """
    TYPE = 'sortterm'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sortterm( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sortterm( self, *args, **kwargs )

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

    def __str__(self):
        if self.asc:
            return '%s' % self.var
        return '%s DESC' % self.var

    def __cmp__(self, other):
        if isinstance(other, SortTerm):
            if self.asc == other.asc:
                return cmp(self.var, other.var)
        return 1
