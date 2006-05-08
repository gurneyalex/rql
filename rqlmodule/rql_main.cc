

#include "rql_parser.hh"
#include <fstream>
#include <iostream>
#include "nodes.hh"
#include <string>

using namespace cppcc;


void skip( std::istream& f )
{
    char c;
    std::cout << "Skipping:";
    while(f) {
	f.get(c);
	std::cout << c;;
	if (c=='\n')
	    return ;
    }
}

void show_state( std::ifstream& f, std::streampos _start, std::streampos _end )
{
    char *buffer;
    ssize_t sz;
    std::streampos _saved_pos;
    _saved_pos = f.tellg();
    f.seekg( _start );
    std::cout << "Parsed: ("<<_start<<","<<_end<<")";
    sz = int(_end-_start)+1;
    //std::cout << sz << std::endl;
    buffer = new char[sz];
    f.read( buffer, _end - _start );
    std::cout << buffer << std::endl;
    delete [] buffer;
    f.seekg( _saved_pos );
}


void recover( RqlParser* s )
{
    bool recovered = false;
    while (!recovered) {
	try {
	    s->scanner.switchToState( RqlScanner::START );
	    s->scanner.skipTo( ";" );
	    recovered = true;
	} catch ( ScanException& ex2 )
	{
	    // ignore
	    std::cout << (char)s->scanner.getChar();
	}
    }
}

int main( int argc, char** argv )
{
    bool done = false;
    std::streampos _start, _end;
    if (argc<2) {
	std::cout << "Usage: rqlparse rql_file" << std::endl;
	exit(1);
    }
    std::ifstream fin( argv[1] );
    RqlParser *s = new RqlParser( &fin );
    TypeDict *types = new TypeDict();
    StmtNode* goal;

    while (!done) {
	try {
	    std::cout << "-------------------------------" << std::endl;
	    _start = s->scanner.getStreamPos();
	    if (s->scanner.la()->id == RqlToken::eof)
		break;
	    goal = s->Goal( NULL );
	    DisplayVisitor disp( std::cout );
	    goal->visit( &disp );
	    std::cout << std::endl;
	    std::cout << *goal << std::endl;
	    _end = s->scanner.getStreamPos();
	    show_state( fin, _start, _end );
	    std::cout << "OK" << std::endl;
	} catch( ScanException& exc ) {
	    std::cout << std::string(exc) << std::endl;
	    _end = s->scanner.getStreamPos();
	    show_state( fin, _start, _end );
	    recover( s );
	}
	catch( ParseException& exc ) {
	    std::cout << std::string(exc) << std::endl;
	    _end = s->scanner.getStreamPos();
	    show_state( fin, _start, _end );
	    recover( s );
	}
    }
}
