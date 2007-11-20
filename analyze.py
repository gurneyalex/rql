"""Analyze of the RQL syntax tree to get possible types for rql variables

:organization: Logilab
:copyright: 2004-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

import warnings
warnings.filterwarnings(action='ignore', module='logilab.constraint.propagation')

from logilab.constraint import Repository, Solver, fd

from rql import TypeResolverException
from rql import nodes 
from rql.utils import iget_nodes
from pprint import pprint


class ETypeResolver:
    """resolve variables types according to the schema

    CSP modelisation :
    
      variable    <-> RQL variable
      domains     <-> different entity's types defined in the schema
      constraints <-> relations between (RQL) variables
    """
    
    def __init__(self, schema, uid_func_mapping=None):
        """
        * `schema` is an instance implemeting ISchema to describe entities and
          relations
        * `uid_func_mapping` is a dictionary with as key a string designing an
          attribute used as Unique IDentifiant and with associated value a
          method that maybe used to get an entity's type given the value of
          the attribute
        """
        self.set_schema(schema)
        # mapping from relation to function taking rhs value as argument
        # and returning an entity type
        self.uid_func_mapping = uid_func_mapping or {}
        if uid_func_mapping:
            self.uid_func = uid_func_mapping.values()[0]
        else:
            self.uid_func = None
            
    def set_schema(self, schema):
        self.schema = schema
        # default domain for a variable
        self._base_domain = [str(etype) for etype in schema.entities()]
        self._nonfinal_domain = [str(etype) for etype in schema.entities() if not etype.is_final()]
        
    def visit(self, node, uid_func_mapping=None, kwargs=None, debug=False):
        # FIXME: not thread safe
        if uid_func_mapping:
            assert len(uid_func_mapping) <= 1
            self.uid_func_mapping = uid_func_mapping
            self.uid_func = uid_func_mapping.values()[0]
        if self.uid_func:
            # check rewritten uid const
            for consts in node.stinfo['rewritten'].values():
                if not consts:
                    continue
                uidtype = self.uid_func(consts[0].eval(kwargs))
                for const in consts:
                    const.uidtype = uidtype
        self.kwargs = kwargs
        # init variables for a visit
        domains = {}
        constraints = []
        # set domain for the all variables
        for var in node.defined_vars.values():
            domains[var.name] = fd.FiniteDomain(self._base_domain)
        # no variable short cut
        if not domains:
            return [{}]
        # add restriction specific to delete and insert 
        if node.TYPE in ('delete', 'insert'):
            for etype, variable in node.main_variables:
                if node.TYPE == 'delete' and etype == 'Any':
                    continue
                assert etype in self.schema, etype
                var = variable.name
                constraints.append(fd.make_expression(
                    (var,), '%s == %r' % (var, etype)))
            for relation in node.main_relations:
                self._visit(relation, constraints)
        # add restriction specific to update
        elif node.TYPE == 'update':
            for relation in node.main_relations:
                self._visit(relation, constraints)
        
        restriction = node.get_restriction()
        if restriction is not None:
            # get constraints from the restriction subtree
            self._visit(restriction, constraints)
        elif node.TYPE == 'select':
            varnames = [v.name for v in node.get_selected_variables()]
            if varnames:
                # add constraint on real relation types if no restriction
                types = [eschema.type for eschema in self.schema.entities()
                         if not eschema.is_final()]
                constraints.append(fd.make_expression(varnames, '%s in %s ' % (
                    '=='.join(varnames), types)))
        
        # debug info
        if debug > 1:
            print "- AN1 -"+'-'*80
            print node
            print "DOMAINS:"
            pprint(domains)
            print "CONSTRAINTS:"
            pprint(constraints)
            
        return self.solve(node, domains, constraints, kwargs)


    def solve(self, node, domains, constraints, kwargs=None):
        # solve the problem and check there is at least one solution
        r = Repository(domains.keys(), domains, constraints)
        solver = Solver()
        sols = solver.solve(r, verbose=0)
        if not sols:
            rql = node.as_string('utf8', kwargs)
            raise TypeResolverException(
                'Unable to resolve variables types in "%s"!!' % (rql))
        return sols

        
    def _visit(self, node, constraints):
        """recurse among the tree"""
        func = getattr(self, 'visit_%s' % node.__class__.__name__.lower())
        func(node, constraints)
        #node.accept(self, constraints)
        for c in node.children:
            self._visit(c, constraints)


    def _uid_node_types(self, valnode):
        types = set()
        for cst in iget_nodes(valnode, nodes.Constant):
            assert cst.type
            if cst.type == 'Substitute':
                eid = self.kwargs[cst.value]
            else:
                eid = cst.value
            cst.uidtype = self.uid_func(eid)
            types.add(cst.uidtype)
        return types
    
    def visit_relation(self, relation, constraints):
        """extract constraints for an relation according to it's  type"""
        rtype = relation.r_type
        lhs, rhs = relation.get_parts()
        if relation.is_types_restriction():
            types = [c.value for c in iget_nodes(rhs, nodes.Constant)
                     if c.type == 'etype']
            if relation._not:
                not_types = [t for t in self._nonfinal_domain if not t in types]
                types = not_types
            constraints.append(fd.make_expression(
                (lhs.name,), '%s in %s ' % (lhs.name, types)))
            return
        elif rtype in self.uid_func_mapping:
            if relation._not or relation.operator() != '=':
                # non final entity types
                types = self._nonfinal_domain
            else:
                types = self._uid_node_types(rhs)
            if types:
                constraints.append(fd.make_expression(
                    (lhs.name,), '%s in %s ' % (lhs.name, types)))
                return
        if isinstance(rhs, nodes.Comparison):
            rhs = rhs.children[0]
        rschema = self.schema.relation_schema(rtype)
        if isinstance(lhs, nodes.Constant): # lhs is a constant node (simplified tree)
            if not isinstance(rhs, nodes.VariableRef):
                return
            var = rhs.name
            if self.uid_func:
                alltypes = set()
                for etype in self._uid_node_types(lhs):
                    for targettypes in rschema.objects(etype):
                        alltypes.add(targettypes)
            else:
                alltypes = rschema.objects()
            cstr = '%s in (%s,)' % (
                    var, ','.join('"%s"' % t for t in alltypes))
            vars = [var]
        elif isinstance(rhs, nodes.Constant) and not rschema.is_final():
            if not isinstance(lhs, nodes.VariableRef):
                return
            var = lhs.name
            if self.uid_func:
                alltypes = set()
                for etype in self._uid_node_types(rhs):
                    for targettypes in rschema.subjects(etype):
                        alltypes.add(targettypes)
            else:
                alltypes = rschema.subjects()
            cstr = '%s in (%s,)' % (
                    var, ','.join('"%s"' % t for t in alltypes))
            vars = [var]
        else:
            if not isinstance(lhs, nodes.VariableRef):
                # XXX: check relation is valid
                return
            lhsvar = lhs.name
            rhsvars = []
            samevar = False
            for v in iget_nodes(rhs, nodes.VariableRef):
                if v.name == lhsvar:
                    samevar = True
                else:
                    rhsvars.append(v.name)
            if rhsvars:
                s2 = '=='.join(rhsvars)
                res = []
                for fromtype, totypes in rschema.associations():
                    cstr = '(%s=="%s" and %s in (%s,))' % (
                        lhsvar, fromtype, s2, ','.join('"%s"' % t for t in totypes))
                    res.append(cstr)
                cstr = ' or '.join(res)
            else:
                cstr = '%s in (%s,)' % (
                    lhsvar, ','.join('"%s"' % t for t in rschema.subjects()))
            vars = [lhsvar] + rhsvars
            if samevar:
                res = []
                for fromtype, totypes in rschema.associations():
                    if not fromtype in totypes:
                        continue
                    res.append(fromtype)
                cstr2 = '%s in (%s,)' % (lhsvar, ','.join('"%s"' % t for t in res))
                constraints.append(fd.make_expression([lhsvar], cstr2))
        constraints.append(fd.make_expression(vars, cstr))

    def visit_and(self, et, constraints):
        pass
    def visit_or(self, ou, constraints):
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


