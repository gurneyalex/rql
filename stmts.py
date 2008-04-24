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
from rql.base import BaseNode, Node
from rql.utils import rqlvar_maker, build_visitor_stub

            
def _check_references(defined, varrefs):
    refs = {}
    for var in defined.values():
        for vref in var.references():
            # be careful, Variable and VariableRef define __cmp__
            if not [v for v in varrefs if v is vref]:
                raise AssertionError('vref %r is not in the tree' % vref)
            refs[id(vref)] = 1
    for vref in varrefs:
        if not refs.has_key(id(vref)):
            raise AssertionError('vref %r is not referenced' % vref)
    return True


class ScopeNode(BaseNode):
    solutions = None # list of possibles solutions for used variables
    _varmaker = None # variable names generator, built when necessary
    where = None     # where clause node
    
    def __init__(self):
        # dictionnary of defined variables in the original RQL syntax tree
        self.defined_vars = {}
        
    def get_selected_variables(self):
        return self.selected_terms()
        
    def set_where(self, node):
        self.where = node
        node.parent = self
        
    def copy(self, copy_solutions=True, solutions=None):
        new = self.__class__()
        if self.schema is not None:
            new.schema = self.schema
        if solutions is not None:
            new.solutions = solutions
        elif copy_solutions and self.solutions is not None:
            new.solutions = deepcopy(self.solutions)
        return new

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

        
class Statement(object):
    """base class for statement nodes"""

    # default values for optional instance attributes, set on the instance when
    # used
    schema = None     # ISchema
    annotated = False # set by the annotator
    
#     def __init__(self):
#         Node.__init__(self)
#         # syntax tree meta-information
#         self.stinfo = {}

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
    
    def ored(self, _fromnode=None):
        return None
    def neged(self, _fromnode=None, strict=False):
        return None

    def check_references(self):
        """test function"""
        varrefs = self.get_nodes(nodes.VariableRef)
        try:
            return _check_references(self.defined_vars, varrefs)
        except:
            print repr(self)
            raise


class Union(Statement, Node):
    """the select node is the root of the syntax tree for selection statement
    using UNION
    """
    TYPE = 'select'
    # default values for optional instance attributes, set on the instance when
    # used
    undoing = False  # used to prevent from memorizing when undoing !
    memorizing = 0   # recoverable modification attributes

    def __init__(self):
        Node.__init__(self)
        # limit / offset
        self.limit = None
        self.offset = 0
            
    @property 
    def root(self):
        """return the root node of the tree"""
        if self.parent is None:
            return self
        return self.parent.root
    
    def get_description(self):
        return [c.get_description() for c in self.children]

    # repr / as_string / copy #################################################
    
    def __repr__(self):
        s = [repr(select) for select in self.children]
        s = ['\nUNION\n'.join(s)]
        if self.limit is not None:
            s.append('LIMIT %s' % self.limit)
        if self.offset:
            s.append('OFFSET %s' % self.offset)
        return ' '.join(s)                             
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        s = [select.as_string(encoding, kwargs) for select in self.children]
        s = [' UNION '.join(s)]
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
        new.limit = self.limit
        new.offset = self.offset
        return new

    # union specific methods ##################################################

    def locate_subquery(self, col, etype, kwargs=None):
        if len(self.children) == 1:
            return self.children[0]
        try:
            return self._subq_cache[(col, etype)]
        except AttributeError:
            self._subq_cache = {}
        except KeyError:
            pass
        for select in self.children:
            term = select.selection[col]
            for i, solution in enumerate(select.solutions):
                if term.get_type(solution, kwargs) == etype:
                    self._subq_cache[(col, etype)] = select
                    return select
        raise Exception('internal error, %s not found on col %s' % (etype, col))
    
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

    # recoverable modification methods ########################################
    
    @property
    @cached
    def undo_manager(self):
        from rql.undo import SelectionManager
        return SelectionManager(self)

    @property
    def should_register_op(self):
        return self.memorizing and not self.undoing

    def save_state(self):
        """save the current tree"""
        self.undo_manager.push_state()
        self.memorizing += 1

    def recover(self):
        """reverts the tree as it was when save_state() was last called"""
        self.memorizing -= 1
        assert self.memorizing >= 0
        self.undo_manager.recover()    

    def check_references(self):
        """test function"""
        for select in self.children:
            select.check_references()
        return True


