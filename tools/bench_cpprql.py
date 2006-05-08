from rql.rqlparse import parse
import sys

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
    "Sortterm" : SortTerm,
}

if len(sys.argv)<2:
    print "Usage: bench_cpprql file"
    print "     file: a file containing rql queries"
    sys.exit(1)

f = file(sys.argv[1])
for l in f:
    #print l,
    x = parse(l, builder)
    print ".",

