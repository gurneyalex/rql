"""Objects to construct a syntax tree and some utilities to manipulate it. 
This module defines only first level nodes (i.e. statements). Child nodes are
defined in the nodes module

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from copy import deepcopy

from logilab.common.decorators import cached

from rql import BadRQLQuery, CoercionError, nodes
from rql.base import Node
from rql.utils import rqlvar_maker

            
def _check_references(defined, varrefs):
    refs = {}
    for var in defined.values():
        for vref in var.references():
            # be careful, Variable and VariableRef define __cmp__
            if not [v for v in varrefs if v is vref]:
                raise AssertionError('buggy reference %r in %r (actual var: %r)' %
                                     (varref, self, var))
            refs[id(vref)] = 1
    for vref in varrefs:
        if not refs.has_key(id(vref)):
            raise AssertionError('unreferenced varref %r' % vref)
    return True


class Statement(nodes.EditableMixIn, Node):
    """base class for statement nodes"""

    # default values for optional instance attributes, set on the instance when
    # used
    solutions = None # list of possibles solutions for used variables
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
    
    def copy(self, copy_solutions=True, solutions=None):
        new = self.__class__()
        if self.schema is not None:
            new.schema = self.schema
        if solutions is not None:
            new.solutions = solutions
        elif copy_solutions and self.solutions is not None:
            new.solutions = deepcopy(self.solutions)
        for child in self.children:
            new.append(child.copy(new))
        return new
        
    # navigation helper methods #############################################
    
    @property 
    def root(self):
        """return the root node of the tree"""
        return self
        
    @property
    def stmt(self):
        return self

    @property
    def scope(self):
        return self
    
    def ored_rel(self, _fromnode=None):
        return None
    def neged_rel(self, _fromnode=None):
        return None
        
    def get_selected_variables(self):
        return self.selected_terms()
        
    def get_restriction(self):
        """return all the subtree with restriction clauses. That maybe a Or,
        And, or Relation instance.
        return None if there is no restriction clauses.
        """
        for c in self.children:
            if not isinstance(c, nodes.Group) and not isinstance(c, nodes.Sort):
                return c
            break
        return None
    
    def selected_terms(self):
        raise NotImplementedError()
    
    # construction helper methods #############################################
    
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
            var.stmt = self
            return var

    def allocate_varname(self):
        """return an yet undefined variable name"""
        if self._varmaker is None:
            self._varmaker = rqlvar_maker(defined=self.defined_vars)
        name =  self._varmaker.next()
        while name in self.defined_vars:
            name =  self._varmaker.next()
        return name
        
    def make_variable(self, etype=None):
        """create a new variable with an unique name for this tree"""
        var = self.get_variable(self.allocate_varname())
        if self.should_register_op:
            from rql.undo import MakeVarOperation
            self.undo_manager.add_operation(MakeVarOperation(var))
        return var
    
    def set_possible_types(self, solutions):
        self.solutions = solutions
        defined = self.defined_vars
        for var in defined.itervalues():
            var.stinfo['possibletypes'] = set()
            for solution in solutions:
                var.stinfo['possibletypes'].add(solution[var.name])

    def check_references(self):
        """test function"""
        varrefs = self.get_nodes(nodes.VariableRef)
        varrefs += self.get_selected_variables()
        for n in getattr(self, 'main_relations', ()):
            varrefs += n.iget_nodes(nodes.VariableRef)
        return _check_references(self.defined_vars, varrefs)



class Union(Statement):
    """the select node is the root of the syntax tree for selection statement
    using UNION
    """
    TYPE = 'select'
    # default values for optional instance attributes, set on the instance when
    # used
    undoing = False  # used to prevent from memorizing when undoing !
    memorizing = 0   # recoverable modification attributes

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
            
    def copy(self, copy_children=True):
        new = Union()
        if copy_children:
            for child in self.children:
                new.append(child.copy())
                assert new.children[-1].parent is new
        if self.sortterms is not None:
            new.set_sortterms(self.sortterms.copy(new))
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
        if offset is not None and (not isinstance(offset, (int, long)) or offset < 0):
            raise BadRQLQuery('bad offset %s' % offset)
        if self.should_register_op and offset != self.offset:
            from rql.undo import SetOffsetOperation
            self.undo_manager.add_operation(SetOffsetOperation(self.offset))
        self.offset = offset
        
    def set_possible_types(self, solutions):
        raise RuntimeError('Union has no solutions')
            
    @property 
    def root(self):
        """return the root node of the tree"""
        if self.parent is None:
            return self
        return self.parent
    
    # access to select statements property, which in certain condition
    # should have homogeneous values (don't use this in other cases)
    def get_restriction(self):
        raise ValueError('Union has no restriction')
    
    def get_description(self):
        return [c.get_description() for c in self.children]

#     @property
#     @cached
#     def groups(self):
#         """return a list of grouped variables (i.e a Group object) or None if
#         there is no grouped variable.
#         """
#         groups = self.children[0].get_groups()
#         if groups is None:
#             for c in self.children[1:]:
#                 if c.get_groups() is not None:
#                     raise BadRQLQuery('inconsistent groups among subqueries')
#         else:
#             for c in self.children[1:]:
#                 if not groups.is_equivalent(c.get_groups()):
#                     raise BadRQLQuery('inconsistent groups among subqueries')
#         return groups

