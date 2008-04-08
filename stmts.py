"""Objects to construct a syntax tree and some utilities to manipulate it. 
This module defines only first level nodes (i.e. statements). Child nodes are
defined in the nodes module

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from logilab.common.decorators import cached

from rql import BadRQLQuery, CoercionError, nodes
from rql.base import Node
from rql.utils import rqlvar_maker

class Statement(nodes.EditableMixIn, Node):
    """base class for statement nodes"""

    # default values for optional instance attributes, set on the instance when
    # used
    solutions = None # list of possibles solutions for used variables
    undoing = False  # used to prevent from memorizing when undoing !
    memorizing = 0   # recoverable modification attributes
    schema = None    # ISchema
    _varmaker = None # variable names generator, built when necessary
    
    def __init__(self):
        Node.__init__(self)
        # dictionnary of defined variables in the original RQL syntax tree
        self.defined_vars = {}
        # syntax tree meta-information
        self.stinfo = {}
        
    def __str__(self):
        return self.as_string(None, {})

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        raise NotImplementedError()
    
    def copy(self):
        new = self.__class__()
        new.schema = self.schema
        for child in self.children:
            new.append(child.copy(new))
        return new
        
    # navigation helper methods #############################################
    
    def root(self):
        """return the root node of the tree"""
        return self
        
    def get_selected_variables(self):
        return self.selected_terms()
        
    def get_restriction(self):
        """return all the subtree with restriction clauses. That maybe a Or,
        And, or Relation instance.
        return None if there is no restriction clauses.
        """
        # XXX : le commentaire correspond pas!!!
        for c in self.children:
            if not isinstance(c, nodes.Group) and not isinstance(c, nodes.Sort):
                return c
            break
        return None
    
    def selected_terms(self):
        raise NotImplementedError

    @property
    def scope(self):
        return self
    
    def exists_root(self):
        return None
    
    def ored_rel(self, _fromnode=None):
        return False
    
    # construction helper methods #############################################

    def allocate_varname(self):
        """return an yet undefined variable name"""
        if self._varmaker is None:
            self._varmaker = rqlvar_maker(defined=self.defined_vars)
        name =  self._varmaker.next()
        while name in self.defined_vars:
            name =  self._varmaker.next()
        return name
    
    def get_etype(self, name):
        """return the type object for the given entity's type name
        
        raise BadRQLQuery on unknown type
        """
        return nodes.Constant(name, 'etype')
        
    def get_variable(self, name):
        """get a variable instance from its name
        
        the variable is created if it doesn't exist yet
        """
        try:
            return self.defined_vars[name]
        except:
            self.defined_vars[name] = var = nodes.Variable(name)
            var.root = self
            return var
        

    def set_possible_types(self, solutions, solsidx=0):
        solutions = solutions[solsidx]
        self.solutions = solutions
        defined = self.defined_vars
        for var in defined.itervalues():
            var.stinfo['possibletypes'] = set()
        for solution in solutions:
            for vname, etype in solution.iteritems():
                defined[vname].stinfo['possibletypes'].add(etype)

    # recoverable modification methods ########################################
    
    @property
    @cached
    def undo_manager(self):
        from rql.undo import SelectionManager
        return SelectionManager(self)

    def save_state(self):
        """save the current tree"""
        self.undo_manager.push_state()
        self.memorizing += 1

    def recover(self):
        """reverts the tree as it was when save_state() was last called"""
        self.memorizing -= 1
        assert self.memorizing >= 0
        self.undo_manager.recover()    

    def make_variable(self, etype=None):
        """create a new variable with an unique name for this tree"""
        var = self.get_variable(self.allocate_varname())
        if self.memorizing and not self.undoing:
            from rql.undo import MakeVarOperation
            self.undo_manager.add_operation(MakeVarOperation(var))
        return var
    
    def remove_node(self, node):
        """remove the given node from the tree

        USE THIS METHOD INSTEAD OF .remove to get correct variable references
        handling
        """
        # unregister variable references in the removed subtree
        for varref in node.iget_nodes(nodes.VariableRef):
            varref.unregister_reference()
            #if not varref.variable.references():
            #    del node.root().defined_vars[varref.name]
        if self.memorizing and not self.undoing:
            from rql.undo import RemoveNodeOperation
            self.undo_manager.add_operation(RemoveNodeOperation(node))
        node.parent.remove(node)
        #assert check_relations(self)


class Union(Statement):
    """the select node is the root of the syntax tree for selection statement
    using UNION
    """
    TYPE = 'select'

    def __init__(self):
        Statement.__init__(self)
        # limit / offset
        self.limit = None
        self.offset = 0
        # for sort variables
        self.sortterms = None

    def __repr__(self):
        s = [repr(select) for select in self.children]
        s = ['\nUNION\n'.join(s)]
        if self.sortterms is not None:
            s.append(repr(self.sortterms))
        if self.limit is not None:
            s.append('LIMIT %s' % self.limit)
        if self.offset:
            s.append('OFFSET %s' % self.offset)
        return ' '.join(s)                             
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        s = [select.as_string(encoding, kwargs) for select in self.children]
        s = [' UNION '.join(s)]
        if self.sortterms is not None:
            s.append(self.sortterms.as_string(encoding, kwargs))
        if self.limit is not None:
            s.append('LIMIT %s' % self.limit)
        if self.offset:
            s.append('OFFSET %s' % self.offset)
        return ' '.join(s)                              
            
    def copy(self):
        new = Union()
        for child in self.children:
            new.append(child.copy())
        if self.sortterms:
            new.sortterms = self.sortterms.copy(new)
            new.sortterms.parent = new
        new.limit = self.limit
        new.offset = self.offset
        return new

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_union(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_union(self, *args, **kwargs)
    
    def set_sortterms(self, node):
        self.sortterms = node
        node.parent = self

    def set_limit(self, limit):
        if limit is not None and (not isinstance(limit, (int, long)) or limit <= 0):
            raise BadRQLQuery('bad limit %s' % limit)
        if self.should_register_op and limit != self.limit:
            from rql.undo import SetLimitOperation
            self.undo_manager.add_operation(SetLimitOperation(self.limit))
        self.limit = limit

    def set_offset(self, offset):
        if offset is not None and (not isinstance(offset, (int, long)) or offset <= 0):
            raise BadRQLQuery('bad offset %s' % offset)
        if self.should_register_op and offset != self.offset:
            from rql.undo import SetOffsetOperation
            self.undo_manager.add_operation(SetOffsetOperation(self.offset))
        self.offset = offset
        
    def set_possible_types(self, solutions):
        assert len(solutions) == len(self.children)
        for i, select in enumerate(self.children):
            select.set_possible_types(solutions, i)

    def remove_node(self, node):
        if node is self.sortterms:
            for varref in node.iget_nodes(nodes.VariableRef):
                varref.unregister_reference()
            self.sortterms = None # XXX undoing
        else:
            Statement.remove_node(self, node)
            
    # access to select statements property, which in certain condition
    # should have homogeneous values (don't use this in other cases)

    @cached
    def get_groups(self):
        """return a list of grouped variables (i.e a Group object) or None if
        there is no grouped variable.
        """
        groups = self.children[0].get_groups()
        if groups is None:
            for c in self.children[1:]:
                if c.get_groups() is not None:
                    raise BadRQLQuery('inconsistent groups among subqueries')
        else:
            for c in self.children[1:]:
                if not groups.is_equivalent(c.get_groups()):
                    raise BadRQLQuery('inconsistent groups among subqueries')
        return groups

    @cached
    def selected_terms(self):
        selected = self.children[0].selected_terms()
        for c in self.children[1:]:
            cselected = c.selected_terms()
            for i, term in enumerate(selected):
                if not term.is_equivalent(cselected[i]):
                    raise BadRQLQuery('inconsistent selection among subqueries')
        return selected
        
    @property
    def selected(self):
        # consistency check done by selected_terms
        return self.children[0].selected
        
    @property
    @cached
    def distinct(self):
        distinct = self.children[0].distinct
        for c in self.children[1:]:
            if c.distinct != distinct:
                raise BadRQLQuery('inconsistent distinct among subqueries')
        return distinct


class Select(Statement):
    """the select node is the root of the syntax tree for selection statement
    without UNION
    """
    TYPE = 'select'

    def __init__(self):
        Statement.__init__(self)
        # distinct ?
        self.distinct = False
        # list of selected relations (maybe variables or functions)
        self.selected = []
        # set by the annotator
        self.has_aggregat = False
        # syntax tree meta-information
        self.stinfo['rewritten'] = {}

    def __repr__(self):
        if self.distinct:
            base = 'DISTINCT Any'
        else:
            base = 'Any'
        s = ['%s %s WHERE' % (base,
                              ','.join([repr(v) for v in self.selected]))]
        for child in self.children:
            s.append(repr(child))
        return '\n'.join(s)
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        if self.distinct:
            base = 'DISTINCT Any'
        else:
            base = 'Any'
        s = ['%s %s' % (base, ','.join(v.as_string(encoding, kwargs)
                                       for v in self.selected))]
        r = self.get_restriction()
        if r is not None:
            s.append('WHERE %s' % r.as_string(encoding, kwargs))
        groups = self.get_groups()
        if groups is not None:
            s.append(groups.as_string(encoding, kwargs))
        having = self.get_having()
        if having is not None:
            s.append(having.as_string(encoding, kwargs))
        return ' '.join(s)
                                      
    def copy(self):
        new = Statement.copy(self)
        for child in self.selected:
            new.append_selected(child.copy(new))
        new.distinct = self.distinct
        #assert check_relations(new)
        return new
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_select(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_select(self, *args, **kwargs)
        
    # construction helper methods #############################################

    def append_selected(self, term):
        if isinstance(term, nodes.Constant) and term.type == 'etype':
            raise BadRQLQuery('Entity type are not allowed in selection')
        term.parent = self
        self.selected.append(term)
            
    def replace(self, oldnode, newnode):
        # XXX no vref handling ?
        try:
            Statement.replace(self, oldnode, newnode)
        except ValueError:
            i = self.selected.index(oldnode)
            self.selected.pop(i)
            self.selected.insert(i, newnode)
            newnode.parent = self
            
    def set_statement_type(self, etype):
        """set the statement type for this selection
        this method must be called last (i.e. once selected variables has been
        added)
        """
        assert self.selected
        # Person P  ->  Any P where P is Person
        if etype != 'Any':
            for var in self.get_selected_variables():
                self.add_type_restriction(var.variable, etype)

    def get_description(self):
        """return the list of types or relations (if not found) associated to
        selected variables
        """
        descr = []
        for term in self.selected:
            try:
                descr.append(term.get_description())
            except CoercionError:
                descr.append('Any')
        return descr

    def set_distinct(self, value):
        """mark DISTINCT query"""
        if self.should_register_op and value != self.distinct:
            from rql.undo import SetDistinctOperation
            self.undo_manager.add_operation(SetDistinctOperation(self.distinct))
        self.distinct = value
        
    # quick accessors #########################################################
    
    def get_groups(self):
        """return a Group node or None if there is no grouped variable"""
        for c in self.children:
            if isinstance(c, nodes.Group):
                return c
        return None
    
    def get_having(self):
        """return a Having or None if there is no HAVING clause"""
        for c in self.children:
            if isinstance(c, nodes.Having):
                return c
        return None
    
    def get_selected_variables(self):
        """returns all selected variables, including those used in aggregate
        functions
        """
        for term in self.selected_terms():
            for node in term.iget_nodes(nodes.VariableRef):
                yield node

    def selected_terms(self):
        """returns selected terms"""
        return self.selected[:]

    
class Delete(Statement):
    """the Delete node is the root of the syntax tree for deletion statement
    """
    TYPE = 'delete'
    
    def __init__(self):
        Statement.__init__(self)
        self.main_variables = []
        self.main_relations = []
    
    def __repr__(self):
        result = ['DELETE']
        if self.main_variables:
            result.append(', '.join(['%r %r' %(etype, var)
                                     for etype, var in self.main_variables]))
        if self.main_relations:
            if self.main_variables:
                result.append(',')
            result.append(', '.join([repr(rel) for rel in self.main_relations]))
        r = self.get_restriction()
        if r is not None:
            result.append('WHERE %r' % r)
        return ' '.join(result)

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['DELETE']
        if self.main_variables:
            result.append(', '.join(['%s %s' %(etype, var)
                                     for etype, var in self.main_variables]))
        if self.main_relations:
            if self.main_variables:
                result.append(',')
            result.append(', '.join([rel.as_string(encoding, kwargs)
                                     for rel in self.main_relations]))                
        r = self.get_restriction()
        if r is not None:
            result.append('WHERE %s' % r.as_string(encoding, kwargs))
        return ' '.join(result)

    def copy(self):
        new = Statement.copy(self)
        for etype, var in self.main_variables:
            vref = nodes.VariableRef(new.get_variable(var.name))
            new.add_main_variable(etype, vref)
        for child in self.main_relations:
            new.add_main_relation(child.copy(new))
        #assert check_relations(new)
        return new

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_delete( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_delete( self, *args, **kwargs )
    
    def get_selected_variables(self):
        return self.selected_terms()
    
    def selected_terms(self):
        return [vref for et, vref in self.main_variables]
    
    def add_main_variable(self, etype, vref):
        """add a variable to the list of deleted variables"""
        #if etype == 'Any':
        #    raise BadRQLQuery('"Any" is not supported in DELETE statement')
        vref.parent = self
        self.main_variables.append( (etype.encode(), vref) )

    def add_main_relation(self, relation):
        """add a relation to the list of deleted relations"""
        assert isinstance(relation.children[0], nodes.VariableRef)
        assert isinstance(relation.children[1], nodes.Comparison)
        assert isinstance(relation.children[1].children[0], nodes.VariableRef)
        relation.parent = self
        self.main_relations.append( relation )


class Insert(Statement):
    """the Insert node is the root of the syntax tree for insertion statement
    """
    TYPE = 'insert'
    
    def __init__(self):
        Statement.__init__(self)
        self.main_variables = []
        self.main_relations = []
        self.inserted_variables = {}
                              
    def __repr__(self):
        result = ['INSERT']
        result.append(', '.join(['%r %r' % (etype, var)
                                 for etype, var in self.main_variables]))
        if self.main_relations:
            result.append(':')
            result.append(', '.join([repr(rel) for rel in self.main_relations]))
        restr = self.get_restriction()
        if restr is not None:
            result.append('WHERE %r' % restr)
        return ' '.join(result)

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['INSERT']
        result.append(', '.join(['%s %s' % (etype, var)
                                 for etype, var in self.main_variables]))
        if self.main_relations:
            result.append(':')
            result.append(', '.join([rel.as_string(encoding, kwargs)
                                     for rel in self.main_relations]))
        restr = self.get_restriction()
        if restr is not None:
            result.append('WHERE %s' % restr.as_string(encoding, kwargs))
        return ' '.join(result)

    def copy(self):
        new = Statement.copy(self)
        for etype, var in self.main_variables:
            vref = nodes.VariableRef(new.get_variable(var.name))
            new.add_main_variable(etype, vref)
        for child in self.main_relations:
            new.add_main_relation(child.copy(new))
        #assert check_relations(new)
        return new

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_insert( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_insert( self, *args, **kwargs )

    def selected_terms(self):
        return [vref for et, vref in self.main_variables]
        
    def add_main_variable(self, etype, vref):
        """add a variable to the list of inserted variables"""
        if etype == 'Any':
            raise BadRQLQuery('"Any" is not supported in INSERT statement')
        self.main_variables.append( (etype.encode(), vref) )
        vref.parent = self
        self.inserted_variables[vref.variable] = 1
        
    def add_main_relation(self, relation):
        """add a relation to the list of inserted relations"""
        var = relation.children[0].variable
        rhs = relation.children[1]
        if not self.inserted_variables.has_key(var):
            if isinstance(rhs, nodes.Constant):
                msg = 'Using variable %s in declaration but %s is not an \
insertion variable'
                raise BadRQLQuery(msg % (var, var))
        relation.parent = self
        self.main_relations.append( relation )

        
class Update(Statement):
    """the Update node is the root of the syntax tree for update statement
    """
    TYPE = 'update'

    def __init__(self):
        Statement.__init__(self)
        self.main_relations = []

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['SET']
        result.append(', '.join([rel.as_string(encoding, kwargs)
                                 for rel in self.main_relations]))
        r = self.get_restriction()
        if r is not None:
            result.append('WHERE %s' % r.as_string(encoding, kwargs))
        return ' '.join(result)

    def copy(self):
        new = Statement.copy(self)
        for child in self.main_relations:
            new.add_main_relation(child.copy(new))
        #assert check_relations(new)
        return new

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_update( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_update( self, *args, **kwargs )

    def selected_terms(self):
        return []
        
    def add_main_relation(self, relation):
        """add a relation to the list of modified relations"""
        relation.parent = self
        self.main_relations.append( relation )