class Select(Statement, nodes.EditableMixIn, ScopeNode):
    """the select node is the base statement of the syntax tree for selection
    statement, always child of a UNION root.
    """
    parent = None
    distinct = False
    # select clauses
    groupby = ()
    orderby = ()
    having = ()
    with_ = ()
    # set by the annotator
    has_aggregat = False
    
    def __init__(self):
        Statement.__init__(self)
        ScopeNode.__init__(self)
        self.selection = []
        # subqueries alias
        self.aliases = {}
        # syntax tree meta-information
        self.stinfo = {'rewritten': {}}

    @property 
    def root(self):
        """return the root node of the tree"""
        return self.parent
                    
    def get_description(self):
        """return the list of types or relations (if not found) associated to
        selected variables
        """
        descr = []
        for term in self.selection:
            try:
                descr.append(term.get_description())
            except CoercionError:
                descr.append('Any')
        return descr

    @property
    def children(self):
        children = self.selection[:]
        if self.groupby:
            children += self.groupby
        if self.orderby:
            children += self.orderby
        if self.where:
            children.append(self.where)
        if self.having:
            children += self.having
        if self.with_:
            children += self.with_
        return children

    # repr / as_string / copy #################################################
    
    def __repr__(self):
        return self.as_string(userepr=True)
    
    def as_string(self, encoding=None, kwargs=None, userepr=False):
        """return the tree as an encoded rql string"""
        if userepr:
            as_string = repr
        else:
            as_string = lambda x: x.as_string(encoding, kwargs)
        s = [','.join(as_string(term) for term in self.selection)]
        if self.groupby:
            s.append('GROUPBY ' + ','.join(as_string(term)
                                           for term in self.groupby))
        if self.orderby:
            s.append('ORDERBY ' + ','.join(as_string(term)
                                           for term in self.orderby))
        if self.where:
            s.append('WHERE ' + as_string(self.where))
        if self.having:
            s.append('HAVING ' + ','.join(as_string(term)
                                           for term in self.having))
        if self.with_:
            s.append('WITH ' + ','.join(as_string(term)
                                        for term in self.with_))
        if self.distinct:
            return 'DISTINCT Any ' + ' '.join(s)
        return 'Any ' + ' '.join(s)
                                      
    def copy(self, copy_solutions=True, solutions=None):
        new = Select()
        if solutions is not None:
            new.solutions = solutions
        elif copy_solutions and self.solutions is not None:
            new.solutions = deepcopy(self.solutions)
        if self.with_:
            new.set_with([sq.copy(new) for sq in self.with_], check=False)
        for child in self.selection:
            new.append_selected(child.copy(new))
        if self.groupby:
            new.set_groupby([sq.copy(new) for sq in self.groupby])
        if self.orderby:
            new.set_orderby([sq.copy(new) for sq in self.orderby])
        if self.where:
            new.set_where(self.where.copy(new))
        if self.having:
            new.set_having([sq.copy(new) for sq in self.having])
        new.distinct = self.distinct
        return new
    
    # select specific methods #################################################

    def set_statement_type(self, etype):
        """set the statement type for this selection
        this method must be called last (i.e. once selected variables has been
        added)
        """
        assert self.selection
        # Person P  ->  Any P where P is Person
        if etype != 'Any':
            for var in self.get_selected_variables():
                self.add_type_restriction(var.variable, etype)
    
    def set_distinct(self, value):
        """mark DISTINCT query"""
        if self.should_register_op and value != self.distinct:
            from rql.undo import SetDistinctOperation
            self.undo_manager.add_operation(SetDistinctOperation(self.distinct, self))
        self.distinct = value
    
    def set_orderby(self, terms):
        self.orderby = terms
        for node in terms:
            node.parent = self

    def set_groupby(self, terms):
        self.groupby = terms
        for node in terms:
            node.parent = self

    def set_having(self, terms):
        self.having = terms
        for node in terms:
            node.parent = self
            
    def set_with(self, terms, check=True):
        self.with_ = []
        for node in terms:
            self.add_subquery(node, check)
            
    def add_subquery(self, node, check=True):
        assert node.query
        node.parent = self
        self.with_.append(node)
        if check and len(node.aliases) != len(node.query.children[0].selection):
            raise BadRQLQuery('Should have the same number of aliases than '
                              'selected terms in sub-query')
        for i, alias in enumerate(node.aliases):
            alias = alias.name
            if check and alias in self.aliases:
                raise BadRQLQuery('Duplicated alias %s' % alias)
            ca = self.get_variable(alias, i)
            ca.query = node.query
            
    def get_variable(self, name, colnum=None):
        """get a variable instance from its name
        
        the variable is created if it doesn't exist yet
        """
        if name in self.aliases:
            return self.aliases[name]
        if colnum is not None: # take care, may be 0
            self.aliases[name] = nodes.ColumnAlias(name, colnum)
            # alias may already have been used as a regular variable, replace it
            if name in self.defined_vars:
                for vref in self.defined_vars.pop(name).references():
                    vref.variable = self.aliases[name]
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

