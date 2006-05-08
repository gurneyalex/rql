from rql.rqlparse import parse as cparse
from rql import parse
from rql.compare2 import compare_tree, RQLCanonizer, make_canon_dict
import sys
from rql.nodes import *
from rql.stmts import *
from pprint import pprint

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


f = file(sys.argv[1])
for l in f:
    #print l,
    x1 = cparse(l, builder)
    x2 = parse(l)
    l = l.strip()
    d1 = make_canon_dict( x1 )
    d2 = make_canon_dict( x2 )
    t = d1==d2
    print '%s : "%s"' % (t,l)
    if not t:
        print "CPP",x1
        pprint(d1)
        print "PYT",x2
        pprint(d2)

