"""Analyze of the RQL syntax tree to get possible types for RQL variables.

:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from cStringIO import StringIO
import warnings
warnings.filterwarnings(action='ignore', module='logilab.constraint.propagation')

from logilab.constraint import Repository, Solver, fd

from rql import TypeResolverException, nodes
from pprint import pprint

from copy import deepcopy

try:
    import rql_solve
except ImportError:
    rql_solve = None
    # Gecode solver not available


class ConstraintCSPProblem(object):
    def __init__(self):
        self.constraints = []
        self.domains = {}
        self.scons = []
        self.output = StringIO()

    def get_output(self):
        return self.output.getvalue()

    def printer(self, *msgs):
        self.output.write(' '.join(str(msg) for msg in msgs))
        self.output.write('\n')

    def solve(self):
        repo = Repository(self.domains.keys(), self.domains, self.get_constraints())
        solver = Solver(printer=self.printer)
        sols = solver.solve(repo, verbose=(True or self.debug))
        return sols

    def add_var(self, name, values):
        self.domains[name] = fd.FiniteDomain(values)

    def get_domains(self):
        return self.domains

    def get_constraints(self):
        return self.constraints

    def add_expr( self, vars, expr ):
        self.constraints.append( fd.make_expression( vars, expr ) )
        self.scons.append(expr)

    def var_has_type(self, var, etype):
        assert isinstance(etype, (str,unicode))
        self.add_expr( (var,), '%s == %r' % (var, etype) )

    def var_has_types(self, var, etypes):
        etypes = tuple(etypes)
        for t in etypes:
            assert isinstance( t, (str,unicode))
        if len(etypes) == 1:
            cstr = '%s == "%s"' % (var, etypes[0])
        else:
            cstr = '%s in %s ' % (var, etypes)
        self.add_expr( (var,), cstr)

    def vars_have_types(self, varnames, types):
        self.add_expr( varnames, '%s in %s' % ( '=='.join(varnames), types))

    def or_and(self, equalities):
        orred = set()
        variables = set()
        for orred_expr in equalities:
            anded = set()
            for vars, types in orred_expr:
                types=tuple(types)
                for t in types:
                    assert isinstance(t, (str,unicode))
                if len(types)==1:
                    anded.add( '%s == "%s"' % ( '=='.join(vars), types[0]) )
                else:
                    anded.add( '%s in %s' % ( '=='.join(vars), types) )
                for var in vars:
                    variables.add(var)
            orred.add( '(' + ' and '.join( list(anded) ) + ')' )
        expr = " or ".join( list(orred) )
        self.add_expr( tuple(variables), expr )

class _eq(object):
    def __init__(self, var, val):
        self.var = var
        self.val = val

    def __str__(self):
        return '%s == "%s"' % (self.var, self.val)

    def get_vars(self, s):
        s.add(self.var)

    def for_gecode(self, all_vars, all_values):
        return ["eq", all_vars.index( self.var ), all_values.index(self.val) ]

class _eqv(object):
    def __init__(self, vars):
        self.vars = set(vars)
    def __str__(self):
        return '(' + " == ".join( str(t) for t in self.vars ) + ')'
    def get_vars(self, s):
        s+=self.vars
    def for_gecode(self, all_vars, all_values):
        l = ["eqv"]
        for v in self.vars:
            l.append( all_vars.index( v ) )
        return l

class _and(object):
    def __init__(self):
        self.cond = []
    def add(self, expr):
        self.cond.append( expr )
        #if expr not in self.cond:
        #    self.cond.append( expr )
    def __str__(self):
        return '(' + " and ".join( str(t) for t in self.cond ) + ')'
    def get_vars(self, s):
        for t in self.cond:
            t.get_vars(s)
    def for_gecode(self, all_vars, all_values):
        l = ["and"]
        for n in self.cond:
            l.append( n.for_gecode(all_vars, all_values) )
        return l


class _or(_and):
    def __str__(self):
        return '(' + " or ".join( str(t) for t in self.cond ) + ')'
    def for_gecode(self, all_vars, all_values):
        l = ["or"]
        for n in self.cond:
            l.append( n.for_gecode(all_vars, all_values) )
        return l
# TODO: refactor/optimize:
# now that gecode solver is working we don't need the above _and/_or... classes
# we can generate the constraint tree directly as ["and", ['or',...], ... ]
# Another thing that 
class GecodeCSPProblem(object):
    def __init__(self):
        self.constraints = []
        self.op = _and()
        self.domains = {}

    def get_output(self):
        return ""
    def solve(self):
        # assign an integer to each var and each domain values
        all_values = set()
        all_vars = sorted(self.domains.keys())
        for values in self.domains.values():
            all_values.update(values)
        all_values = sorted(all_values)
        constraints = self.op.for_gecode( all_vars, all_values )
        var_domains = []
        for var in all_vars:
            dom = []
            for val in self.domains[var]:
                dom.append( all_values.index(val) )
            var_domains.append( dom )

        sols = rql_solve.solve( var_domains, len(all_values), constraints )
        rql_sols = []
        for s in sols:
            r={}
            for var,val in zip(all_vars,s):
                r[var] = all_values[val]
            rql_sols.append(r)
        return rql_sols

    def add_var(self, name, values):
        self.domains[name] = set(values)

    def and_eq( self, var, value ):
        eq = _eq(var, value)
        self.op.add(eq)

    def equal_vars(self, varnames):
        if len(varnames)>1:
            self.op.add( _eqv(varnames) )

    def var_has_type(self, var, etype):
        self.and_eq( var, etype)

    def var_has_types(self, var, etypes):
        for t in etypes:
            assert isinstance( t, (str,unicode))
        if len(etypes) == 1:
            self.and_eq( var, tuple(etypes)[0] )
        else:
            orred = _or()
            for t in etypes:
                orred.add( _eq(var, t) )
            self.op.add( orred )

    def vars_have_types(self, varnames, types):
        self.equal_vars( varnames )
        for var in varnames:
            self.var_has_types( var, types )

    def or_and(self, equalities):
        orred = _or()
        for orred_expr in equalities:
            anded = _and()
            for vars, types in orred_expr:
                self.equal_vars( vars )
                for t in types:
                    assert isinstance(t, (str,unicode))
                for var in vars:
                    if len(types)==1:
                        anded.add( _eq(var, types[0]) )
                    else:
                        or2 = _or()
                        for t in types:
                            or2.add( _eq(var, t) )
                        anded.add( or2 )
            orred.add(anded)
        self.op.add(orred)

if rql_solve is None:
    CSPProblem = ConstraintCSPProblem
else:
    CSPProblem = GecodeCSPProblem


class ETypeResolver(object):
    """Resolve variables types according to the schema.
    
    CSP modelisation:
     * variable    <-> RQL variable
     * domains     <-> different entity's types defined in the schema
     * constraints <-> relations between (RQL) variables
    """
    var_solkey = 'possibletypes'
    
    def __init__(self, schema, uid_func_mapping=None):
        """
        :Parameters:
         * `schema`: an object describing entities and relations that implements
           the ISchema interface.
         * `uid_func_mapping`: a dictionary where keys are strings representing an
           attribute used as a Unique IDentifier and values are methods that
           accept attribute values and return entity's types.
           [mapping from relation to function taking rhs value as argument
           and returning an entity type].
        """
        self.set_schema(schema)
        if uid_func_mapping is None:
            self.uid_func_mapping = {}
            self.uid_func = None
        else:
            self.uid_func_mapping = uid_func_mapping
            self.uid_func = uid_func_mapping.values()[0]
            
    def set_schema(self, schema):
        self.schema = schema
        # default domains for a variable
        self._base_domain = [str(etype) for etype in schema.entities()]
        self._nonfinal_domain = [str(etype) for etype in schema.entities()
                                 if not etype.is_final()]
        
    def solve(self, node, constraints):
        # debug info
        if self.debug > 1:
            print "- AN1 -"+'-'*80
            print node
            print "DOMAINS:"
            pprint(domains)
            print "CONSTRAINTS:"
            pprint(constraints.scons)

        sols = constraints.solve()

        if not sols:
            rql = node.as_string('utf8', self.kwargs)
            ex_msg = 'Unable to resolve variables types in "%s"!!' % (rql,)
            if True or self.debug:
                ex_msg += '\n%s' % (constraints.get_output(),)
            raise TypeResolverException(ex_msg)
        node.set_possible_types(sols, self.kwargs, self.var_solkey)

    def _visit(self, node, constraints=None):
        """Recurse down the tree."""
        func = getattr(self, 'visit_%s' % node.__class__.__name__.lower())
        if constraints is None:
            func(node)
        else:
            if func(node, constraints) is None:
                for c in node.children:
                    self._visit(c, constraints)

    def _uid_node_types(self, valnode):
        types = set()
        for cst in valnode.iget_nodes(nodes.Constant):
            assert cst.type
            if cst.type == 'Substitute':
                eid = self.kwargs[cst.value]
            else:
                eid = cst.value
            cst.uidtype = self.uid_func(eid)
            types.add(cst.uidtype)
        return types

    def _init_stmt(self, node):
        pb = CSPProblem()
        # set domain for the all variables
        for var in node.defined_vars.itervalues():
            pb.add_var( var.name, self._base_domain )
        # no variable short cut
        return pb

    def _extract_constraint(self, constraints, var, term, get_target_types):
        if self.uid_func:
            alltypes = set()
            for etype in self._uid_node_types(term):
                for targettypes in get_target_types(etype):
                    alltypes.add(targettypes)
        else:
            alltypes = get_target_types()

        constraints.var_has_types( var, [ str(t) for t in alltypes] )
        
    def visit(self, node, uid_func_mapping=None, kwargs=None, debug=False):
        # FIXME: not thread safe
        self.debug = debug
        if uid_func_mapping:
            assert len(uid_func_mapping) <= 1
            self.uid_func_mapping = uid_func_mapping
            self.uid_func = uid_func_mapping.values()[0]
        self.kwargs = kwargs
        self._visit(node)
        
    def visit_union(self, node):
        for select in node.children:
            self._visit(select)

    def visit_insert(self, node):
        if not node.defined_vars:
            node.set_possible_types([{}])
            return
        constraints = self._init_stmt(node)
        for etype, variable in node.main_variables:
            if node.TYPE == 'delete' and etype == 'Any':
                continue
            assert etype in self.schema, etype
            var = variable.name
            constraints.var_has_type( var, etype )
        for relation in node.main_relations:
            self._visit(relation, constraints)
        # get constraints from the restriction subtree
        if node.where is not None:
            self._visit(node.where, constraints)
        self.solve(node, constraints)
        
    visit_delete = visit_insert
    
    def visit_set(self, node):
        if not node.defined_vars:
            node.set_possible_types([{}])
            return
        constraints = self._init_stmt(node)
        for relation in node.main_relations:
            self._visit(relation, constraints)
        # get constraints from the restriction subtree
        if node.where is not None:
            self._visit(node.where, constraints)
        self.solve(node, constraints)
        
    def visit_select(self, node):
        if not (node.defined_vars or node.aliases):
            node.set_possible_types([{}])
            return
        for subquery in node.with_: # resolve subqueries first
            self.visit_union(subquery.query)
        constraints = self._init_stmt(node)
        for ca in node.aliases.itervalues():
            etypes = set(stmt.selection[ca.colnum].get_type(sol, self.kwargs)
                         for stmt in ca.query.children for sol in stmt.solutions)
            constraints.add_var( ca.name, etypes )
        if self.uid_func:
            # check rewritten uid const
            for consts in node.stinfo['rewritten'].values():
                if not consts:
                    continue
                uidtype = self.uid_func(consts[0].eval(self.kwargs))
                for const in consts:
                    const.uidtype = uidtype
        # get constraints from the restriction subtree
        if node.where is not None:
            self._visit(node.where, constraints)
        elif not node.with_:
            varnames = [v.name for v in node.get_selected_variables()]
            if varnames:
                # add constraint on real relation types if no restriction
                types = [eschema.type for eschema in self.schema.entities()
                         if not eschema.is_final()]
                constraints.vars_have_types( varnames, types )
        self.solve(node, constraints)
    
    def visit_relation(self, relation, constraints):
        """extract constraints for an relation according to it's  type"""
        if relation.is_types_restriction():
            self.visit_type_restriction(relation, constraints)
            return True
        
        rtype = relation.r_type
        lhs, rhs = relation.get_parts()
        if rtype in self.uid_func_mapping:
            if isinstance(relation.parent, nodes.Not) or relation.operator() != '=':
                # non final entity types
                etypes = self._nonfinal_domain
            else:
                etypes = self._uid_node_types(rhs)
            if etypes:
                constraints.var_has_types( lhs.name, etypes )
                return True
        if isinstance(rhs, nodes.Comparison):
            rhs = rhs.children[0]
        
        rschema = self.schema.rschema(rtype)
        if isinstance(lhs, nodes.Constant): # lhs is a constant node (simplified tree)
            if not isinstance(rhs, nodes.VariableRef):
                return True
            self._extract_constraint(constraints, rhs.name, lhs, rschema.objects)
        elif isinstance(rhs, nodes.Constant) and not rschema.is_final():
            # rhs.type is None <-> NULL
            if not isinstance(lhs, nodes.VariableRef) or rhs.type is None:
                return True
            self._extract_constraint(constraints, lhs.name, rhs, rschema.subjects)
        else:
            if not isinstance(lhs, nodes.VariableRef):
                # XXX: check relation is valid
                return True
            lhsvar = lhs.name
            rhsvars = []
            samevar = False
            if not isinstance(rhs, nodes.MathExpression):
                # rhs type is the result of the math expression, not of
                # individual variables, so don't add constraints on rhs
                # variables
                for v in rhs.iget_nodes(nodes.VariableRef):
                    if v.name == lhsvar:
                        samevar = True
                    else:
                        rhsvars.append(v.name)
            else:
                return True
            if rhsvars:
                s2 = '=='.join(rhsvars)
                res = []
                for fromtype, totypes in rschema.associations():
                    res.append( [ ( [lhsvar], [str(fromtype)]), (rhsvars, [ str(t) for t in totypes]) ] )
                constraints.or_and( res )
            else:
                constraints.var_has_types( lhsvar, [ str(subj) for subj in rschema.subjects()] )
            if samevar:
                res = []
                for fromtype, totypes in rschema.associations():
                    if not fromtype in totypes:
                        continue
                    res.append(str(fromtype))
                constraints.var_has_types( lhsvar, res )
        return True
    
    def visit_type_restriction(self, relation, constraints):
        lhs, rhs = relation.get_parts()
        etypes = set(c.value for c in rhs.iget_nodes(nodes.Constant)
                     if c.type == 'etype')
        if relation.r_type == 'is_instance_of':
            for etype in tuple(etypes):
                for specialization in self.schema.eschema(etype).specialized_by():
                    etypes.add(specialization.type)
        if relation.neged(strict=True):
            etypes = frozenset(t for t in self._nonfinal_domain if not t in etypes)

        constraints.var_has_types( lhs.name, [ str(t) for t in etypes ] )
       
    def visit_and(self, et, constraints):
        pass
    def visit_or(self, ou, constraints):
        pass        
    def visit_not(self, et, constraints):
        pass
    def visit_comparison(self, comparison, constraints):
        pass
    def visit_mathexpression(self, mathexpression, constraints):
        pass
    def visit_function(self, function, constraints):
        pass
    def visit_variableref(self, variableref, constraints):
        pass
    def visit_constant(self, constant, constraints):
        pass
    def visit_keyword(self, keyword, constraints):
        pass
    def visit_exists(self, exists, constraints):
        pass


class ETypeResolverIgnoreTypeRestriction(ETypeResolver):
    """same as ETypeResolver but ignore type restriction relation

    results are stored in as the 'allpossibletypes' key in variable'stinfo
    """
    var_solkey = 'allpossibletypes'

    def visit_type_restriction(self, relation, constraints):
        pass
    
    def visit_not(self, et, constraints):
        child = et.children[0]
        if isinstance(child, nodes.Relation) and \
           not self.schema.rschema(child.r_type).is_final():
            return True