#     def subquery_aliases(self, subquery):
#         aliases = [ca for ca in self.aliases.itervalues() if ca.query is subquery]
#         aliases.sort(key=lambda x: x.colnum)
#         return aliases
        
    def get_selected_variables(self):
        """returns all selected variables, including those used in aggregate
        functions
        """
        for term in self.selection:
            for node in term.iget_nodes(nodes.VariableRef):
                yield node

    # construction helper methods #############################################

    def append_selected(self, term):
        if isinstance(term, nodes.Constant) and term.type == 'etype':
            raise BadRQLQuery('Entity type are not allowed in selection')
        term.parent = self
        self.selection.append(term)
            
    def replace(self, oldnode, newnode):
        assert oldnode is self.where
        self.where = newnode
        newnode.parent = self
#         # XXX no vref handling ?
#         try:
#             Statement.replace(self, oldnode, newnode)
#         except ValueError:
#             i = self.selection.index(oldnode)
#             self.selection.pop(i)
#             self.selection.insert(i, newnode)
        
    def remove(self, node):
        if node is self.where:
            self.where = None
        elif node in self.orderby:
            self.remove_sort_term(node)
        elif node in self.groupby:
            self.remove_group_var(node)
        else:
            raise Exception('duh XXX')
        node.parent = None
        
    def undefine_variable(self, var):
        """undefine the given variable and remove all relations where it appears"""
        if hasattr(var, 'variable'):
            var = var.variable
        # remove relations where this variable is referenced
        for vref in var.references():
            rel = vref.relation()
            if rel is not None:
                self.remove_node(rel)
            # XXX may have other nodes between vref and the sort term
            elif isinstance(vref.parent, nodes.SortTerm):
                self.remove_sort_term(vref.parent)
            elif vref in self.groupby:
                self.remove_group_var(vref)
            else: # selected variable
                self.remove_selected(vref)
        # effective undefine operation
        if self.should_register_op:
            from rql.undo import UndefineVarOperation
            self.undo_manager.add_operation(UndefineVarOperation(var))
        del self.defined_vars[var.name]

    def _var_index(self, var):
        """get variable index in the list using identity (Variable and VariableRef
        define __cmp__
        """
        for i, term in enumerate(self.selection):
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
        for vref in self.selection.pop(index).iget_nodes(nodes.VariableRef):
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
            self.selection.insert(index, term)
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
        if not self.groupby:
            self.groupby = []
        vref = nodes.variable_ref(var)
        vref.register_reference()
        self.groupby.append(vref)
        vref.parent = self
        if self.should_register_op:
            from rql.undo import AddGroupOperation
            self.undo_manager.add_operation(AddGroupOperation(vref))

    def remove_group_var(self, vref):
        """remove the group variable and the group node if necessary"""
        vref.unregister_reference()
        self.groupby.remove(vref)
        if self.should_register_op:
            from rql.undo import RemoveGroupOperation
            self.undo_manager.add_operation(RemoveGroupOperation(vref))

    def remove_groups(self):
        for vref in self.groupby:
            self.remove_group_var(vref)
            
    def add_sort_var(self, var, asc=True):
        """add var in 'orderby' constraints
        asc is a boolean indicating the sort order (ascendent or descendent)
        """
        vref = nodes.variable_ref(var)
        vref.register_reference()
        term = nodes.SortTerm(vref, asc)
        self.add_sort_term(term)
        
    def add_sort_term(self, term):
        if not self.orderby:
            self.orderby = []
        self.orderby.append(term)
        term.parent = self
        for vref in term.iget_nodes(nodes.VariableRef):
            try:
                vref.register_reference()
            except AssertionError:
                pass # already referenced
        if self.should_register_op:
            from rql.undo import AddSortOperation
            self.undo_manager.add_operation(AddSortOperation(term))

    def remove_sort_terms(self):
        if self.orderby:
            for term in self.orderby:
                self.remove_sort_term(term)
        
    def remove_sort_term(self, term):
        """remove a sort term and the sort node if necessary"""
        if self.should_register_op:
            from rql.undo import RemoveSortOperation
            self.undo_manager.add_operation(RemoveSortOperation(term))
        for vref in term.iget_nodes(nodes.VariableRef):
            vref.unregister_reference()
        self.orderby.remove(term)

    def select_only_variables(self):
        selection = []
        for term in self.selection:
            for vref in term.iget_nodes(nodes.VariableRef):
                if not vref in selection:
                    selection.append(vref)
        self.selection = selection

    