# ==========================================================



class UnifyError(Exception):
    """raised when unification produces an error"""

# XXX: C'est l'algo de NlpTools, on peut le simplifier
# bcp car on n'a que des traits de type { x: [v1], y:[v2] }
# on peut en faire une version non destructive en traquant
# les id() des listes (qui servent de pointeurs)
# ensuite on peut enlever les deepcopy dans unify_sols
def feature_unify(f1, f2):
    f1_real = f1
    while type(f1_real) == list:
        f1 = f1_real
        f1_real = f1_real[0]
    f2_real = f2
    while type(f2_real) == list:
        f2 = f2_real
        f2_real = f2_real[0]
    if f1_real == None:
        if type(f1) == list:
            f1[0] = f2_real
            return f1
        return f2
    if f2_real == None:
        if type(f2) == list:
            f2[0] = f1_real
            return f2
        return f1
    if type(f1_real)!=dict and f1_real == f2_real:
        if type(f1) == list:
            f1[0] = f2_real
            return f2
        elif type(f2) == list:
            f2[0] = f1_real
            return f1
        return f1
    if type(f1_real) == dict and type(f2_real) == dict:
        for k2, v2 in f2_real.items():
            v1 = f1_real.get(k2, [None])
            vv = feature_unify(v2, v1)
            f1_real[k2] = vv
        return f1_real
    raise UnifyError

