/* -*- mode:c++ -*- */

#ifndef __NODES_HPP__
#define __NODES_HPP__


//#include <Python.h>
#include <map>
#include <string>
#include <list>
#include <iostream>
#include <set>
#include <typeinfo>


class RQLVisitor;
class RelationNode;
class RQLNode;
class VarNode;

typedef std::set<std::string> string_set_t;
typedef std::list<RQLNode*> nodes_list_t;
typedef std::map<std::string,VarNode*> var_map_t;
typedef std::pair<std::string,VarNode*> var_pair_t;
typedef std::list< var_pair_t > var_list_t;
typedef std::list< RelationNode* > rel_list_t;

#define DEBUG 0

std::string unquote( std::string& str );

bool is_r_type( std::string& str );
bool is_e_type( std::string& str );
bool is_funcname( std::string& str );
bool is_var( std::string& str );


class TypeDict {
public:
    void add_type( const char* str ) { typeset.insert( std::string(str) ); }

    bool has_type( const std::string& type_name ) {
	string_set_t::iterator it = typeset.find( type_name );
	if (it == typeset.end()) {
	    return false;
	}
	return true;
    }

    string_set_t typeset;
};


class RQLNode {
public:
    RQLNode() {
#if DEBUG
    std::cout<< typeid(this).name() << "(" << (void*)this << ")" << std::endl;
#endif
    }
    virtual ~RQLNode() {
#if DEBUG
	std::cout<< "~" << typeid(this).name() << "(" << (void*)this << ")" << "{";
#endif
	for( nodes_list_t::iterator it=m_children.begin(); it!=m_children.end(); ++it ) {
	    delete *it;
	}	 
#if DEBUG
	std::cout<< "}" << std::endl;
#endif
    }
        
    nodes_list_t& get_children() { return m_children; }

    virtual void visit( RQLVisitor* visitor );

    void append( RQLNode* node ) { m_children.push_back( node ); }

    virtual void display( std::ostream& sout, int level=0 );
    void display_children( std::ostream& sout, int level );

    friend class RQLVisitor;
protected:
    nodes_list_t  m_children;

};


std::ostream& operator<<( std::ostream& sout, RQLNode& node );

class EType {
};


class BinaryOp : public RQLNode {
public:
    BinaryOp() {}
    BinaryOp( RQLNode* lhs, RQLNode* rhs ) { append(lhs); append(rhs); }
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
};



class ExprNode : public RQLNode {
public:
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
};

class VarNode : public ExprNode {
public:
    VarNode( const std::string& _name ):name(_name) {}
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
    const std::string& getname() const { return name; }
    std::string name;
};

/*
class TypeNode : public ExprNode {
public:
    TypeNode( const std::string& _name ):name(_name) {}
    virtual void display( std::ostream& sout, int level=0 );
    std::string name;
};
*/

class Constant : public ExprNode {
public:
    Constant( const std::string& _type, const std::string& _val ):type(_type),strval(_val) {}
    Constant( const std::string& _type, int _val ):type(_type),intval(_val) {}
    Constant( const std::string& _type, double _val ):type(_type),floatval(_val) {}

    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );

    std::string type;
    std::string strval;
    int intval;
    double floatval;
};

class FuncNode : public ExprNode {
public:
    FuncNode( const std::string& _name ):name(_name) {}
    virtual void visit( RQLVisitor* visitor );
    std::string name;
};

/*
class VariableRef : public RQLNode {
public:
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
};
*/

class MathExpression : public ExprNode {
public:
    MathExpression( std::string _op, ExprNode* lhs, ExprNode* rhs ):op(_op)
    {
	append(lhs);
	append(rhs);
    }
    virtual void visit( RQLVisitor* visitor );
    std::string op;
};

class StmtNode : public RQLNode {
public:
    StmtNode( TypeDict* dct):typedict(dct) {}
    void add_main_variable( std::string& etype, VarNode* v );
    void add_main_relation( RelationNode* v );

    VarNode* get_variable( const std::string& varname );
    ExprNode* get_type( const std::string& typname );
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );


    var_map_t varmap;
    var_list_t main_variables;
    rel_list_t main_relations;
    
    std::streampos stmt_start, stmt_end;
    TypeDict* typedict;
};

class SelectStmt : public StmtNode {
public:
    SelectStmt( TypeDict * dct ):StmtNode(dct),distinct(false),limit(-1),offset(0) {}
    ~SelectStmt() {
	for( nodes_list_t::iterator it=selected.begin(); it!=selected.end(); ++it ) {
	    delete *it;
	}	
    }
    void set_statement_type( const std::string& type ) { statement_type = type; }
    void append_selected( RQLNode* node ) { selected.push_back( node ); }
    void set_limit( int _limit ) { limit = _limit; }
    void set_offset( int _offset ) { offset = _offset; }
    virtual void visit( RQLVisitor* visitor );
    bool distinct;
    int limit, offset;
    std::string statement_type;
    nodes_list_t selected;
};

