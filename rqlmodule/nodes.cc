

#include "nodes.hh"
#include <iostream>
#include <string>
#include <assert.h>
#include "rql_scanner.hh"
#include "rql_parser.hh"
#include "node_exceptions.hh"
#include <cctype>

using namespace std;

std::string unquote( std::string& str )
{
    std::string s;
    std::string::iterator it;
    bool one_slash = false;
    char c;
    c = str[0];
    s.assign(str, 1, str.size()-2 );
    it = s.begin();

    while(it!=s.end()) {
	if (one_slash) {
	    one_slash = false;
	    if (*it=='\\') {
		it = s.erase(it);
		continue;
	    }
	    if (*it==c) {
		--it;
		it = s.erase(it);
	    }
	} else if (*it=='\\') {
	    one_slash = true;
	}
	++it;
    }
    return s;
}

bool is_r_type( std::string& str )
{
    std::string::iterator it;
    for (it=str.begin();it!=str.end();++it) {
	if (*it=='_')
	    continue;
	if (!islower(*it))
	    return false;
    }
    return true;
}
bool is_e_type( std::string& str )
{
    std::string::iterator it;
    it = str.begin();
    if (!isupper(*it))
	return false;
    ++it;
    for (;it!=str.end();++it) {
	if (!islower(*it))
	    return false;
    }
    return true;
}

bool is_funcname( std::string& str )
{
    std::string::iterator it;
    for (it=str.begin();it!=str.end();++it) {
	if (false)
	    return false;
    }
    return true;
}

bool is_var( std::string& str )
{
    std::string::iterator it;
    it = str.begin();
    if (!isupper(*it)) {
	return false;
    }
    ++it;
    for (;it!=str.end();++it) {
	if (isdigit(*it))
	    continue;
	if (*it == '_')
	    continue;
	if (!isupper(*it))
	    return false;
    }
    return true;
}

/* display nodes */
void RQLNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "RQLNode(";
    display_children( sout, level+1 );
    sout << ")";
}

void RQLNode::display_children( ostream& sout, int level )
{
    if (m_children.size()>1) {
	nodes_list_t::iterator i=m_children.begin();
	int idx = 0;
	do {
	    sout << "arg" << idx <<"=";
	    (*i)->display( sout, level );
	    ++i;
	    ++idx;
	    if (i!=m_children.end() )
		sout << "," << endl;
	} while (i!=m_children.end() );
    } else if (m_children.size()==1) {
	(*m_children.begin())->display( sout, 0 );
    }
}

void Constant::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "Constant(";
    sout << type << ", ";
    if (type=="INT") {
	sout << intval;
    } else if (type=="FLOAT") {
	sout << floatval;
    } else {
	sout << strval;
    }
    sout << ")";
    assert(m_children.size()==0);
}

void BinaryOp::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "BinaryOp(";
    display_children( sout, level+1 );
    sout << ")";
}

void ExprNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "ExprNode(";
    display_children( sout, level+1 );
    sout << ")";
}

void VarNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "VarNode(" << name << ")";
    assert(m_children.size()==0);
    sout << ")";
}

/* XXX
void TypeNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "TypeNode(" << name << ")";
    assert(m_children.size()==0);
    sout << ")";
}
*/

void StmtNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "StmtNode(";
    display_children( sout, level+1 );
    sout << ")";
}

void RelNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "RelNode( not=" << _not << ",";
    display_children( sout, level+1 );
    sout << ")";
}

void OrNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "OrNode( not=" << _not << ",";
    display_children( sout, level+1 );
    sout << ")";
}

void AndNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "AndNode( not=" << _not << ",";
    display_children( sout, level+1 );
    sout << ")";
}

void RelationNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "RelationNode( not=" << _not << ", type=" << rtype << ",";
    display_children( sout, level+1 );
    sout << ")";
}

void ComparisonNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "ComparisonNode( " << cmp_op << ",";
    display_children( sout, level+1 );
    sout << ")";
}

void GroupNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "GroupNode(";
    display_children( sout, level+1 );
    sout << ")";
}

void SortNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "SortNode(";
    display_children( sout, level+1 );
    sout << ")";
}

void SortTermNode::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "SortTermNode( order=" << ordering << ",";
    display_children( sout, level+1 );
    sout << ")";
}

/* XXX
void VariableRef::display( ostream& sout, int level )
{
    string indent( level, ' ' );
    sout << indent << "VariableRef(";
    display_children( sout, level+1 );
    sout << ")";
}
*/

ostream& operator<<( ostream& sout, RQLNode& node )
{
    node.display( sout );
    return sout;
}

void StmtNode::add_main_variable( string& etype, VarNode* v )
{
    main_variables.push_back( var_pair_t(etype,v) );
}

void StmtNode::add_main_relation( RelationNode* v )
{
    main_relations.push_back( v );
}

VarNode* StmtNode::get_variable( const string& varname )
{
    VarNode* var;
/*    var = varmap[varname];
    if (!var) {
	var = new VarNode( varname );
	varmap[varname] = var;
    }
*/
    var = new VarNode( varname );
    return var;
}

ExprNode* StmtNode::get_type( const string& typname )
{
    if (typedict) {
	if (!typedict->has_type( typname ))
	    throw UnknownTypeException(typname);
    }
    return new Constant( "etype", typname );
}

/* Visitor callbacks */
#if 0
#define VISITDBG()  std::cout << typeid(*this).name() << std::endl
#else
#define VISITDBG()
#endif

void RQLNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitRQLNode( this );
}

void BinaryOp::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitBinaryOp( this );
}

void ExprNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitExpr( this );
}

void VarNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitVar( this );
}

void Constant::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitConstant( this );
}

void FuncNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitFunc( this );
}

void MathExpression::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitMathExpression( this );
}

void StmtNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitStmt( this );
}

void SelectStmt::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitSelect( this );
}
void InsertStmt::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitInsert( this );
}
void DeleteStmt::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitDelete( this );
}
void UpdateStmt::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitUpdate( this );
}
void SortTermNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitSortTerm( this );
}
void SortNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitSort( this );
}
void GroupNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitGroup( this );
}
void RelNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitRel( this );
}
void AndNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitAnd( this );
}
void OrNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitOr( this );
}
void RelationNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitRelation( this );
}
void ComparisonNode::visit(RQLVisitor* visitor)
{
    VISITDBG();
    visitor->visitComparison( this );
}

/* Node types */



/* DisplayVisitor */


void DisplayVisitor::visitConstant( Constant* node )
{
    node->display( out, 0 );
}


void DisplayVisitor::defaultVisit( RQLNode* node ) {
    out << typeid(*node).name() << "[" << (void*)node << "](";
    nodes_list_t::iterator it=node->get_children().begin();
    while(it!=node->get_children().end())
    {
	(*it)->visit( this );
	++it;
	if (it!=node->get_children().end()) {
	    out<<",";
	}
    }
    out << ")";
}


int RQLExpression::parse( const std::string& input )
{
    std::istringstream istr( input );

    cppcc::RqlParser s( &istr );
    if (root) delete root;
    root = s.Goal( &types );
    return 0;
}

int RQLExpression::parse( std::istream& stream )
{
    cppcc::RqlParser s( &stream );
    if (root) delete root;
    root = s.Goal( &types );
    return 0;
}

void RQLExpression::show_types()
{
    std::cout << "Types:" << std::endl;
    for( string_set_t::iterator i=types.typeset.begin();i!=types.typeset.end();++i ) {
	std::cout << *i << std::endl;
    }
}
