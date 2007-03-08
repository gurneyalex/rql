"""RQL implementation independant library.

:organization: Logilab
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

import sys
import threading
from cStringIO import StringIO

from yapps.runtime import print_error, SyntaxError, NoMoreTokens

from rql._exceptions import *
from rql.interfaces import *
from rql.parser import Hercule, HerculeScanner
from rql.nodes import Constant
from rql.stcheck import RQLSTAnnotator
from rql.analyze import ETypeResolver
from rql.compare import compare_tree
from rql.utils import is_keyword, get_nodes

REQUIRED_TYPES = ['String', 'Float', 'Int', 'Boolean', 'Date']

class RQLHelper:
    """Helper class for RQL handling

    give access to methods for :
      - parsing RQL strings
      - variables type resolving
      - comparison of two queries
    """
    def __init__(self, schema, uid_func_mapping=None, special_relations=None,
                 Resolver=ETypeResolver):
        # chech schema
        #for e_type in REQUIRED_TYPES:
        #    if not schema.has_entity(e_type):
        #        raise MissingType(e_type)
        # create helpers
        special_relations = special_relations or {}
        if uid_func_mapping:
            for key in uid_func_mapping:
                special_relations[key] = 'uid'
        self._annotator = RQLSTAnnotator(schema, special_relations)
        self._analyser = Resolver(schema, uid_func_mapping)
        self.set_schema(schema)
        
    def set_schema(self, schema):
        self.e_types = etypes = {}
        for etype in schema.entities():
            etype = str(etype)
            if is_keyword(etype) or etype.capitalize() == 'Any':
                raise UsesReservedWord(etype)
            etypes[etype] = etype
        for rtype in schema.relations():
            rtype = str(rtype)
            if is_keyword(rtype):# or rtype.lower() == 'is':
                raise UsesReservedWord(rtype)
        self._annotator.schema = schema
        self._analyser.set_schema(schema)

    def parse(self, rqlstring):
        """return a syntax tree from an sql string"""
        tree = parse(rqlstring, self.e_types, False)
        self._annotator.annotate(tree, checkselected=True)
        return tree
    
    def annotate(self, rqlst, checkselected=False):
        self._annotator.annotate(rqlst, checkselected=checkselected)

    def get_solutions(self, rqlst, uid_func_mapping=None, kwargs=None, debug=False):
        """return a list of solutions for variables of the syntax tree

        each solution is a dictionary with variable's name as key and
        variable's type as value
        """
        return self._analyser.visit(rqlst, uid_func_mapping, kwargs, debug)

    def simplify(self, rqlst, needcopy=True):
        if rqlst.TYPE == 'delete':
            return rqlst
        if needcopy:
            rqlstcopy = None
        else: 
            rqlstcopy = rqlst
        for var in rqlst.defined_vars.values():
            stinfo = var.stinfo
            if stinfo['constnode'] and not (
                stinfo['finalrels'] or stinfo['optrels']):
                if rqlstcopy is None:
                    rqlstcopy = rqlst.copy()
                    self.annotate(rqlstcopy)
                if needcopy:
                    var = rqlstcopy.defined_vars[var.name]
                    stinfo = var.stinfo
                assert len(stinfo['uidrels']) == 1, var
                uidrel = stinfo['uidrels'].pop()
                var = uidrel.children[0].variable
                rqlstcopy.stinfo['rewritten'][uidrel] = vconsts = []
                rhs = uidrel.children[1].children[0]
                assert isinstance(rhs, nodes.Constant), rhs
                for varref in var.references():
                    rel = varref.relation()
                    assert varref.parent
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
        return compare_tree(self.parse(rqlstring1),
                            self.parse(rqlstring2))

        
def parse(rqlstring, e_types=None, print_errors=True): 
    """return a syntax tree from an sql string"""   
    # make sure rql string ends with a semi-colon
    rqlstring = rqlstring.strip()
    if rqlstring and not rqlstring.endswith(';') :
        rqlstring += ';'
    # parse the RQL string
    parser = Hercule(HerculeScanner(rqlstring))
    try:
        return parser.goal(e_types)
    except SyntaxError, ex:
        if not print_errors:
            raise RQLSyntaxError(ex.msg)
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
