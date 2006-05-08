"""RQL implementation independant library.

This module provides an interface to the C version
of the parser

Copyright (c) 2004-2005 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: crql.py,v 1.2 2006-02-13 17:27:39 ludal Exp $"



FACTORY = {}

import rql.stmts as stmts
import rql.nodes as nodes
from rqlparse import parse as _parse
import rql._exceptions as _exceptions

stmt_classes = [
    "Select",
    "Delete",
    "Insert",
    "Update",
]
node_classes = [
    "AND", "OR", "Relation", "Comparison", "Function",
    "Constant", "MathExpression", "VariableRef", "Variable", "Group",
    "Sort", "SortTerm",
    ]

error_classes = [ "BadRQLQuery", "RQLSyntaxError" ]
def loadsymb( module, symbols):
    for symbol in symbols:
        FACTORY[symbol] = getattr(module, symbol)


loadsymb( stmts, stmt_classes )
loadsymb( nodes, node_classes )
loadsymb( _exceptions, error_classes )


def parse( rql_string, e_types=None, print_errors=True ):
    if rql_string and not rql_string.endswith(';') :
        rql_string += ';'
    return _parse( rql_string, FACTORY, e_types, print_errors )
