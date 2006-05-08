from ginco.server.schema_readers import load_schema
from rql import RQLHelper
from rql.analyze import AltETypeResolver, Alt2ETypeResolver, ETypeResolver, ETypeResolver2
from pprint import pprint
import sys


SCHEMA_DIRECTORY = "/home/ludal/SB/prive/soft/ginco/applications/crm/schema"
APP_NAME = "toto"

schema = load_schema(SCHEMA_DIRECTORY, APP_NAME )

#print schema

def cmp_sol( sol1, sol2 ):
    ret = True
    for l in sol1:
        if l not in sol2:
            ret = False
            print "Sol1", l
    for l in sol2:
        if l not in sol1:
            ret = False
            print "Sol2", l
    return ret

def analyze_rq( rq ):
    print "RQL:", rq
    helper1 = RQLHelper( schema, Resolver=ETypeResolver  )
    helper2 = RQLHelper( schema, Resolver=ETypeResolver2 )
    node1 = helper1.parse( rq )
    node2 = helper2.parse( rq )
    sol1 = helper1.get_solutions( node1 )
    sol2 = helper2.get_solutions( node2 )
    return helper1, helper2, node1, node2, sol1, sol2

if len(sys.argv)<2:
    print "Usage: rql_analyze.py file"
    sys.exit(1)


for l in file(sys.argv[1]):
    helper1, helper2, node1, node2, sol1, sol2 = analyze_rq(l)
    an1 = helper1._rql_analyser
    an2 = helper2._rql_analyser
    if not cmp_sol( sol1, sol2 ):
        break
    
