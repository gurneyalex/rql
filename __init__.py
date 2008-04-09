"""RQL implementation independant library.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

import sys
import threading
from cStringIO import StringIO

from rql._exceptions import *

#REQUIRED_TYPES = ['String', 'Float', 'Int', 'Boolean', 'Date']

class RQLHelper:
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
            if is_keyword(rtype):# or rtype.lower() == 'is':
                raise UsesReservedWord(rtype)
        self._checker.schema = schema
        self._annotator.schema = schema
        self._analyser.set_schema(schema)

    def parse(self, rqlstring):
        """return a syntax tree from an sql string"""
        rqlst = parse(rqlstring, False)
        self._checker.check(rqlst)
        self.annotate(rqlst)
        rqlst.schema = self._annotator.schema
        return rqlst
    
    def annotate(self, rqlst):
        self._annotator.annotate(rqlst)

    def get_solutions(self, rqlst, uid_func_mapping=None, kwargs=None,
                      debug=False):
        """return a list of solutions for variables of the syntax tree

        each solution is a dictionary with variable's name as key and
        variable's type as value
        """
        self._analyser_lock.acquire()
        try:
            solutions = self._analyser.visit(rqlst, uid_func_mapping, kwargs,
                                             debug)
        finally:
            self._analyser_lock.release()
        rqlst.set_possible_types(solutions)
        return solutions
    
    def simplify(self, rqlst, needcopy=True):
        #print 'simplify', rqlst.as_string(encoding='UTF8')
        if rqlst.TYPE == 'select':
            from rql import nodes
            if needcopy:
                # XXX  should only copy when necessary ?
                rqlst = rqlst.copy()
                self.annotate(rqlst)
            for select in rqlst.children:
                self._simplify(select, False)
                # deal with rewritten variable which are used in orderby
                for vname in select.stinfo['rewritten']:
                    try:
                        var = rqlst.defined_vars.pop(vname)
                    except KeyError:
                        continue
                    else:
                        for vref in var.references():
                            term = vref.parent
                            while not isinstance(term, nodes.SortTerm):
                                term = term.parent
                            rqlst.remove_sort_term(term)
        return rqlst
        
    def _simplify(self, rqlst, needcopy):
        if needcopy:
            rqlstcopy = None
        else: 
            rqlstcopy = rqlst
        for var in rqlst.defined_vars.values():
            stinfo = var.stinfo
            if stinfo['constnode'] and not stinfo['blocsimplification']:
                if rqlstcopy is None:
                    rqlstcopy = rqlst.copy()
                    self.annotate(rqlstcopy)
                if needcopy:
                    var = rqlstcopy.defined_vars[var.name]
                    stinfo = var.stinfo
                #assert len(stinfo['uidrels']) == 1, var
                uidrel = stinfo['uidrels'].pop()
                var = uidrel.children[0].variable
                rqlstcopy.stinfo['rewritten'][var.name] = vconsts = []
                rhs = uidrel.children[1].children[0]
                #from rql.nodes import Constant
                #assert isinstance(rhs, nodes.Constant), rhs
                for varref in var.references():
                    rel = varref.relation()
                    #assert varref.parent
                    if rel and (rel is uidrel or rel.is_types_restriction()):
                        # drop this relation
                        rel.parent.remove(rel)
                    else:
                        rhs = rhs.copy(rqlstcopy)
                        rhs.uid = True
                        # should have been set by the analyzer
                        #assert rhs.uidtype , (rqlst, rhs, id(rhs))
                        vconsts.append(rhs)
                        # substitute rhs
                        if rel and uidrel._not:
                            rel._not = rel._not or uidrel._not
                        varref.parent.replace(varref, rhs)
                del rqlstcopy.defined_vars[var.name]
        return rqlstcopy or rqlst
        
    def compare(self, rqlstring1, rqlstring2):
        """compares 2 RQL requests
        
        returns true if both requests would return the same results
        returns false otherwise
        """
        from rql.compare import compare_tree
        return compare_tree(self.parse(rqlstring1), self.parse(rqlstring2))

        
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
