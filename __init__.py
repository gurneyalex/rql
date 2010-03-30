"""RQL library (implementation independant).

:copyright:
  2001-2010 `LOGILAB S.A. <http://www.logilab.fr>`_ (Paris, FRANCE),
  all rights reserved.

:contact:
  http://www.logilab.org/project/rql --
  mailto:python-projects@logilab.org

:license:
  `General Public License version 2
  <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>`_
"""
__docformat__ = "restructuredtext en"

from rql.__pkginfo__ import version as __version__
from math import log

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
        # IgnoreTypeRestriction analyser
        from rql.analyze import ETypeResolverIgnoreTypeRestriction
        self._itr_analyser_lock = threading.Lock()
        self._itr_analyser = ETypeResolverIgnoreTypeRestriction(schema, uid_func_mapping)
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
        """Return a syntax tree created from a RQL string."""
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
        """Set solutions for variables of the syntax tree.

        Each solution is a dictionary with variable's name as key and
        variable's type as value.
        """
        self._analyser_lock.acquire()
        try:
            self._analyser.visit(rqlst, uid_func_mapping, kwargs,
                                 debug)
        finally:
            self._analyser_lock.release()

    def compute_all_solutions(self, rqlst, uid_func_mapping=None, kwargs=None,
                          debug=False):
        """compute syntaxe tree solutions with all types restriction (eg
        is/instance_of relations) ignored
        """
        self._itr_analyser_lock.acquire()
        try:
            self._itr_analyser.visit(rqlst, uid_func_mapping, kwargs,
                                 debug)
        finally:
            self._itr_analyser_lock.release()


    def simplify(self, rqlst):
        """Simplify `rqlst` by rewriting non-final variables associated to a const
        node (if annotator say we can...)

        The tree is modified in-place.
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
        rewritten = False
        for var in select.defined_vars.values():
            stinfo = var.stinfo
            if stinfo['constnode'] and not stinfo['blocsimplification']:
                #assert len(stinfo['uidrels']) == 1, var
                uidrel = stinfo['uidrels'].pop()
                var = uidrel.children[0].variable
                vconsts = []
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
                    elif rel is uidrel:
                        # drop this relation
                        rel.parent.remove(rel)
                    elif rel.is_types_restriction():
                        stinfo['typerels'].remove(rel)
                        rel.parent.remove(rel)
                    elif rel in stinfo['uidrels']:
                        # XXX check equivalence not necessary else we wouldn't be here right?
                        stinfo['uidrels'].remove(rel)
                        rel.parent.remove(rel)
                    else:
                        rhs = copy_uid_node(select, rhs, vconsts)
                        vref.parent.replace(vref, rhs)
                del select.defined_vars[var.name]
                rewritten = True
                if vconsts:
                    select.stinfo['rewritten'][var.name] = vconsts
        if rewritten and select.solutions:
            select.clean_solutions()

    def compare(self, rqlstring1, rqlstring2):
        """Compare 2 RQL requests.

        Return True if both requests would return the same results.
        """
        from rql.compare import compare_tree
        return compare_tree(self.parse(rqlstring1), self.parse(rqlstring2))


def copy_uid_node(select, node, vconsts):
    node = node.copy(select)
    node.uid = True
    vconsts.append(node)
    return node


def parse(rqlstring, print_errors=True):
    """Return a syntax tree created from a RQL string."""
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
            if ex.pos is not None:
                multi_lines_rql = rqlstring.splitlines()
                nb_lines = len(multi_lines_rql)
                if nb_lines > 5:
                    width = log(nb_lines, 10)+1
                    template = " %%%ii: %%s" % width
                    rqlstring = '\n'.join( template % (idx + 1, line) for idx, line in enumerate(multi_lines_rql))


                msg = '%s\nat: %r\n%s' % (rqlstring, ex.pos,  ex.msg)
            else:
                msg = '%s\n%s' % (rqlstring, ex.msg)
            raise RQLSyntaxError(msg), None, sys.exc_info()[-1]
        # try to get error message from yapps
        try:
            out = sys.stdout
            sys.stdout = stream = StringIO()
            try:
                print_error(ex, parser._scanner)
            finally:
                sys.stdout = out
            raise RQLSyntaxError(stream.getvalue()), None, sys.exc_info()[-1]
        except ImportError: # duh?
            sys.stdout = out
            raise RQLSyntaxError('Syntax Error', ex.msg, 'on line',
                                 1 + pinput.count('\n', 0, ex.pos)), None, sys.exc_info()[-1]
    except NoMoreTokens:
        msg = 'Could not complete parsing; stopped around here: \n%s'
        raise RQLSyntaxError(msg  % parser._scanner), None, sys.exc_info()[-1]

pyparse = parse
