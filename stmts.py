"""Objects to construct a syntax tree and some utilities to manipulate it. 
This module defines only first level nodes (i.e. statements). Child nodes are
defined in the nodes module

:organization: Logilab
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from logilab.common.tree import VNode as Node

from rql.utils import iget_nodes
from rql._exceptions import BadRQLQuery
from rql import nodes

Node.get_nodes = iget_nodes

def add_restriction(select, relation):
    """add a restriction to a select node
    
    this is intentionally not a method of Select !
    """
    # XXX this method is deprecated
    select.add(relation)


class Statement(Node, object):
    """base class for statement nodes"""
    
    def __init__(self, e_types):
        Node.__init__(self)
        # a dictionnary mapping known entity type names to the corresponding
        # type object
        self.e_types = e_types
        # dictionnary of defined variables in the original RQL syntax tree
        self.defined_vars = {}
        self.stinfo = {'rewritten': {}}

    def __str__(self):
        return self.as_string(None, {})

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        raise NotImplementedError()
    
    def copy(self):
        new = self.__class__(self.e_types)
        for child in self.children:
            new.append(child.copy(new))
        return new
        
        
    def get_selected_variables(self):
        return self.selected_terms()
    
    def selected_terms(self):
        raise NotImplementedError
    
    # construction helper methods #############################################

    def get_type(self, name):
        """return the type object for the given entity's type name
        
        raise BadRQLQuery on unknown type
        """
        # do not check the type
        if self.e_types is None:
            return nodes.Constant(name, 'etype')
        try:
            return nodes.Constant(self.e_types[name], 'etype')
        except KeyError:
            raise BadRQLQuery('No such entity type %r' % name)
        
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

    def make_variable(self, e_type=None):
        """create a new variable with an unique name for this tree"""
        count = 0
        if e_type:
            base_name = e_type[0]
        else:
            base_name = 'TMP'
        var_name = '%s' % base_name
        while var_name in self.defined_vars.keys():
            count += 1
            var_name = '%s%s' % (base_name, count)
        return self.get_variable(var_name)

    def add(self, relation):
        """add a restriction relation (XXX should not collide with add_restriction
        or add_relation optionaly plugged by the editextensions module
        """
        r = self.get_restriction()
        if r is not None:
            new_node = nodes.AND(r, relation)
            self.replace(r, new_node)
        else:
            self.insert(0, relation)
        
    def add_type_restriction(self, variable, e_type):
        """builds a restriction node to express : variable is e_type"""
        relation = nodes.Relation('is')
        var_ref = nodes.VariableRef(variable)
        relation.append(var_ref)
        comp_entity = nodes.Comparison('=')
        comp_entity.append(nodes.Constant(e_type, 'etype'))
        relation.append(comp_entity)
        self.add(relation)

                
class Select(Statement):
    """the select node is the root of the syntax tree for selection statement
    """
    TYPE = 'select'
    
    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_select( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_select( self, *args, **kwargs )

    def __init__(self, e_types):
        Statement.__init__(self, e_types)
        # distinct ?
        self.distinct = False
        # list of selected relations (maybe variables or functions)
        self.selected = []
        # limit / offset
        self.limit = None
        self.offset = 0

    def set_limit(self, limit):
        if not isinstance(limit, (int, long)) or limit <= 0:
            raise BadRQLQuery('bad limit %s' % limit)
        self.limit = limit

    def set_offset(self, offset):
        if not isinstance(offset, (int, long)) or offset <= 0:
            raise BadRQLQuery('bad offset %s' % offset)
        self.offset = offset
        
    def copy(self):
        new = Statement.copy(self)
        for child in self.selected:
            new.append_selected(child.copy(new))
        new.distinct = self.distinct
        new.limit = self.limit
        new.offset = self.offset
        #assert check_relations(new)
        return new
        
        
    # construction helper methods #############################################

    def append_selected(self, stmt):
        if isinstance(stmt, nodes.Constant) and stmt.type == 'etype':
            raise BadRQLQuery('Entity type are not allowed in selection')
        stmt.parent = self
        self.selected.append(stmt)

    def replace(self, oldnode, newnode):
        try:
            Statement.replace(self, oldnode, newnode)
        except ValueError:
            i = self.selected.index(oldnode)
            self.selected.pop(i)
            self.selected.insert(i, newnode)
            newnode.parent = self
            
    def set_statement_type(self, stmt_type):
        """set the statement type for this selection
        this method must be called last (i.e. once selected variables has been
        added)
        """
        assert self.selected
        # Person P  ->  Any P where P is 'Person'
        e_type = stmt_type.capitalize()
        if e_type != 'Any':
            for var in self.get_selected_variables():
                self.add_type_restriction(var.variable, e_type)

    def get_description(self):
        """return the list of types or relations (if not found) associated to
        selected variables
        """
        descr = []
        for term in self.selected:
            try:
                descr.append(getattr(self, '%s_description' % term.TYPE)(term))
            except AttributeError:
                descr.append('Any')
        return descr

    def variableref_description(self, term):
        var =  term.variable
        etype = 'Any'
        for ref in var.references():
            rel = ref.relation()
            if rel is None:
                continue
            if rel.r_type == 'is' and var.name == rel.children[0].name:
                etype = rel.children[1].children[0].value.encode()
                break
            if rel.r_type != 'is' and var.name != rel.children[0].name:
                etype = rel.r_type
                break
        return etype
    
    def function_description(self, term):
        return nodes.FUNC_TYPES_MAP.get(term.name, 'Any')
        
    def constant_description(self, term):
        if term.uid:
            return term.uidtype
        return term.type
        
    def get_indexed_description(self):
        """return the list of types or relations (if not found) associated to
        selected variables
        """
        descr = []
        for index, var in enumerate(self.selected):
            var = var.variable
            var_type = 'Any'
            for ref in var.references():
                rel = ref.relation()
                if rel is None:
                    continue
                if rel.r_type == 'is' and var.name == rel.children[0].name:
                    var_type = rel.children[1].children[0].value.encode()
                    break
                if rel.r_type != 'is' and var.name != rel.children[0].name:
                    var_type = rel.r_type
                    break
            descr.append((index, var_type))
        return descr

    # string representation ###################################################
    
    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        if self.distinct:
            base = 'DISTINCT Any'
        else:
            base = 'Any'
        s = ['%s %s' % (base, ','.join([v.as_string(encoding, kwargs)
                                        for v in self.selected]))]
        r = self.get_restriction()
        if r is not None:
            s.append('WHERE %s' % r.as_string(encoding, kwargs))
        groups = self.get_groups()
        if groups is not None:
            s.append('GROUPBY %s' % ', '.join([str(group) for group in groups]))
        sorts = self.get_sortterms()
        if sorts is not None:
            s.append('ORDERBY %s' % ', '.join([str(sort) for sort in sorts]))
        if self.limit is not None:
            s.append('LIMIT %s' % self.limit)
        if self.offset:
            s.append('OFFSET %s' % self.offset)
        return ' '.join(s)
                              

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

    # quick accessors #########################################################
    
    def get_sortterms(self):
        """return a list of sortterms (i.e a Sort object).
        return an empty list if there is no sortterm.
        """
        for c in self.children:
            if isinstance(c, nodes.Sort):
                return c
        return None
    
    def get_groups(self):
        """return a list of grouped variables (i.e a Group object).
        return an empty list if there is no grouped variable.
        """
        for c in self.children:
            if isinstance(c, nodes.Group):
                return c
        return None
    
    def get_selected_variables(self):
        """returns all selected variables, including those used in aggregate
        functions
        """
        for term in self.selected_terms():
            for node in iget_nodes(term, nodes.VariableRef):
                yield node

    def selected_terms(self):
        """returns selected terms
        """
        return self.selected[:]
    
class Delete(Statement):
    """the Delete node is the root of the syntax tree for deletion statement
    """
    TYPE = 'delete'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_delete( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_delete( self, *args, **kwargs )
    
    def __init__(self, e_types):
        Statement.__init__(self, e_types)
        self.main_variables = []
        self.main_relations = []

    def copy(self):
        new = Statement.copy(self)
        for etype, var in self.main_variables:
            vref = nodes.VariableRef(new.get_variable(var.name))
            new.main_variables.append( (etype, vref) )
        for child in self.main_relations:
            new.main_relations.append(child.copy(new))
        #assert check_relations(new)
        return new
    
    def get_selected_variables(self):
        return self.selected_terms()
    
    def selected_terms(self):
        return [vref for et, vref in self.main_variables]
    
        
    def add_main_variable(self, e_type, variable):
        """add a variable to the list of deleted variables"""
        if e_type == 'Any':
            raise BadRQLQuery('"Any" is not supported in DELETE statement')
        self.main_variables.append( (e_type.encode(), variable) )

    def add_main_relation(self, relation):
        """add a relation to the list of deleted relations"""
        assert isinstance(relation.children[0], nodes.VariableRef)
        assert isinstance(relation.children[1], nodes.VariableRef)
        self.main_relations.append( relation )

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['DELETE']
        if self.main_variables:
            result.append(', '.join(['%s %s' %(e_type, var)
                                     for e_type, var in self.main_variables]))
        if self.main_relations:
            if self.main_variables:
                result.append(',')
            result.append(', '.join([rel.as_string(encoding, kwargs)
                                     for rel in self.main_relations]))
                
        r = self.get_restriction()
        if r is not None:
            result.append('WHERE %s' % r.as_string(encoding, kwargs))
        return ' '.join(result)


class Insert(Statement):
    """the Insert node is the root of the syntax tree for insertion statement
    """
    TYPE = 'insert'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_insert( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_insert( self, *args, **kwargs )
    
    def __init__(self, e_types):
        Statement.__init__(self, e_types)
        self.main_variables = []
        self.main_relations = []
        self.inserted_variables = {}

    def copy(self):
        new = Statement.copy(self)
        for etype, var in self.main_variables:
            vref = nodes.VariableRef(new.get_variable(var.name))
            new.main_variables.append( (etype, vref) )
        for child in self.main_relations:
            new.main_relations.append(child.copy(new))
        # this shouldn't ever change, don't have to copy  it
        new.inserted_variables = self.inserted_variables 
        #assert check_relations(new)
        return new

    def selected_terms(self):
        return [vref for et, vref in self.main_variables]
        
    def add_main_variable(self, e_type, variable):
        """add a variable to the list of inserted variables"""
        if e_type == 'Any':
            raise BadRQLQuery('"Any" is not supported in INSERT statement')
        self.main_variables.append( (e_type.encode(), variable) )
        self.inserted_variables[variable.variable] = 1
        
    def add_main_relation(self, relation):
        """add a relation to the list of inserted relations"""
        var = relation.children[0].variable
        rhs = relation.children[1]
        if not self.inserted_variables.has_key(var):
            if isinstance(rhs, nodes.Constant):
                msg = 'Using variable %s in declaration but %s is not an \
insertion variable'
                raise BadRQLQuery(msg % (var, var))
        self.main_relations.append( relation )

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['INSERT']
        result.append(', '.join(['%s %s' % (e_type, var)
                                 for e_type, var in self.main_variables]))
        if self.main_relations:
            result.append(':')
            result.append(', '.join([rel.as_string(encoding, kwargs)
                                     for rel in self.main_relations]))
        restr = self.get_restriction()
        if restr is not None:
            result.append('WHERE %s' % restr.as_string(encoding, kwargs))
        return ' '.join(result)
                              
    def __repr__(self):
        result = ['INSERT']
        result.append(', '.join(['%r %r' % (e_type, var)
                                 for e_type, var in self.main_variables]))
        if self.main_relations:
            result.append(':')
            result.append(', '.join([repr(rel) for rel in self.main_relations]))
        restr = self.get_restriction()
        if restr is not None:
            result.append('WHERE %r' % restr)
        return ' '.join(result)

        
class Update(Statement):
    """the Update node is the root of the syntax tree for update statement
    """
    TYPE = 'update'

    def accept(self, visitor, *args, **kwargs):
        return visitor.visit_update( self, *args, **kwargs )
    
    def leave(self, visitor, *args, **kwargs):
        return visitor.leave_update( self, *args, **kwargs )

    def __init__(self, e_types):
        Statement.__init__(self, e_types)
        self.main_relations = []

    def selected_terms(self):
        return []

    def copy(self):
        new = Statement.copy(self)
        for child in self.main_relations:
            new.main_relations.append(child.copy(new))
        #assert check_relations(new)
        return new
        
    def add_main_relation(self, relation):
        """add a relation to the list of modified relations"""
        self.main_relations.append( relation )

    def as_string(self, encoding=None, kwargs=None):
        """return the tree as an encoded rql string"""
        result = ['SET']
        result.append(', '.join([rel.as_string(encoding, kwargs)
                                 for rel in self.main_relations]))
        r = self.get_restriction()
        if r is not None:
            result.append('WHERE %s' % r.as_string(encoding, kwargs))
        return ' '.join(result)

#from rql.editextensions import check_relations