#     @cached
#     def selected_terms(self):
#         selected = self.children[0].selected_terms()
#         for c in self.children[1:]:
#             cselected = c.selected_terms()
#             for i, term in enumerate(selected):
#                 if not term.is_equivalent(cselected[i]):
#                     raise BadRQLQuery('inconsistent selection among subqueries')
#         return selected
        
#     @property
#     def selected(self):
#         # consistency check done by selected_terms
#         return self.children[0].selected
        
#     @property
#     @cached
#     def distinct(self):
#         distinct = self.children[0].distinct
#         for c in self.children[1:]:
#             if c.distinct != distinct:
#                 raise BadRQLQuery('inconsistent distinct among subqueries')
#         return distinct

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

    def add_sort_var(self, var, asc=True):
        """add var in 'orderby' constraints
        asc is a boolean indicating the sort order (ascendent or descendent)
        """
        var = nodes.variable_ref(var)
        var.register_reference()
        term = nodes.SortTerm(var, asc)
        self.add_sort_term(term)
        
    def add_sort_term(self, term):
        if self.sortterms is None:
            self.set_sortterms(nodes.Sort())
        self.sortterms.append(term)
        if self.should_register_op:
            from rql.undo import AddSortOperation
            self.undo_manager.add_operation(AddSortOperation(term))

    def remove_sort_terms(self):
        if self.sortterms is not None:
            for term in self.sortterms.children:
                self.remove_sort_term(term)
        
    def remove_sort_term(self, term):
        """remove a sort term and the sort node if necessary"""
        if self.should_register_op:
            from rql.undo import RemoveSortOperation
            self.undo_manager.add_operation(RemoveSortOperation(term))        
        self.remove_node(term)        
        if not self.sortterms.children:
            self.sortterms = None

    def check_references(self):
        """test function"""
        for select in self.children:
            select.check_references()
        if self.sortterms:
            varrefs = self.sortterms.get_nodes(nodes.VariableRef)
            _check_references(self.defined_vars, varrefs)
        return True


