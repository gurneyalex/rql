"""RQL implementation independant library.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

import sys
import threading
from cStringIO import StringIO

from rql._exceptions import *

#REQUIRED_TYPES = ['String', 'Float', 'Int', 'Boolean', 'Date']

class RQLHelper(object):
    """Helper class for RQL handling

    give access to methods for :
      - parsing RQL strings
      - variables type resolving
      - comparison of two queries
    """
    def __init__(self, schema, uid_func_mapping=None, special_relations=None,
                 resolver_class=None):
        # chech schema
        #for e_type in REQUIRED_TYPES:
        #    if not schema.has_entity(e_type):
        #        raise MissingType(e_type)
        # create helpers
        from rql.stcheck import RQLSTChecker, RQLSTAnnotator
        special_relations = special_relations or {}
        if uid_func_mapping:
            for key in uid_func_mapping:
                special_relations[key] = 'uid'
        self._checker = RQLSTChecker(schema)
        self._annotator = RQLSTAnnotator(schema, special_relations)
        self._analyser_lock = threading.Lock()
        if resolver_class is None:
            from rql.analyze import ETypeResolver
            resolver_class = ETypeResolver
        self._analyser = resolver_class(schema, uid_func_mapping)
        self.set_schema(schema)

    def set_schema(self, schema):
        from rql.utils import is_keyword
        for etype in schema.entities():
            etype = str(etype)
            if is_keyword(etype) or etype.capitalize() == 'Any':
                raise UsesReservedWord(etype)
        for rtype in schema.relations():
            rtype = str(rtype)
            if is_keyword(rtype):
                raise UsesReservedWord(rtype)
        self._checker.schema = schema
        self._annotator.schema = schema
        self._analyser.set_schema(schema)

    def parse(self, rqlstring, annotate=True):
        """return a syntax tree from an sql string"""
        rqlst = parse(rqlstring, False)
        self._checker.check(rqlst)
        if annotate:
            self.annotate(rqlst)
        rqlst.schema = self._annotator.schema
        return rqlst
    
    def annotate(self, rqlst):
        self._annotator.annotate(rqlst)

    def compute_solutions(self, rqlst, uid_func_mapping=None, kwargs=None,
                          debug=False):
        """set solutions for variables of the syntax tree

        each solution is a dictionary with variable's name as key and
        variable's type as value
        """
        self._analyser_lock.acquire()
        try:
            self._analyser.visit(rqlst, uid_func_mapping, kwargs,
                                             debug)
        finally:
            self._analyser_lock.release()
    
    def simplify(self, rqlst):
        """simplify rqlst by rewritten non final variable associated to a const
        node (if annotator say we can...)

        The tree is modified in-place
        """
        #print 'simplify', rqlst.as_string(encoding='UTF8')
        if rqlst.TYPE == 'select':
            from rql import nodes
            for select in rqlst.children:
                self._simplify(select)

    def _simplify(self, select):
        # recurse on subqueries first
        for subquery in select.with_:
            for select in subquery.query.children:
                self._simplify(select)
        for var in select.defined_vars.values():
            stinfo = var.stinfo
            if stinfo['constnode'] and not stinfo['blocsimplification']:
                #assert len(stinfo['uidrels']) == 1, var
                uidrel = stinfo['uidrels'].pop()
                var = uidrel.children[0].variable
                select.stinfo['rewritten'][var.name] = vconsts = []
                rhs = uidrel.children[1].children[0]
                #from rql.nodes import Constant
                #assert isinstance(rhs, nodes.Constant), rhs
                for vref in var.references():
                    rel = vref.relation()
                    #assert vref.parent
                    if rel is None:
                        term = vref
                        while not term.parent is select:
                            term = term.parent
                        if term in select.selection:
                            rhs = copy_uid_node(select, rhs, vconsts)
                            if vref is term:
                                select.selection[select.selection.index(vref)] = rhs
                                rhs.parent = select
                            else:
                                vref.parent.replace(vref, rhs)
                        elif term in select.orderby:
                            # remove from orderby
                            select.remove(term)
                        elif not select.having:
                            # remove from groupby if no HAVING clause
                            select.remove(term)
                        else:
                            rhs = copy_uid_node(select, rhs, vconsts)
                            select.groupby[select.groupby.index(vref)] = rhs
                            rhs.parent = select                            
                    elif rel is uidrel or rel.is_types_restriction():
                        # drop this relation
                        rel.parent.remove(rel)
                    else:
                        rhs = copy_uid_node(select, rhs, vconsts)
                        vref.parent.replace(vref, rhs)
                del select.defined_vars[var.name]
        if select.stinfo['rewritten'] and select.solutions:
            select.clean_solutions()
        
    def compare(self, rqlstring1, rqlstring2):
        """compares 2 RQL requests
        
        returns true if both requests would return the same results
        returns false otherwise
        """
        from rql.compare import compare_tree
        return compare_tree(self.parse(rqlstring1), self.parse(rqlstring2))

def copy_uid_node(select, node, vconsts):
    node = node.copy(select)
    node.uid = True
    vconsts.append(node)
    return node

        
def parse(rqlstring, print_errors=True): 
    """return a syntax tree from an sql string"""   
    from yapps.runtime import print_error, SyntaxError, NoMoreTokens
    from rql.parser import Hercule, HerculeScanner
    # make sure rql string ends with a semi-colon
    rqlstring = rqlstring.strip()
    if rqlstring and not rqlstring.endswith(';') :
        rqlstring += ';'
    # parse the RQL string
    parser = Hercule(HerculeScanner(rqlstring))
    try:
        return parser.goal()
    except SyntaxError, ex:
        if not print_errors:
            raise RQLSyntaxError('%s\n%s' % (rqlstring, ex.msg))
        # try to get error message from yapps
        try:
            out = sys.stdout
            sys.stdout = stream = StringIO()
            try:
                print_error(ex, parser._scanner)
            finally:
                sys.stdout = out
            raise RQLSyntaxError(stream.getvalue())
        except ImportError:
            sys.stdout = out
            raise RQLSyntaxError('Syntax Error', ex.msg, 'on line',
                                 1 + pinput.count('\n', 0, ex.pos))            
    except NoMoreTokens:
        msg = 'Could not complete parsing; stopped around here: \n%s'
        raise RQLSyntaxError(msg  % parser._scanner)

pyparse = parse
