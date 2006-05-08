from rql import parse
import sys
f = file(sys.argv[1])
for l in f:
    parse(l)
    print ".",