class Select(Statement):
    """the select node is the base statement of the syntax tree for selection
    statement, always child of a UNION root.
    """

    def __init__(self):
        Statement.__init__(self)
        # distinct ?
        self.distinct = False
        # list of selected relations (maybe variables or functions)
        self.selected = []
        # subqueries alias
        self.aliases = {}
        self.from_ = []
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
        if self.from_:
            s.append('FROM')
            for subquery in self.from_:
                s.append('(%s) AS' % subquery.as_string(encoding, kwargs))
                aliases = self.subquery_aliases(subquery)
                if len(aliases) == 1:
                    s.append(aliases[0].name)
                else:
                    s.append('(%s)' % ','.join(ca.name for ca in aliases))
        r = self.get_restriction()
        if r is not None:
            s.append('WHERE %s' % r.as_string(encoding, kwargs))
        groups = self.groups
        if groups is not None:
            s.append(groups.as_string(encoding, kwargs))
        having = self.having
        if having is not None:
            s.append(having.as_string(encoding, kwargs))
        return ' '.join(s)
                                      
    def copy(self, copy_solutions=True, solutions=None):
        new = Select()
        if solutions is not None:
            new.solutions = solutions
        elif copy_solutions and self.solutions is not None:
            new.solutions = deepcopy(self.solutions)
        for child in self.from_: # copy subqueries first
            new.add_subquery(child.copy(), [ca.name for ca in self.subquery_aliases(child)])
        for child in self.children:
            new.append(child.copy(new))
        for child in self.selected:
            new.append_selected(child.copy(new))
        new.distinct = self.distinct
        return new
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_select(self, *args, **kwargs)
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_select(self, *args, **kwargs)

    def get_variable(self, name):
        """get a variable instance from its name
        
        the variable is created if it doesn't exist yet
        """
        if name in self.aliases:
            return self.aliases[name]
        return super(Select, self).get_variable(name)
    
    def clean_solutions(self, solutions=None):
        """when a rqlst has been extracted from another, this method returns
        solutions which make sense for this sub syntax tree
        """
        if solutions is None:
            solutions = self.solutions
        # this may occurs with rql optimization, for instance on
        # 'Any X WHERE X eid 12' query
        if not self.defined_vars:
            self.solutions = [{}]
        else:
            newsolutions = []
            for origsol in solutions:
                asol = {}
                for var in self.defined_vars:
                    asol[var] = origsol[var]
                if not asol in newsolutions:
                    newsolutions.append(asol)
            self.solutions = newsolutions
    
    # quick accessors #########################################################

    def subquery_aliases(self, subquery):
        aliases = [ca for ca in self.aliases.itervalues() if ca.query is subquery]
        aliases.sort(key=lambda x: x.colnum)
        return aliases
    
    @property 
    def root(self):
        """return the root node of the tree"""
        return self.parent

    @property
    def groups(self):
        """return a Group node or None if there is no grouped variable"""
        for c in self.children:
            if isinstance(c, nodes.Group):
                return c
        return None
    
    @property
    def having(self):
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

    def add_subquery(self, union, aliases):
        if len(aliases) != len(union.children[0].selected):
            raise BadRQLQuery('Should have the same number of aliases than selected terms in sub-query')
        self.from_.append(union)
        union.parent = self
        for i, alias in enumerate(aliases):
            if alias in self.aliases:
                raise BadRQLQuery('Duplicated alias %s' % alias)
            self.aliases[alias] = nodes.ColumnAlias(alias, i, union)
            # alias may already have been used as a regular variable, replace it
            if alias in self.defined_vars:
                for vref in self.defined_vars.pop(alias).references():
                    vref.variable = self.aliases[alias]
                    
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
            self.undo_manager.add_operation(SetDistinctOperation(self.distinct, self))
        self.distinct = value

    def undefine_variable(self, var):
        """undefine the given variable and remove all relations where it appears"""
        if hasattr(var, 'variable'):
            var = var.variable
        # remove relations where this variable is referenced
        for varref in var.references():
            rel = varref.relation()
            if rel is not None:
                self.parent.remove_node(rel)
            elif isinstance(varref.parent, nodes.SortTerm):
                self.parent.remove_sort_term(varref.parent)
            elif isinstance(varref.parent, nodes.Group):
                self.remove_group_var(varref)
            else: # selected variable
                self.remove_selected(varref)
        # effective undefine operation
        if self.should_register_op:
            from rql.undo import UndefineVarOperation
            self.undo_manager.add_operation(UndefineVarOperation(var))
        del self.defined_vars[var.name]

    def _var_index(self, var):
        """get variable index in the list using identity (Variable and VariableRef
        define __cmp__
        """
        for i, term in enumerate(self.selected):
            if term is var:
                return i
        raise IndexError()

    def remove_selected(self, var):
        """deletes var from selection variable"""
        #assert isinstance(var, VariableRef)
        index = self._var_index(var)
        if self.should_register_op:
            from rql.undo import UnselectVarOperation
            self.undo_manager.add_operation(UnselectVarOperation(var, index))
        for vref in self.selected.pop(index).iget_nodes(nodes.VariableRef):
            vref.unregister_reference()

    def add_selected(self, term, index=None):
        """override Select.add_selected to memoize modification when needed"""
        if isinstance(term, nodes.Variable):
            term = nodes.VariableRef(term, noautoref=1)
            term.register_reference()
        else:
            for var in term.iget_nodes(nodes.VariableRef):
                var = nodes.variable_ref(var)
                var.register_reference()
        if index is not None:
            self.selected.insert(index, term)
            term.parent = self
        else:
            self.append_selected(term)
        if self.should_register_op:
            from rql.undo import SelectVarOperation
            self.undo_manager.add_operation(SelectVarOperation(term))

    def add_group_var(self, var):
        """add var in 'orderby' constraints
        asc is a boolean indicating the group order (ascendent or descendent)
        """
        var = nodes.variable_ref(var)
        var.register_reference()
        groups = self.groups
        if groups is None:
            groups = nodes.Group()
            self.append(groups)
        groups.append(var)
        if self.should_register_op:
            from rql.undo import AddGroupOperation
            self.undo_manager.add_operation(AddGroupOperation(var))

    def remove_group_var(self, var):
        """remove the group variable and the group node if necessary"""
        groups = self.groups
        assert var in groups.children
        if len(groups.children) == 1:
            self.parent.remove_node(groups)
        else:
            self.parent.remove_node(var)

    
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
