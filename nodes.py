"""This module defines all the nodes we can find in a RQL Syntax tree, except
root nodes, defined in the stmts module.

:organization: Logilab
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"


from logilab.common.tree import VNode as Node, BinaryNode, ListNode, \
     post_order_list
from logilab.common.visitor import VisitedMixIn

from rql import CoercionError
from rql.utils import function_description, quote, uquote

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

# rql st edition utilities

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


# base objects ################################################################

class EditableMixIn(object):
    @property
    def undo_manager(self):
        return self.root().undo_manager

    def should_register_op(self):
        root = self.root()
        return root.memorizing and not root.undoing
    
    def add(self, relation):
        """add a restriction relation (XXX should not collide with add_restriction
        or add_relation optionaly plugged by the editextensions module
        """
        r = self.get_restriction()
        if r is not None:
            self.replace(r, AND(r, relation))
        else:
            self.insert(0, relation)
            
    def add_restriction(self, relation):
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
        
    def add_constant_restriction(self, variable, rtype, value, ctype,
                                 operator='='):
        """builds a restriction node to express a constant restriction:

        variable rtype = value
        """
        if ctype is None:
            if isinstance(value, int):
                ctype = 'Int'
                # FIXME : other cases
            else:
                ctype = 'String'
        self.add_restriction(make_relation(variable, rtype, (value, ctype),
                                           Constant, operator))
        
    def add_relation(self, lhsvar, rtype, rhsvar): 
        """builds a restriction node to express '<var> eid <eid>'"""
        self.add_restriction(make_relation(lhsvar, rtype, (rhsvar,),
                                           VariableRef))

    def add_eid_restriction(self, var, eid): 
        """builds a restriction node to express '<var> eid <eid>'"""
        self.add_restriction(make_relation(var, 'eid', (eid, 'Int'), Constant))


class HSMixin(object):
    """mixin class for classes which may be the lhs or rhs of an expression
    """    
    def relation(self):
        """return the parent relation where self occurs or None"""
        parent = self.parent
        while parent is not None and not parent.TYPE == 'relation':
            parent = parent.parent
        return parent
    
    def is_variable(self):
        """check if this node contains a reference to one ore more variables"""
        for c in post_order_list(self):
            if isinstance(c, VariableRef):
                return 1
        return 0
        
    def get_description(self):
        return self.get_type()
    
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
                return False
        except IndexError:
            return False
    return True
Node.is_equivalent = is_equivalent

def exists_root(self):
    return self.parent.exists_root()
Node.exists_root = exists_root

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
    
    def ored_rel(self):
        return self.parent.ored_rel()

    
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
        return '(%s) OR (%s)' % (self.children[0].as_string(encoding, kwargs),
                                 self.children[1].as_string(encoding, kwargs))
    def __repr__(self):
        return '%s OR %s' % (repr(self.children[0]),
                             repr(self.children[1]))
    
    def ored_rel(self):
        return True


class Exists(HSMixin, EditableMixIn, Node):
    """EXISTS sub query"""
    TYPE = 'exists'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_exists(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_exists(self, *args, **kwargs)

    def __init__(self, restriction=None, _not=0):
        Node.__init__(self)
        self._not = _not
        if restriction is not None:
            self.append(restriction)

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (None, self._not)
                
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        if self._not:
            return 'NOT EXISTS(%s)' % self.children[0].as_string(encoding, kwargs)
        return 'EXISTS(%s)' % self.children[0].as_string(encoding, kwargs)

    def __repr__(self, indent=0):
        if self._not:
            return 'NOT EXISTS(%r)' % (self.children[0])
        return 'EXISTS(%r)' % (self.children[0])

    def get_restriction(self):
        return self.children[0]
    
    def is_equivalent(self, other):
        raise NotImplementedError

    def exists_root(self):
        return self
    
    def ored_rel(self):
        return self.parent.ored_rel()

    
class Relation(Node):
    """a single RQL relation
    """
    TYPE = 'relation'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_relation( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_relation( self, *args, **kwargs )
    
    def __init__(self, r_type, _not=0, optional=None):
        Node.__init__(self)
        self.r_type = r_type.encode()
        self._not = _not
        self.optional = None
        self.set_optional(optional)

    def is_types_restriction(self):
        rhs = self.children[1]
        if isinstance(rhs, Comparison):
            rhs = rhs.children[0]
        # else: relation used in SET OR DELETE selection
        return self.r_type == 'is' and \
               ((isinstance(rhs, Constant) and rhs.type == 'etype')
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
    
    def set_optional(self, optional):
        assert optional in (None, 'left', 'right')
        if optional is not None:
            if self.optional and self.optional != optional:
                self.optional = 'both'
            else:
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
        try:
            lhs = self.children[0].as_string(encoding, kwargs)
            if self.optional in ('left', 'both'):
                lhs += '?'
            rhs = self.children[1].as_string(encoding, kwargs)
            if self.optional in ('right', 'both'):
                rhs += '?'
        except IndexError:
            return repr(self) # not fully built relation
        if self._not:
            return 'NOT %s %s %s' % (lhs, self.r_type, rhs)
        return '%s %s %s' % (lhs, self.r_type, rhs)

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
    
    def ored_rel(self):
        return self.parent.ored_rel()

    
class Comparison(HSMixin, Node):
    """handle comparisons:

     <, <=, =, >=, > LIKE and ILIKE operators have a unique children.    
    """
    TYPE = 'comparison'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_comparison( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_comparison( self, *args, **kwargs )

    def __init__(self, operator, value=None):
        Node.__init__(self)
        if operator == '~=':
            operator = 'ILIKE'
        elif operator == '=' and isinstance(value, Constant) and \
                 value.type is None:
            operator = 'IS'            
        assert operator in ('<', '<=', '=', '>=', '>', 'ILIKE', 'LIKE', 'IS'), operator
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
    
    def get_type(self, solution=None):
        """return the type of object returned by this function if known

        solution is an optional variable/etype mapping
        """
        lhstype = self.children[0].get_type(solution)
        rhstype = self.children[1].get_type(solution)
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
        schema = self.root().schema
        for vref in self.get_nodes(VariableRef):
            rtype = vref.get_description()
            if schema.has_relation(rtype):
                return rtype
        return self.get_type()
        
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

    def get_type(self, solution=None):
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
        # FIXME: e_type defined by erudi's sql generator
        return function_description(self.name)
        
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

    def get_type(self, solution=None):
        if self.uid:
            return self.uidtype
        return self.type
        
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string (an unicode string is
        returned if encoding is None)
        """
        if self.type is None or self.type in ('etype', 'Datetime', 'Date',
                                              'Boolean', 'Int', 'Float'):
            return str(self.value)
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
        return not self.is_equivalent(other)

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

    def get_type(self, solution=None):
        return self.variable.get_type(solution)

    def get_description(self):
        return self.variable.get_description()

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
    
    def exists_root(self):
        return False
    
    
class Sort(ListNode):
    """a sort (ORDERBY) node
    """
    TYPE = 'sort'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_sort(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_sort(self, *args, **kwargs)

    def selected_terms(self):
        return self
    
    def as_string(self, encoding=None, kwargs=None):
        return 'ORDERBY %s' % ', '.join([child.as_string(encoding, kwargs)
                                         for child in self.children])
    
    def exists_root(self):
        return False
    

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
        if copy is None:
            self.append(variable)
            
    @property
    def var(self): # XXX deprecated, use .term
        return self.children[0]
            
    @property
    def term(self): 
        return self.children[0]
    
    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node"""
        return (self.term.copy(stmt), self.asc)
    
    def __repr__(self, indent=0):
        if self.asc:
            return '%r ASC' % self.term
        return '%r DESC' % self.term

    def as_string(self, encoding=None, kwargs=None):
        if self.asc:
            return '%s' % self.term
        return '%s DESC' % self.term
    
    def __str__(self):
        return self.as_string()

    def is_equivalent(self, other):
        if not is_equivalent(self, other):
            return False
        return self.asc == other.asc

    def exists_root(self):
        return False



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
            'scope': None,
            # link to VariableReference objects in the syntax tree
            # it must be a list to keep order
            'references': [],
            # relations where this variable is used on the lhs/rhs
            'relations': set(),
            'lhsrelations': set(),
            'rhsrelations': set(),
            # final relations where this variable is used on the lhs
            'finalrels': set(),
            # optional relations where this variable is used
            'optrels': set(),
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
            # link to the (prefered) attribute owner variable
            'attrvar': None,
            # constant node linked to an uid variable if any
            'constnode': None,
            }
    
    
    def set_scope(self, scopenode):
        if scopenode is self.root or self.stinfo['scope'] is None:
            self.stinfo['scope'] = scopenode
    def get_scope(self):
        return self.stinfo['scope']
    scope = property(get_scope, set_scope)

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

    def selected_index(self):
        """return the index of this variable in the selection if it's selected,
        else None
        """
        for i, term in enumerate(self.root.selected_terms()):
            for node in term.get_nodes(VariableRef):
                if node.variable is self:
                    return i
    
    def get_type(self, solution=None):
        """return entity type of this object, 'Any' if not found"""
        if solution:
            return solution[self.name]
        etype = 'Any'
        schema = self.root.schema
        for ref in self.references():
            rel = ref.relation()
            if rel is None:
                continue
            if rel.r_type == 'is' and self.name == rel.children[0].name:
                etype = rel.children[1].children[0].value.encode()
                break
            if rel.r_type != 'is' and self.name != rel.children[0].name:
                if schema is not None:
                    try:
                        lhstype = rel.children[0].get_type(solution)
                        etype = schema.eschema(lhstype).destination(rel.r_type)
                        break
                    except: # CoertionError, AssertionError :(
                        pass
        return etype
    
    def get_description(self):
        """return :
        * the name of a relation where this variable is used as lhs,
        * the entity type of this object if specified by a 'is' relation,
        * 'Any' if nothing nicer has been found...

        give priority to relation name
        """
        etype = 'Any'
        result = None
        schema = self.root.schema
        for ref in self.references():
            rel = ref.relation()
            if rel is None:
                continue
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
        
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        return self.name
    
    def __repr__(self, indent=0):
        return '%s%s(%#X)' % (' '*indent, self.name, id(self))

    def __str__(self):
        return self.name