def deepcopy(s):
    r = {}
    memo = {}
    for k, v in s.items():
        if type(v)==list:
            seen = memo.setdefault(id(v),[v[0]])
        r[k] = v
    return r

def unify_sols( sols1, sols2 ):
    sols = []
#    print "Unifying"
#    print "Sols1", sols1
#    print "Sols2", sols2
    for s1 in sols1:
        for s2 in sols2:
            sa = deepcopy(s1)
            sb = deepcopy(s2)
            try:
                s = feature_unify( sa, sb )
                sols.append(s)
            except UnifyError:
                pass
#    print "Result", sols
    return sols

def feature_get( dct, n ):
    """Simplified version of feature_set for a feature
    set containing no subfeatures"""
    v = dct[n]
    while type(v)==list:
        v=v[0]
    return v

def feature_set( dct, n, val ):
    """Simplified version of feature_set for a feature
    set containing no subfeatures"""
    v = dct[n]
    if type(v)!=list:
        dct[n] = val
    while type(v[0])==list:
        v=v[0]
    v[0] = val


def flatten_features( f ):
    for k, v in f.items():
        while type(v)==list:
            v = v[0]
        f[k] = v
    return f

def fprint( f ):
    from NlpTools.grammar.unification import feature_pprint_text
    feature_pprint_text(f)


BASE_TYPES_MAP = {
    'String' : 'String',
    'Int' : 'Int',
    'Float' : 'Float',
    'Boolean' : 'Boolean',
    'Date' : 'Datetime',
    'Time' : 'Datetime',
    'Datetime' : 'Datetime',
    'Password' : 'String',
    'Bytes' : 'Bytes',
    }



class UnifyingETypeResolver:
    """resolve variables types according to the schema

    CSP modelisation :
    
      variable    <-> RQL variable
      domains     <-> different entity's types defined in the schema
      constraints <-> relations between (RQL) variables
    """
    
    def __init__(self, schema, uid_func_mapping=None):
        # mapping from relation to function taking rhs value as argument
        # and returning an entity type
        self.uid_func_mapping = {}
        if uid_func_mapping:
            self.uid_func_mapping = uid_func_mapping
        # default domain for a variable
        self.set_schema(schema)

    def set_schema(self, schema):
        self.schema = schema
        # default domain for a variable
        self._base_domain = schema.entities()
        self._types = [eschema.type for eschema in self.schema.entities()
                       if not eschema.is_final()]

    def visit(self, node, uid_func_mapping=None, kwargs=None, debug=False):
