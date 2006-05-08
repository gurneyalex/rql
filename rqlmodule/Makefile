
CFLAGS=-g -Wall
LDFLAGS=
PYFLAGS=-I/usr/include/python2.3
BOOSTLDFLAGS=-lboost_python -lpython2.3

PARSEROBJ=rql_token.o rql_parser.o rql_scanner.o


rqlparse.so: rql_token.o rql_parser.o rql_scanner.o nodes.o rqlmodule.o
	${CXX} --shared -lpython2.3 ${PYFLAGS} ${CFLAGS} ${LDFLAGS} -o $@ $^

rqlboostparser.so: rql_token.o rql_parser.o rql_scanner.o nodes.o boost_module.cc
	${CXX} --shared ${BOOSTLDFLAGS} ${PYFLAGS} ${CFLAGS} ${LDFLAGS} -o $@ $^

rqlmodule.o: rqlmodule.cc
	${CXX} ${CFLAGS} ${LDFLAGS} $(PYFLAGS) -c -o $@ $^

rqlparse: rql_main.o rql_token.o rql_parser.o rql_scanner.o nodes.o
	${CXX} ${CFLAGS} ${LDFLAGS} -o $@ $^

rql_main.o: rql_main.cc rql_parser.hh rql_token.hh rql_scanner.hh
	${CXX} ${CFLAGS} -c -o $@ $<

nodes.o: nodes.cc nodes.hh
	${CXX} ${CFLAGS} -c -o $@ $<

rql_token.o: rql_token.cc rql_token.hh nodes.hh
	${CXX} ${CFLAGS} -c -o $@ $<

rql_parser.o: rql_parser.cc rql_parser.hh nodes.hh
	${CXX} ${CFLAGS} -c -o $@ $<

rql_scanner.o: rql_scanner.cc rql_scanner.hh nodes.hh
	${CXX} ${CFLAGS} -c -o $@ $<

rql_scanner.cc rql_token.cc rql_parser.cc rql_scanner.hh rql_token.h rql_parser.hh: rql.cg
	cppcc rql.cg

.PHONY: clean

clean:
	-rm -f *.o
	-rm -f *~
# dependencies
nodes.cc: nodes.hh node_exceptions.hh

