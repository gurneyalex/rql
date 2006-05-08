"""RQL implementation independant library.

Copyright (c) 2004-2005 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: __init__.py,v 1.30 2006-05-01 13:01:56 syt Exp $"

import sys
import threading
from cStringIO import StringIO

from rql._exceptions import *
from rql.interfaces import *
from rql.parser import Hercule, HerculeScanner, print_error, \
     SyntaxError, NoMoreTokens
from rql.nodes import Constant
from rql.stcheck import RQLSTChecker
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
    def __init__(self, schema, uid_func_mapping=None, Resolver=ETypeResolver):
        # chech schema
        #for e_type in REQUIRED_TYPES:
        #    if not schema.has_entity(e_type):
        #        raise MissingType(e_type)
        # create helpers
        self._rql_checker = RQLSTChecker(schema)
        self._rql_analyser = Resolver(schema, uid_func_mapping)
        self.set_schema(schema)
        
    def set_schema(self, schema):
        self.e_types = e_types = {}
        for e_type in schema.entities():
            if is_keyword(e_type) or e_type.capitalize() == 'Any':
                raise UsesReservedWord(e_type)
            e_types[e_type] = e_type
        for r_type in schema.relations():
            if is_keyword(r_type) or r_type.lower() == 'is':
                raise UsesReservedWord(r_type)
        self._rql_checker.schema = schema
        self._rql_analyser.set_schema(schema)
        
    def parse(self, rql_string):
        """return a syntax tree from an sql string"""
        tree = parse(rql_string, self.e_types)
        # check for errors not detectable at parsing time
        self._rql_checker.visit(tree)
        # ok, return the tree
        return tree

    def get_solutions(self, rql_st, uid_func_mapping=None, kwargs=None, debug=False):
        """return a list of solutions for variables of the syntax tree

        each solution is a dictionary with variable's name as key and
        variable's type as value
        """
        return self._rql_analyser.visit(rql_st, uid_func_mapping, kwargs, debug)

    def compare(self, rql_string1, rql_string2):
        """compares 2 RQL requests
        
        returns true if both requests would return the same results
        returns false otherwise
        """
        return compare_tree(self.parse(rql_string1),
                            self.parse(rql_string2))

        
def parse(rql_string, e_types=None, print_errors=True): 
    """return a syntax tree from an sql string"""   
    # make sure rql string ends with a semi-colon
    rql_string = rql_string.strip()
    if rql_string and not rql_string.endswith(';') :
        rql_string += ';'
    # parse the RQL string
    parser = Hercule(HerculeScanner(rql_string))
    try:
        return parser.goal(e_types)
    except SyntaxError, ex:
        if not print_errors:
            raise RQLSyntaxError(ex.msg)
        # try to get error message from yapps
        pinput = parser._scanner.input
        try:
            out = sys.stdout
            sys.stdout = stream = StringIO()
            try:
                print_error(pinput, ex, parser._scanner)
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

#try:
#    from rql.crql import parse
#except ImportError:
#    pass
#    #print "Falling back to python version of the RQL parser!"