class Delete(Statement, ScopeNode):
    """the Delete node is the root of the syntax tree for deletion statement
    """
    TYPE = 'delete'
    
    def __init__(self):
        Statement.__init__(self)
        ScopeNode.__init__(self)
        self.main_variables = []
        self.main_relations = []

    @property
    def children(self):
        children = self.selection[:]
        children += self.main_relations
        if self.where:
            children.append(self.where)
        return children

    @property
    def selection(self):
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
    
    # repr / as_string / copy #################################################

    def __repr__(self):
        result = ['DELETE']
        if self.main_variables:
            result.append(', '.join(['%r %r' %(etype, var)
                                     for etype, var in self.main_variables]))
        if self.main_relations:
            if self.main_variables:
                result.append(',')
            result.append(', '.join([repr(rel) for rel in self.main_relations]))
        if self.where is not None:
            result.append(repr(self.where))
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
        if self.where is not None:
            result.append('WHERE ' + self.where.as_string(encoding, kwargs))
        return ' '.join(result)

    def copy(self):
        new = Delete()
        for etype, var in self.main_variables:
            vref = nodes.VariableRef(new.get_variable(var.name))
            new.add_main_variable(etype, vref)
        for child in self.main_relations:
            new.add_main_relation(child.copy(new))
        if self.where:
            new.set_where(self.where.copy(new))
        return new


class Insert(Statement, ScopeNode):
    """the Insert node is the root of the syntax tree for insertion statement
    """
    TYPE = 'insert'
    
    def __init__(self):
        Statement.__init__(self)
        ScopeNode.__init__(self)
        self.main_variables = []
        self.main_relations = []
        self.inserted_variables = {}

    @property
    def children(self):
        children = self.selection[:]
        children += self.main_relations
        if self.where:
            children.append(self.where)
        return children

    @property
    def selection(self):
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
                              
    # repr / as_string / copy #################################################

    def __repr__(self):
        result = ['INSERT']
        result.append(', '.join(['%r %r' % (etype, var)
                                 for etype, var in self.main_variables]))
        if self.main_relations:
            result.append(':')
            result.append(', '.join([repr(rel) for rel in self.main_relations]))
        if self.where is not None:
            result.append('WHERE ' + repr(self.where))
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
        if self.where is not None:
            result.append('WHERE ' + self.where.as_string(encoding, kwargs))
        return ' '.join(result)

    def copy(self):
        new = Insert()
        for etype, var in self.main_variables:
            vref = nodes.VariableRef(new.get_variable(var.name))
            new.add_main_variable(etype, vref)
        for child in self.main_relations:
            new.add_main_relation(child.copy(new))
        if self.where:
            new.set_where(self.where.copy(new))
        return new

        
class Set(Statement, ScopeNode):
    """the Set node is the root of the syntax tree for update statement
    """
    TYPE = 'set'

    def __init__(self):
        Statement.__init__(self)
        ScopeNode.__init__(self)
        self.main_relations = []

    @property
    def children(self):
        children = self.main_relations[:]
        if self.where:
            children.append(self.where)
        return children

    @property
    def selection(self):
        return []
        
    def add_main_relation(self, relation):
        """add a relation to the list of modified relations"""
        relation.parent = self
        self.main_relations.append( relation )

    # repr / as_string / copy #################################################

    def __repr__(self):
        result = ['SET']
        result.append(', '.join(repr(rel) for rel in self.main_relations))
        if self.where is not None:
            result.append('WHERE ' + repr(self.where))
        return ' '.join(result)

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['SET']
        result.append(', '.join(rel.as_string(encoding, kwargs)
                                for rel in self.main_relations))
        if self.where is not None:
            result.append('WHERE ' + self.where.as_string(encoding, kwargs))
        return ' '.join(result)

    def copy(self):
        new = Set()
        for child in self.main_relations:
            new.add_main_relation(child.copy(new))
        if self.where:
            new.set_where(self.where.copy(new))
        return new


build_visitor_stub((Union, Select, Insert, Delete, Set))