#        print "QUERY", node
        if uid_func_mapping:
            self.uid_func_mapping=uid_func_mapping
        sols = node.accept(self)
        # XXX: make sure sols are reported only once
        sols = [flatten_features(f) for f in sols]
        if not sols:
            raise TypeResolverException(
                'Unable to resolve variables types in "%s"!!'%node)
        return sols
    
    def visit_children(self, node):
        sols1 = [{}]
        for n in node.children:
            sols2 = n.accept(self)
            sols1 = unify_sols( sols1, sols2 )
        return sols1


    def visit_insert_or_delete(self, node):
        t = {}
        for etype, variable in node.main_variables:
            t[variable.name] = etype
        sols = [t]
        for relation in node.main_relations:
            sols2 = relation.accept(self)
            sols = unify_sols( sols, sols2 )
        return sols
            
    def visit_delete(self, node):
        return self.visit_insert_or_delete( node )

    def visit_select(self, node):
        sols = self.visit_children(node)
        for n in node.selected:
            sols2 = n.accept(self)
            for s in sols2:
                del s['type']
            sols = unify_sols( sols, sols2 )

        # add non-final types for non resolved vars
        extra = []
        for s in sols:
            for k in s:
                v = feature_get( s, k )
                if v is None:
                    for t in self._types:
                        extra.append( { k : t } )
        if extra:
            sols = unify_sols( sols, extra )
        return sols

    def visit_insert(self, node ):
        return self.visit_insert_or_delete( node )

    def visit_relation(self, relation ):
        r_type = relation.r_type
#        print "Relation", r_type
        lhs, rhs = relation.get_parts()
        expr_sols = rhs.accept(self)
        if r_type == 'is' and not relation._not:
            for s in expr_sols:
                typ = s['type']
                s[lhs.name] = typ
                del s['type']
            return expr_sols
        elif r_type == 'is' and relation._not:
            all_types = [ { lhs.name: t } for t in self._base_domain]
            sols = []
            not_types = [ s['type'] for s in expr_sols ]
            for s in all_types:
                if s[lhs.name] not in not_types:
                    sols.append(s)
            return sols
                
        
        r_schema = self.schema.relation_schema(r_type)
#        print "Schema", r_schema
        l = []
        typ = [None]
        vlhs = [{'type' : typ, lhs.name : typ }]
        for from_type, to_types in r_schema.association_types():
            for to_type in to_types:
                # a little base type pre-unification
                to_type = BASE_TYPES_MAP.get(to_type,to_type)
                s = {
                    'type' : [to_type],
                    lhs.name : [from_type],
                    }
                l.append(s)
        sols = unify_sols( l, expr_sols )
        for s in sols:
            del s['type']
        return sols

    def visit_comparison(self, comparison):
        if len(comparison)==0:
            return [{}]
        sols = comparison[0].accept(self)
        return sols

    def visit_function(self, function):
        # XXX : todo function typing
        return [{ 'type':[None]}]

    def visit_variableref(self, variableref):
        var = variableref.name
        typ = [None]
        sols = [{ 'type' : typ, var : typ }]
        return sols

    def visit_constant(self, constant):
        _typ = constant.type
        if _typ == 'etype':
            _typ = constant.value
        elif _typ == 'Substitute':
            return [{}]
        return [{ 'type' : _typ }]

    def visit_keyword(self, keyword):
        return [{}]
    def visit_group(self, group):
        return [{}]
    def visit_sort(self, sort):
        return [{}]
    
    def visit_mathexpression(self, mathexpression):
        lhs, rhs = mathexpression
        sols1 = lhs.accept( self )
        sols2 = rhs.accept( self )
        sols = unify_sols( sols1, sols2 )
        return sols

    def visit_and(self, et):
        sols1 = et[0].accept(self)
        for n in et[1:]:
            sols2 = n.accept(self)
            sols1 = unify_sols( sols1, sols2 )
        return sols1
    
    def visit_or(self, ou):
        sols = []
        for n in ou:
            sols += n.accept(self)
        return sols
    
#ETypeResolver = UnifyingETypeResolver
