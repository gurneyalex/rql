"""RQL syntax tree nodes.

This module defines all the nodes we can find in a RQL Syntax tree, except
root nodes, defined in the `stmts` module.

:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
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
from rql.base import BaseNode, Node, BinaryNode, LeafNode
from rql.utils import function_description, quote, uquote, build_visitor_stub

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

def variable_refs(node):
    for vref in node.iget_nodes(VariableRef):
        if isinstance(vref.variable, Variable):
            yield vref


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
        return root is not None and root.should_register_op

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
        r = self.where
        if r is not None:
            newnode = And(r, relation)
            self.set_where(newnode)
            if self.should_register_op:
                from rql.undo import ReplaceNodeOperation
                self.undo_manager.add_operation(ReplaceNodeOperation(r, newnode))
        else:
            self.set_where(relation)
            if self.should_register_op:
                from rql.undo import AddNodeOperation
                self.undo_manager.add_operation(AddNodeOperation(relation))
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
        if isinstance(etype, (set, frozenset, tuple, list, dict)):
            if len(etype) > 1:
                rel = make_relation(var, 'is', ('IN',), Function, operator='=')
                infunc = rel.children[1].children[0]
                for atype in sorted(etype):
                    infunc.append(Constant(atype, 'etype'))
                return self.add_restriction(rel)
            etype = iter(etype).next() # may be a set
        return self.add_constant_restriction(var, 'is', etype, 'etype')

# base RQL nodes ##############################################################

class SubQuery(BaseNode):
    """WITH clause"""
    __slots__ = ('aliases', 'query')
    def __init__(self, aliases=None, query=None):
        if aliases is not None:
            self.set_aliases(aliases)
        if query is not None:
            self.set_query(query)
            
    def set_aliases(self, aliases):
        self.aliases = aliases
        for node in aliases:
            node.parent = self
            
    def set_query(self, node):
        self.query = node
        node.parent = self

    def copy(self, stmt):
        return SubQuery([v.copy(stmt) for v in self.aliases], self.query.copy())
    
    @property
    def children(self):
        return self.aliases + [self.query]
    
    def as_string(self, encoding=None, kwargs=None):
        return '%s BEING (%s)' % (','.join(v.name for v in self.aliases),
                                  self.query.as_string())
    def __repr__(self):
        return '%s BEING (%s)' % (','.join(repr(v) for v in self.aliases),
                                  repr(self.query))
    
class And(BinaryNode):
    """a logical AND node (binary)"""
    __slots__ = ()
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return '%s, %s' % (self.children[0].as_string(encoding, kwargs),
                           self.children[1].as_string(encoding, kwargs))
    def __repr__(self):
        return '%s AND %s' % (repr(self.children[0]), repr(self.children[1]))
    
    def ored(self, _fromnode=None):
        return self.parent.ored(_fromnode or self)
    def neged(self, _fromnode=None):
        return self.parent.neged(_fromnode or self)

    
class Or(BinaryNode):
    """a logical OR node (binary)"""
    __slots__ = ()
    
    def as_string(self, encoding=None, kwargs=None):
        return '(%s) OR (%s)' % (self.children[0].as_string(encoding, kwargs),
                                 self.children[1].as_string(encoding, kwargs))
    
    def __repr__(self):
        return '%s OR %s' % (repr(self.children[0]), repr(self.children[1]))
    
    def ored(self, _fromnode=None):
        return self
    def neged(self, _fromnode=None):
        return self.parent.neged(_fromnode or self)


class Not(Node):
    """a logical NOT node (unary)"""
    __slots__ = ()
    
    def as_string(self, encoding=None, kwargs=None):
        if isinstance(self.children[0], (Exists, Relation)):
            return 'NOT %s' % self.children[0].as_string(encoding, kwargs)
        return 'NOT (%s)' % self.children[0].as_string(encoding, kwargs)
    
    def __repr__(self, encoding=None, kwargs=None):
        return 'NOT (%s)' % repr(self.children[0])
    
    def ored(self, _fromnode=None):
        return self.parent.ored(_fromnode or self)
    def neged(self, _fromnode=None):
        return self


class Exists(EditableMixIn, BaseNode):
    """EXISTS sub query"""
    __slots__ = ('query',)

    def __init__(self, restriction=None):
        if restriction is not None:
            self.set_where(restriction)

    def copy(self, stmt):
        new = self.query.copy(stmt)
        return Exists(new)
    
    @property
    def children(self):
        return (self.query,)
    
    def is_equivalent(self, other):
        raise NotImplementedError
                    
    def as_string(self, encoding=None, kwargs=None):
        content = self.query and self.query.as_string(encoding, kwargs)
        return 'EXISTS(%s)' % content

    def __repr__(self):
        return 'EXISTS(%s)' % repr(self.query)

    def set_where(self, node):
        self.query = node
        node.parent = self
    
    @property
    def where(self):
        return self.query
    
    def replace(self, oldnode, newnode):
        assert oldnode is self.query
        self.query = newnode
        newnode.parent = self

    @property
    def scope(self):
        return self
    
    def ored(self, _fromnode=None):
        if _fromnode is not None: # stop here
            return False
        return self.parent.ored(self)
    def neged(self, _fromnode=None, strict=False):
        if _fromnode is not None: # stop here
            return False
        if strict:
            return isinstance(self.parent, Not)
        return self.parent.neged(self)

    
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
    
    def ored(self, _fromnode=None):
        return self.parent.ored(_fromnode or self)
    def neged(self, _fromnode=None, strict=False):
        if strict:
            return isinstance(self.parent, Not)
        return self.parent.neged(_fromnode or self)

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
    """Operators plus, minus, multiply, divide."""
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
        return self.as_string('utf8')

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
        if isinstance(self.variable, ColumnAlias):
            newvar = stmt.get_variable(self.name, self.variable.colnum)
        else:
            newvar = stmt.get_variable(self.name)
        newvar.init_copy(self.variable)
        return (newvar,)

    def is_equivalent(self, other):
        if not LeafNode.is_equivalent(self, other):
            return False
        return self.name == other.name
    
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
    
    @property
    def term(self): 
        return self.children[0]



###############################################################################
    
class Referenceable(object):
    __slots__ = ('name', 'stinfo')
        
    def __init__(self, name):
        self.name = name.strip().encode()
        # used to collect some global information about the syntax tree
        self.stinfo = {
            # link to VariableReference objects in the syntax tree
            'references': set(),
            }

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return self.name
        
    def register_reference(self, vref):
        """add a reference to this variable"""
        self.stinfo['references'].add(vref)
        
    def unregister_reference(self, vref):
        """remove a reference to this variable"""
        try:
            self.stinfo['references'].remove(vref)
        except KeyError:
            # this may occur on hairy undoing
            pass

    def references(self):
        """return all references on this variable"""
        return tuple(self.stinfo['references'])

    
class ColumnAlias(Referenceable):
    __slots__ = ('colnum', 'query',
                 '_q_sql', '_q_sqltable') # XXX ginco specific
    def __init__(self, alias, colnum, query=None):
        super(ColumnAlias, self).__init__(alias)
        self.colnum = int(colnum)
        self.query = query
    
    def __repr__(self):
        return 'alias %s(%#X)' % (self.name, id(self))
    
    def get_type(self, solution=None, kwargs=None):
        """return entity type of this object, 'Any' if not found"""
        if solution:
            return solution[self.name]
        return 'Any'    

    # Variable compatibility
    def init_copy(self, old):
        pass

    
class Variable(Referenceable):
    """
    a variable definition, should not be directly added to the syntax tree (use
    VariableRef instead)
    
    collects information about a variable use in a syntax tree
    """
    __slots__ = ('stmt',
                 '_q_invariant', '_q_sql', '_q_sqltable') # XXX ginco specific
        
    def __init__(self, name):
        super(Variable, self).__init__(name)
        # reference to the selection
        self.stmt = None

    def prepare_annotation(self):
        self.stinfo.update({
            # main scope for this variable
            'scope': None,
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
            })
    
    def __repr__(self):
        return '%s(%#X)' % (self.name, id(self))
    
    def set_scope(self, scopenode):
        if scopenode is self.stmt or self.stinfo['scope'] is None:
            self.stinfo['scope'] = scopenode
    def get_scope(self):
        return self.stinfo['scope']
    scope = property(get_scope, set_scope)

    def init_copy(self, old):
        # should copy variable's possibletypes on copy
        if not self.stinfo.get('possibletypes'):
            self.stinfo['possibletypes'] = old.stinfo.get('possibletypes')
    
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
        if not self.stinfo['selected']:
            return None
        return iter(self.stinfo['selected']).next()

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
            if rel.is_types_restriction():
                try:
                    etype = str(rel.children[1].children[0].value)
                except AttributeError:
                    # "IN" Function node
                    pass
                continue
            if schema is not None:
                rschema = schema.rschema(rel.r_type)
                if rschema.is_final():
                    if self.name == rel.children[0].name:
                        continue # ignore
                    result = rel.r_type
                    break
            result = rel.r_type
            # use getattr since variable may have been rewritten
            if not self.name != getattr(rel.children[0], 'name', None):
                # priority to relation where variable is on the rhs
                break
        return result or etype
    
    def main_relation(self):
        """Return the relation where this variable is used in the rhs.

        It is useful for cases where this variable is final and we are
        looking for the entity to which it belongs.
        """
        for ref in self.references():
            rel = ref.relation()
            if rel is None:
                continue
            if rel.r_type != 'is' and self.name != rel.children[0].name:
                return rel
        return None

build_visitor_stub((SubQuery, And, Or, Not, Exists, Relation,
                    Comparison, MathExpression, Function, Constant,
                    VariableRef, SortTerm, ColumnAlias, Variable))
