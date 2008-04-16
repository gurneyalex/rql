"""This module defines all the nodes we can find in a RQL Syntax tree, except
root nodes, defined in the `stmts` module.


:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from itertools import chain

try:
    from mx.DateTime import DateTimeType, today, now
except:
    from datetime import datetime as DateTimeType, date, datetime
    from time import localtime
    def now():
        return datetime(*localtime()[:6])
    def today():
        return date(*localtime()[:3])
    
KEYWORD_MAP = {'NOW' : now,
               'TODAY': today}

from rql import CoercionError
from rql.base import Node, BinaryNode, LeafNode
from rql.utils import function_description, quote, uquote

CONSTANT_TYPES = frozenset((None, 'Date', 'Datetime', 'Boolean', 'Float', 'Int',
                            'String', 'Substitute', 'etype'))

def etype_from_pyobj(value):
    # try to guess type from value
    if isinstance(value, bool):
        return 'Boolean'
    if isinstance(value, (int, long)):
        return 'Int'
    if isinstance(value, DateTimeType):
        return 'Datetime'
    elif isinstance(value, float):
        return 'Float'
    # XXX Bytes
    return 'String'

def variable_ref(var):
    """get a VariableRef"""
    if isinstance(var, Variable):
        return VariableRef(var, noautoref=1)
    assert isinstance(var, VariableRef)
    return var    


class HSMixin(object):
    """mixin class for classes which may be the lhs or rhs of an expression"""
    __slots__ = ()
    
    def relation(self):
        """return the parent relation where self occurs or None"""
        try:
            return self.parent.relation()
        except AttributeError:
            return None
        
    def get_description(self):
        return self.get_type()


# rql st edition utilities ####################################################

def make_relation(var, rel, rhsargs, rhsclass, operator='='):
    """build an relation equivalent to '<var> rel = <cst>'"""
    cmpop = Comparison(operator)
    cmpop.append(rhsclass(*rhsargs))
    relation = Relation(rel)
    if hasattr(var, 'variable'):
        var = var.variable
    relation.append(VariableRef(var))
    relation.append(cmpop)
    return relation


class EditableMixIn(object):
    """mixin class to add edition functionalities to some nodes, eg root nodes
    (statement) and Exists nodes
    """ 
    __slots__ = ()
   
    @property
    def undo_manager(self):
        return self.root.undo_manager

    @property
    def should_register_op(self):
        root = self.root
        # root is None during parsing
        return root is not None and root.memorizing and not root.undoing

    def remove_node(self, node):
        """remove the given node from the tree

        USE THIS METHOD INSTEAD OF .remove to get correct variable references
        handling
        """
        # unregister variable references in the removed subtree
        for varref in node.iget_nodes(VariableRef):
            varref.unregister_reference()
            #if not varref.variable.references():
            #    del node.root().defined_vars[varref.name]
        if self.should_register_op:
            from rql.undo import RemoveNodeOperation
            self.undo_manager.add_operation(RemoveNodeOperation(node))
        node.parent.remove(node)
    
    def add_restriction(self, relation):
        """add a restriction relation"""
        r = self.get_restriction()
        if r is not None:
            newnode = AND(r, relation)
            self.replace(r, newnode)
            if self.should_register_op:
                from rql.undo import ReplaceNodeOperation
                self.undo_manager.add_operation(ReplaceNodeOperation(r, newnode))
        else:
            self.insert(0, relation)
            if self.should_register_op:
                from rql.undo import AddNodeOperation
                self.undo_manager.add_operation(AddNodeOperation(relation))
        #assert check_relations(self)
        return relation
    
    def add_constant_restriction(self, var, rtype, value, ctype,
                                 operator='='):
        """builds a restriction node to express a constant restriction:

        variable rtype = value
        """
        if ctype is None:
            ctype = etype_from_pyobj(value)
        return self.add_restriction(make_relation(var, rtype, (value, ctype),
                                                  Constant, operator))
        
    def add_relation(self, lhsvar, rtype, rhsvar): 
        """builds a restriction node to express '<var> eid <eid>'"""
        return self.add_restriction(make_relation(lhsvar, rtype, (rhsvar,),
                                                  VariableRef))

    def add_eid_restriction(self, var, eid): 
        """builds a restriction node to express '<var> eid <eid>'"""
        return self.add_restriction(make_relation(var, 'eid', (eid, 'Int'), Constant))
    
    def add_type_restriction(self, var, etype):
        """builds a restriction node to express : variable is etype"""
        if isinstance(etype, (set, tuple, list)):
            if len(etype) > 1:
                rel = make_relation(var, 'is', ('IN',), Function, operator='=')
                infunc = rel.children[1].children[0]
                for atype in sorted(etype):
                    infunc.append(Constant(atype, 'etype'))
                return self.add_restriction(rel)
            etype = iter(etype).next() # may be a set
        return self.add_constant_restriction(var, 'is', etype, 'etype')
    

# base RQL nodes ##############################################################

class AND(BinaryNode):
    """a logical AND node (binary)"""
    __slots__ = ()
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_and(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_and(self, *args, **kwargs)
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '%s, %s' % (self.children[0].as_string(encoding, kwargs),
                           self.children[1].as_string(encoding, kwargs))
    def __repr__(self):
        return '%s AND %s' % (repr(self.children[0]), repr(self.children[1]))
    
    def ored_rel(self, _fromnode=None):
        return self.parent.ored_rel(_fromnode or self)
    def neged_rel(self, _fromnode=None):
        return self.parent.neged_rel(_fromnode or self)

    
class OR(BinaryNode):
    """a logical OR node (binary)"""
    __slots__ = ()
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_or(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_or(self, *args, **kwargs)
    
    def as_string(self, encoding=None, kwargs=None):
        return '(%s) OR (%s)' % (self.children[0].as_string(encoding, kwargs),
                                 self.children[1].as_string(encoding, kwargs))
    
    def __repr__(self):
        return '%s OR %s' % (repr(self.children[0]), repr(self.children[1]))
    
    def ored_rel(self, _fromnode=None):
        return self
    def neged_rel(self, _fromnode=None):
        return self.parent.neged_rel(_fromnode or self)


class Not(Node):
    """a logical NOT node (unary)"""
    __slots__ = ()
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_not(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_not(self, *args, **kwargs)
    
    def as_string(self, encoding=None, kwargs=None):
        if isinstance(self.children[0], (Exists, Relation)):
            return 'NOT %s' % self.children[0].as_string(encoding, kwargs)
        return 'NOT (%s)' % self.children[0].as_string(encoding, kwargs)
    
    __repr__ = as_string
    
    def ored_rel(self, _fromnode=None):
        return self.parent.ored_rel(_fromnode or self)
    def neged_rel(self, _fromnode=None):
        return self


class Exists(EditableMixIn, Node):
    """EXISTS sub query"""
    __slots__ = ()

    def __init__(self, restriction=None):
        Node.__init__(self)
        if restriction is not None:
            self.append(restriction)

    def is_equivalent(self, other):
        raise NotImplementedError
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_exists(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_exists(self, *args, **kwargs)
                
    def as_string(self, encoding=None, kwargs=None):
        content = self.children and self.children[0].as_string(encoding, kwargs)
        return 'EXISTS(%s)' % content

    def __repr__(self):
        content = self.children and repr(self.children[0])
        return 'EXISTS(%s)' % content

    def get_restriction(self):
        return self.children[0]

    @property
    def scope(self):
        return self
    
    def ored_rel(self, _fromnode=None):
        if _fromnode: # stop here
            return False
        return self.parent.ored_rel(_fromnode or self)
    def neged_rel(self, _fromnode=None):
        if _fromnode: # stop here
            return False
        return self.parent.neged_rel(_fromnode or self)

    
class Relation(Node):
    """a RQL relation"""
    __slots__ = ('r_type', 'optional',
                 '_q_sqltable', '_q_needcast') # XXX ginco specific
    
    def __init__(self, r_type, optional=None):
        Node.__init__(self)
        self.r_type = r_type.encode()
        self.optional = None
        self.set_optional(optional)
    
    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return self.r_type, self.optional
        
    def is_equivalent(self, other):
        if not Node.is_equivalent(self, other):
            return False
        if self.r_type != other.r_type:
            return False
        return True
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_relation( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_relation( self, *args, **kwargs )
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        try:
            lhs = self.children[0].as_string(encoding, kwargs)
            if self.optional in ('left', 'both'):
                lhs += '?'
            rhs = self.children[1].as_string(encoding, kwargs)
            if self.optional in ('right', 'both'):
                rhs += '?'
        except IndexError:
            return repr(self) # not fully built relation
        return '%s %s %s' % (lhs, self.r_type, rhs)

    def __repr__(self):
        if self.optional:
            rtype = '%s[%s]' % (self.r_type, self.optional)
        else:
            rtype = self.r_type
        try:
            return 'Relation(%r %s %r)' % (self.children[0], rtype,
                                           self.children[1])
        except IndexError:
            return 'Relation(%s)' % self.r_type
    
    def set_optional(self, optional):
        assert optional in (None, 'left', 'right')
        if optional is not None:
            if self.optional and self.optional != optional:
                self.optional = 'both'
            else:
                self.optional = optional
            
    def relation(self):
        """return the parent relation where self occurs or None"""
        return self
    
    def ored_rel(self, _fromnode=None):
        print 'ORED', repr(self)
        print 'PARENT',self.parent
        return self.parent.ored_rel(_fromnode or self)
    def neged_rel(self, _fromnode=None):
        return self.parent.neged_rel(_fromnode or self)

    def is_types_restriction(self):
        if self.r_type != 'is':
            return False
        rhs = self.children[1]
        if isinstance(rhs, Comparison):
            rhs = rhs.children[0]
        # else: relation used in SET OR DELETE selection
        return ((isinstance(rhs, Constant) and rhs.type == 'etype')
                or (isinstance(rhs, Function) and rhs.name == 'IN'))

    def operator(self):
        """return the operator of the relation <, <=, =, >=, > and LIKE

        (relations used in SET, INSERT and DELETE definitions don't have
         an operator as rhs)
        """
        rhs = self.children[1]
        if isinstance(rhs, Comparison):
            return rhs.operator
        return '='
       
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

    def change_optional(self, value):
        root = self.root
        if root.should_register_op and value != self.optional:
            from rql.undo import SetOptionalOperation
            root.undo_manager.add_operation(SetOptionalOperation(self, self.optional))
        self.optional= value

    
class Comparison(HSMixin, Node):
    """handle comparisons:

     <, <=, =, >=, > LIKE and ILIKE operators have a unique children.    
    """
    __slots__ = ('operator',)
    
    def __init__(self, operator, value=None):
        Node.__init__(self)
        if operator == '~=':
            operator = 'ILIKE'
        elif operator == '=' and isinstance(value, Constant) and \
                 value.type is None:
            operator = 'IS'            
        assert operator in ('<', '<=', '=', '>=', '>', 'ILIKE', 'LIKE', 'IS'), operator
        self.operator = operator.encode()
        if value is not None:
            self.append(value)

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.operator,)

    def is_equivalent(self, other):
        if not Node.is_equivalent(self, other):
            return False
        return self.operator == other.operator
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_comparison( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_comparison( self, *args, **kwargs )
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        if len(self.children) == 0:
            return self.operator
        if len(self.children) == 2:
            return '%s %s %s' % (self.children[0].as_string(encoding, kwargs),
                                 self.operator.encode(),
                                 self.children[1].as_string(encoding, kwargs))
        if self.operator in ('=', 'IS'):
            return self.children[0].as_string(encoding, kwargs)
        return '%s %s' % (self.operator.encode(),
                          self.children[0].as_string(encoding, kwargs))

    def __repr__(self):
        return '%s %s' % (self.operator, ', '.join(repr(c) for c in self.children))
    

class MathExpression(HSMixin, BinaryNode):
    """+, -, *, /"""
    __slots__ = ('operator',)

    def __init__(self, operator, lhs=None, rhs=None):
        BinaryNode.__init__(self, lhs, rhs)
        self.operator = operator.encode()

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.operator,)

    def is_equivalent(self, other):
        if not Node.is_equivalent(self, other):
            return False
        return self.operator == other.operator

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_mathexpression(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_mathexpression(self, *args, **kwargs)
        
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '(%s %s %s)' % (self.children[0].as_string(encoding, kwargs),
                               self.operator.encode(),
                               self.children[1].as_string(encoding, kwargs))

    def __repr__(self):
        return '(%r %s %r)' % (self.children[0], self.operator,
                               self.children[1])
    
    def get_type(self, solution=None, kwargs=None):
        """return the type of object returned by this function if known

        solution is an optional variable/etype mapping
        """
        lhstype = self.children[0].get_type(solution, kwargs)
        rhstype = self.children[1].get_type(solution, kwargs)
        key = (self.operator, lhstype, rhstype)
        try:
            return {('-', 'Date', 'Datetime'):     'Interval',
                    ('-', 'Datetime', 'Datetime'): 'Interval',
                    ('-', 'Date', 'Date'):         'Interval',
                    ('-', 'Date', 'Time'):     'Datetime',
                    ('+', 'Date', 'Time'):     'Datetime',
                    ('-', 'Datetime', 'Time'): 'Datetime',
                    ('+', 'Datetime', 'Time'): 'Datetime',
                    }[key]
        except KeyError:
            if lhstype == rhstype:
                return rhstype
            if sorted((lhstype, rhstype)) == ['Float', 'Int']:
                return 'Float'
            raise CoercionError(key)
        
    def get_description(self):
        """if there is a variable in the math expr used as rhs of a relation,
        return the name of this relation, else return the type of the math
        expression
        """
        schema = self.root.schema
        for vref in self.iget_nodes(VariableRef):
            rtype = vref.get_description()
            if schema.has_relation(rtype):
                return rtype
        return self.get_type()

    
class Function(HSMixin, Node):
    """Class used to deal with aggregat functions (sum, min, max, count, avg)
    and latter upper(), lower() and other RQL transformations functions
    """
    __slots__ = ('name',)

    def __init__(self, name):
        Node.__init__(self)
        self.name = name.strip().upper().encode()

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.name,)

    def is_equivalent(self, other):
        if not Node.is_equivalent(self, other):
            return False
        return self.name == other.name

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_function(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_function(self, *args, **kwargs)
        
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '%s(%s)' % (self.name, ', '.join(c.as_string(encoding, kwargs)
                                                for c in self.children))

    def __repr__(self):
        return '%s(%s)' % (self.name, ', '.join(repr(c) for c in self.children))

    def get_type(self, solution=None, kwargs=None):
        """return the type of object returned by this function if known

        solution is an optional variable/etype mapping
        """
        rtype = self.descr().rtype
        if rtype is None:
            # XXX support one variable ref child
            try:
                rtype = solution and solution.get(self.children[0].name)
            except AttributeError:
                pass
        return rtype or 'Any'

    def get_description(self):
        return self.descr().st_description(self)
        
    def descr(self):
        """return the type of object returned by this function if known"""
        return function_description(self.name)


class ColumnAlias(object):
    __slots__ = ('name', 'colnum', 'query',
                 '_q_sql') # XXX ginco specific
    def __init__(self, alias, colnum, query=None):
        self.name = alias.encode()
        self.colnum = int(colnum)
        self.query = query
        
    def register_reference(self, vref):
        pass
    def init_copy(self, old):
        pass
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_columnalias(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_columnalias(self, *args, **kwargs)
    
#     def as_string(self, encoding=None, kwargs=None):
#         return self.alias
        
        
class Constant(HSMixin, LeafNode):
    """String, Int, TRUE, FALSE, TODAY, NULL..."""
    __slots__ = ('value', 'type', 'uid', 'uidtype')
    
    def __init__(self, value, c_type, _uid=False, _uidtype=None):
        assert c_type in CONSTANT_TYPES, "Error got c_type="+repr(c_type)
        LeafNode.__init__(self) # don't care about Node attributes
        self.value = value
        self.type = c_type
        # updated by the annotator/analyzer if necessary
        self.uid = _uid
        self.uidtype = _uidtype
        
    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.value, self.type, self.uid, self.uidtype)

    def is_equivalent(self, other):
        if not LeafNode.is_equivalent(self, other):
            return False
        return self.type == other.type and self.value == other.value
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_constant(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_constant(self, *args, **kwargs)
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string (an unicode string is
        returned if encoding is None)
        """
        if self.type is None:
            return 'NULL'
        if self.type in ('etype', 'Date', 'Datetime', 'Int', 'Float'):
            return str(self.value)
        if self.type == 'Boolean':
            return self.value and 'TRUE' or 'FALSE'
        if self.type == 'Substitute':
            # XXX could get some type information from self.root().schema()
            #     and linked relation
            if kwargs is not None:
                value = kwargs.get(self.value, '???')
                if isinstance(value, unicode):
                    if encoding:
                        value = quote(value.encode(encoding))
                    else:
                        value = uquote(value)
                elif isinstance(value, str):
                    value = quote(value)
                else:
                    value = repr(value)
                return value
            return '%%(%s)s' % self.value
        if isinstance(self.value, unicode):
            if encoding is not None:
                return quote(self.value.encode(encoding))
            return uquote(self.value)
        return repr(self.value)
        
    def __repr__(self):
        return self.as_string()

    def eval(self, kwargs):
        if self.type == 'Substitute':
            return kwargs[self.value]
        if self.type in ('Date', 'Datetime'): # TODAY, NOW
            return KEYWORD_MAP[self.value]()
        return self.value

    def get_type(self, solution=None, kwargs=None):
        if self.uid:
            return self.uidtype
        if self.type == 'Substitute':
            if kwargs is not None:
                return etype_from_pyobj(self.eval(kwargs))
            return 'String'
        return self.type