class InsertStmt : public StmtNode {
public:
    InsertStmt( TypeDict * dct ):StmtNode(dct) {}
    virtual void visit( RQLVisitor* visitor );
};

class UpdateStmt : public StmtNode {
public:
    UpdateStmt( TypeDict * dct ):StmtNode(dct) {}
    virtual void visit( RQLVisitor* visitor );
};

class DeleteStmt : public StmtNode {
public:
    DeleteStmt( TypeDict * dct ):StmtNode(dct) {}
    virtual void visit( RQLVisitor* visitor );
};

class SortTermNode : public RQLNode {
public:
    SortTermNode( ExprNode* e, bool _ordering ):expr(e),ordering(_ordering) {}
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
    ExprNode* expr;
    bool ordering;
};

class SortNode : public RQLNode {
public:
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
};

class GroupNode : public RQLNode {
public:
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );

};


class RelNode : public BinaryOp {
public:
    RelNode():BinaryOp(),_not(false) {}
    RelNode( RelNode* lhs, RelNode* rhs ):BinaryOp(lhs,rhs),_not(false) {}

    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
    bool _not;
};

class OrNode : public RelNode {
public:
    OrNode( RelNode* lhs, RelNode* rhs ):RelNode(lhs,rhs) {}
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
};

class AndNode : public RelNode {
public:
    AndNode( RelNode* lhs, RelNode* rhs ):RelNode(lhs,rhs) {}
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
};

class RelationNode : public RelNode {
public:
    RelationNode( const std::string& _rtype ):rtype(_rtype) {}
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );

    std::string rtype;
};

class ComparisonNode : public ExprNode {
public:
    ComparisonNode( const std::string _cmp_op, ExprNode* rhs):cmp_op(_cmp_op)
    {
	append(rhs);
    }
    virtual void display( std::ostream& sout, int level=0 );
    virtual void visit( RQLVisitor* visitor );
    std::string cmp_op;
};

class RQLVisitor {
public:
    virtual ~RQLVisitor() {}
    virtual void visitRQLNode( RQLNode* node ) { defaultVisit(node); }
    virtual void visitBinaryOp( BinaryOp* node ) { defaultVisit(node); }
    virtual void visitExpr( ExprNode* node ) { defaultVisit(node); }
    virtual void visitVar( VarNode* node ) { defaultVisit(node); }
    virtual void visitConstant( Constant* node ) { defaultVisit(node); }
    virtual void visitFunc( FuncNode* node ) { defaultVisit(node); }
    virtual void visitMathExpression( MathExpression* node ) { defaultVisit(node); }
    virtual void visitStmt( StmtNode* node ) { defaultVisit(node); }
    virtual void visitSelect( SelectStmt* node ) { defaultVisit(node); }
    virtual void visitInsert( InsertStmt* node ) { defaultVisit(node); }
    virtual void visitDelete( DeleteStmt* node ) { defaultVisit(node); }
    virtual void visitUpdate( UpdateStmt* node ) { defaultVisit(node); }
    virtual void visitSortTerm( SortTermNode* node ) { defaultVisit(node); }
    virtual void visitSort( SortNode* node ) { defaultVisit(node); }
    virtual void visitGroup( GroupNode* node ) { defaultVisit(node); }
    virtual void visitRel( RelNode* node ) { defaultVisit(node); }
    virtual void visitAnd( AndNode* node ) { defaultVisit(node); }
    virtual void visitOr( OrNode* node ) { defaultVisit(node); }
    virtual void visitRelation( RelationNode* node ) { defaultVisit(node); }
    virtual void visitComparison( ComparisonNode* node ) { defaultVisit(node); }

    virtual void defaultVisit( RQLNode* node ) {
	for(nodes_list_t::iterator it=node->get_children().begin();it!=node->get_children().end();++it)
	{
	    (*it)->visit( this );
	}
    }
};


class DisplayVisitor : public RQLVisitor {
public:
    DisplayVisitor( std::ostream& _out ):out(_out) {}

    
    virtual void visitConstant( Constant* node );
    virtual void defaultVisit( RQLNode* node );

protected:
    std::ostream& out;
};


class RQLExpression {
public:
    RQLExpression():root(NULL) {}
    StmtNode& RootNode() { return *root; }

    void set_types( const TypeDict& td ) { types=td; }
    int parse( const std::string& input );
    int parse( std::istream& stream );

    void show_types();

protected:
    TypeDict  types;
    StmtNode* root;
};



#endif
