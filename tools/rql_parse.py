

import rql.rqlparse as rqlparse
from rql.nodes import *
from rql.stmts import *

builder = {
    "Constant" : Constant,
    "Function" : Function,
    "Relation" : Relation,
    "Comparison" : Comparison,
    "And" : AND,
    "Or" : OR,
    "VariableRef" : VariableRef,
    "Insert" : Insert,
    "Select" : Select,
    "Delete" : Delete,
    "Update" : Update,
    "MathExpression" : MathExpression,
    "Sort" : Sort,
    "SortTerm" : SortTerm,
}


v = rqlparse.parse("Any X where X eid 4;", builder )