class VariableRef(HSMixin, LeafNode):
    """a reference to a variable in the syntax tree"""
    __slots__ = ('variable', 'name')

    def __init__(self, variable, noautoref=None):
        LeafNode.__init__(self) # don't care about Node attributes
        self.variable = variable
        self.name = variable.name
        if noautoref is None:
            self.register_reference()

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        newvar = stmt.get_variable(self.name)
        newvar.init_copy(self.variable)
        return (newvar,)

    def is_equivalent(self, other):
        if not LeafNode.is_equivalent(self, other):
            return False
        return self.name == other.name
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_variableref(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_variableref(self, *args, **kwargs)

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return self.name
    
    def __repr__(self):
        return 'VarRef(%#X) to %r' % (id(self), self.variable)

    def __cmp__(self, other):
        return not self.is_equivalent(other)
        
    def register_reference(self):
        self.variable.register_reference(self)

    def unregister_reference(self):
        self.variable.unregister_reference(self)

    def get_type(self, solution=None, kwargs=None):
        return self.variable.get_type(solution, kwargs)

    def get_description(self):
        return self.variable.get_description()

class KWNode(Node):
    __slots__ = ()    
    def as_string(self, encoding=None, kwargs=None):
        return '%s %s' % (self.keyword,
                          ', '.join(child.as_string(encoding, kwargs)
                                    for child in self.children))

    def __repr__(self):
        return '%s %s' % (self.keyword,
                          ', '.join(repr(child) for child in self.children))
        
class Group(KWNode): 
    """a group (GROUPBY) node"""
    __slots__ = ()
    keyword = 'GROUPBY'
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_group(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_group(self, *args, **kwargs)

    
class Having(KWNode): 
    """a having (HAVING) node"""
    __slots__ = ()
    keyword = 'HAVING'
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_having(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_having(self, *args, **kwargs)

    
class Sort(KWNode):
    """a sort (ORDERBY) node"""
    __slots__ = ()
    keyword = 'ORDERBY'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sort(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sort(self, *args, **kwargs)
    

class SortTerm(Node):
    """a sort term bind a variable to the boolean <asc>
    if <asc> ascendant sort
    else descendant sort
    """
    __slots__ = ('asc',)

    def __init__(self, variable, asc=1, copy=None):
        Node.__init__(self)
        self.asc = asc
        if copy is None:
            self.append(variable)
    
    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (None, self.asc, True)

    def is_equivalent(self, other):
        if not Node.is_equivalent(self, other):
            return False
        return self.asc == other.asc

    def as_string(self, encoding=None, kwargs=None):
        if self.asc:
            return '%s' % self.term
        return '%s DESC' % self.term
    
    def __repr__(self):
        if self.asc:
            return '%r ASC' % self.term
        return '%r DESC' % self.term
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sortterm(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sortterm(self, *args, **kwargs)

    @property
    def term(self): 
        return self.children[0]



###############################################################################
    
class Variable(object):
    """
    a variable definition, should not be directly added to the syntax tree (use
    VariableRef instead)
    
    collects information about a variable use in a syntax tree
    """
    __slots__ = ('name', 'stmt', 'stinfo',
                 '_q_invariant', '_q_sql', '_q_sqltable') # XXX ginco specific
        
    def __init__(self, name):
        self.name = name.strip().encode()
        # reference to the selection
        self.stmt = None
        # used to collect some global information about the syntax tree
        # most of them will be filled by the annotator
        self.stinfo = {
            # main scope for this variable
            'scope': None,
            # link to VariableReference objects in the syntax tree
            # it must be a list to keep order
            'references': [],
            # relations where this variable is used on the lhs/rhs
            'relations': set(),
            'rhsrelations': set(),
            'optrelations': set(),
            # empty if this variable may be simplified (eg not used in optional
            # relations and no final relations where this variable is used on
            # the lhs)
            'blocsimplification': set(),
            # type relations (e.g. "is") where this variable is used on the lhs
            'typerels': set(),
            # uid relations (e.g. "eid") where this variable is used on the lhs
            'uidrels': set(),
            # selection indexes if any
            'selected': set(),
            # if this variable is an attribute variable (ie final entity),
            # link to the (prefered) attribute owner variable
            'attrvar': None,
            # set of couple (lhs variable name, relation name) where this
            # attribute variable is used
            'attrvars': set(),
            # constant node linked to an uid variable if any
            'constnode': None,
            # possible types for this variable according to constraints in the tree
            'possibletypes': set()
            }
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return self.name
    
    def __repr__(self):
        return '%s(%#X)' % (self.name, id(self))
    
    def accept(self, visitor, *args, **kwargs):
        """though variable are not actually tree nodes, they may be visited in
        some cases
        """
        return visitor.visit_variable(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        """though variable are not actually tree nodes, they may be visited in
        some cases
        """
        return visitor.leave_variable(self, *args, **kwargs)
    
    def set_scope(self, scopenode):
        if scopenode is self.stmt or self.stinfo['scope'] is None:
            self.stinfo['scope'] = scopenode
    def get_scope(self):
        return self.stinfo['scope']
    scope = property(get_scope, set_scope)

    def init_copy(self, old):
        # should copy variable's possibletypes on copy
        if not self.stinfo['possibletypes']:
            self.stinfo['possibletypes'].update(old.stinfo['possibletypes'])
        
    def register_reference(self, varref):
        """add a reference to this variable"""
        assert not [v for v in self.stinfo['references'] if v is varref]
        self.stinfo['references'].append(varref)
        
    def unregister_reference(self, varref):
        """remove a reference to this variable"""
        for i, _varref in enumerate(self.stinfo['references']):
            if varref is _varref:
                del self.stinfo['references'][i]
                break

    def references(self):
        """return all references on this variable"""
        return tuple(self.stinfo['references'])
    
    def valuable_references(self):
        """return the number of "valuable" references :
        references is in selection or in a non type (is) relations
        """
        stinfo = self.stinfo
        return len(stinfo['selected']) + len(stinfo['relations'])

    def selected_index(self):
        """return the index of this variable in the selection if it's selected,
        else None
        """
        for i, term in enumerate(self.stmt.selected_terms()):
            for node in term.iget_nodes(VariableRef):
                if node.variable is self:
                    return i

    @property
    def schema(self):
        return self.stmt.root.schema
    
    def get_type(self, solution=None, kwargs=None):
        """return entity type of this object, 'Any' if not found"""
        if solution:
            return solution[self.name]
        for rel in self.stinfo['typerels']:
            return str(rel.children[1].children[0].value)
        schema = self.schema
        if schema is not None:
            for rel in self.stinfo['rhsrelations']:
                try:
                    lhstype = rel.children[0].get_type(solution, kwargs)
                    return schema.eschema(lhstype).destination(rel.r_type)
                except: # CoertionError, AssertionError :(
                    pass
        return 'Any'
    
    def get_description(self):
        """return :
        * the name of a relation where this variable is used as lhs,
        * the entity type of this object if specified by a 'is' relation,
        * 'Any' if nothing nicer has been found...

        give priority to relation name
        """
        etype = 'Any'
        result = None
        schema = self.schema
        for rel in chain(self.stinfo['typerels'], self.stinfo['relations']):
            if rel.r_type == 'is':
                if self.name == rel.children[0].name:
                    etype = str(rel.children[1].children[0].value)
                else:
                    etype = 'Eetype' # XXX ginco specific
                continue
            if schema is not None:
                rschema = schema.rschema(rel.r_type)
                if rschema.is_final():
                    if self.name == rel.children[0].name:
                        continue # ignore
                    result = rel.r_type
                    break
            result = rel.r_type
            if self.name != rel.children[0].name:
                # priority to relation where variable is on the rhs
                break
        return result or etype
    
    def main_relation(self):
        """return the relation where this variable is used in the rhs
        (useful for case where this is a final variable and we are
         interested in the entity to which it belongs)
        """
        for ref in self.references():
            rel = ref.relation()
            if rel is None:
                continue
            if rel.r_type != 'is' and self.name != rel.children[0].name:
                return rel
        return None

