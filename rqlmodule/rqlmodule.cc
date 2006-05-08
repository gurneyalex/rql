

#include <Python.h>

#include <string>
#include <sstream>
#include <iostream>
#include <list>
#include <exception>
#include "rql_parser.hh"
#include "nodes.hh"
#include "node_exceptions.hh"

using namespace cppcc;

#undef assert
#define pyassert(x) if ((!x)) throw pyexception();

class pyrqlerror : public std::exception {
public:
    pyrqlerror( const std::string& _msg ):message(_msg) {}
    ~pyrqlerror () throw ()
    {}

    const char* what() throw() { return message.c_str(); }
protected:
    std::string message;
};

class pyexception : public std::exception {
// exception raised to notify about a Python exception
};

class PyRQLVisitor : public RQLVisitor {
public:

    PyRQLVisitor( PyObject* _e_types ):
	e_types(_e_types),statement(0L)
    {} 

    void visitConstant( Constant* node )
    {
	PyObject *cst;
	if (node->type == "Float") {
	    cst = PyObject_CallFunction( constant, "ds", node->floatval,
					 node->type.c_str() );
	} else if (node->type == "Int") {
	    cst = PyObject_CallFunction( constant, "is", node->intval,
					 node->type.c_str() );
	} else if (node->type == "NULL") {
	    cst = PyObject_CallFunction( constant, "sO", node->type.c_str(), Py_None );
	} else {
	    cst = PyObject_CallFunction( constant, "ss", node->strval.c_str(),
					 node->type.c_str() );
	}
	push( cst );
    }

    void visitComparison( ComparisonNode* node )
    {
	PyObject *top;
	PyObject *res;
	doChildren( node, 1 );

	top = pop();
	res = PyObject_CallFunction( comparison,"sO", node->cmp_op.c_str(), top );
	Py_DECREF( top );

	push( res );
    }

    void visitMathExpression( MathExpression* node )
    {
	PyObject *lhs, *rhs;
	PyObject *res;
	doChildren( node, 2 );

	lhs = pop();
	rhs = pop();
	res = PyObject_CallFunction( mathexpression,"sOO", node->op.c_str(), lhs, rhs );
	Py_DECREF(lhs);
	Py_DECREF(rhs);	

	push( res );
    }

    void visitOr( OrNode* node ) {
	binaryNode( or_, node );
    }

    void visitAnd( AndNode* node ) {
	binaryNode( and_, node );
    }

    void doChildren( RQLNode* node, int expected_children )
    {
	int count = 0;
	for( nodes_list_t::reverse_iterator it=node->get_children().rbegin();
	     it != node->get_children().rend(); ++it, ++count )
	{
	    if (expected_children>=0 && count>=expected_children) {
		throw pyrqlerror(std::string(typeid(*node).name()) +": Too many children for this node" );
	    }
	    (*it)->visit( this );
	}

    }

    void binaryNode( PyObject* callable, BinaryOp* node )
    {
	PyObject *lhs, *rhs;
	PyObject *res;
	doChildren( node, 2 );

	lhs = pop();
	rhs = pop();
	res = PyObject_CallFunction( callable,"OO", lhs, rhs );
	Py_DECREF(lhs);
	Py_DECREF(rhs);

	push(res);
    }

    void visitSelect( SelectStmt* node ) {
	PyObject *res, *selected, *obj;

	res = PyObject_CallFunction( select, "O", e_types );
	statement = node;
	pystmt = res;

	if (node->distinct) {
	    PyObject_SetAttrString( res, "distinct", Py_True );
	}
	if (node->limit>=0) {
	    obj = PyInt_FromLong( node->limit );
	    PyObject_SetAttrString( res, "limit", obj );
	    Py_DECREF(obj);
	}
	if (node->offset>=0) {
	    obj = PyInt_FromLong( node->offset );
	    PyObject_SetAttrString( res, "offset", obj );
	    Py_DECREF(obj);
	}

	selected = PyObject_GetAttrString( res, "selected" );
	addChildrenToList( selected, node->selected );
	Py_DECREF(selected);

	addChildren( res, node->get_children() );

	obj = PyObject_CallMethod( res, "set_statement_type", "s", node->statement_type.c_str() );
	pyassert( obj );
	Py_DECREF( obj );
	    
	push(res);
    }

    void visitInsert( InsertStmt* node )
    {
	PyObject *res;

	res = PyObject_CallFunction( insert, "O", e_types );
	statement = node;
	pystmt = res;

	addChildren( res, node->get_children() );
	addMainVariables( res, node );
	addMainRelations( res, node );

	push(res);
    }

    void visitUpdate( UpdateStmt* node )
    {
	PyObject *res;

	res = PyObject_CallFunction( update, "O", e_types );
	statement = node;
	pystmt = res;

	addChildren( res, node->get_children() );
	addMainRelations( res, node );

	push(res);
	
    }

    void visitDelete( DeleteStmt* node )
    {
 	PyObject *res;

	res = PyObject_CallFunction( delete_, "O", e_types );
	statement = node;
	pystmt = res;

	addChildren( res, node->get_children() );
	addMainVariables( res, node );
	addMainRelations( res, node );

	push(res);
   }

    void visitFunc( FuncNode* node )
    {
	PyObject* res;
	res = PyObject_CallFunction( function, "s", node->name.c_str() );
	addChildren( res, node->get_children() );
	push(res);
    }

    void addChildrenToList( PyObject* cont, nodes_list_t& lst )
    {
	PyObject *obj;
	for( nodes_list_t::iterator it=lst.begin();
	     it != lst.end(); ++it )
	{
	    (*it)->visit( this );
	    obj = pop();
	    PyList_Append( cont, obj );
	    Py_DECREF(obj);
	}
    }

    void addChildren( PyObject* res, nodes_list_t& lst )
    {
	PyObject *obj, *ret;
	for( nodes_list_t::iterator it=lst.begin();it != lst.end(); ++it )
	{
	    (*it)->visit( this );
	    obj = pop();
	    ret = PyObject_CallMethod( res, "append", "N", obj );
	    pyassert(ret);
	    Py_DECREF(ret);
	}
    }

    void addMainRelations( PyObject* res, StmtNode* stmt )
    {
	PyObject *obj, *ret;
	for( rel_list_t::iterator it = stmt->main_relations.begin();
	     it != stmt->main_relations.end(); ++ it ) {
	    (*it)->visit( this );
	    obj = pop();
	    ret = PyObject_CallMethod( res, "add_main_relation", "N", obj );
	    pyassert(ret);
	    Py_DECREF(ret);
	}
    }

    void addMainVariables( PyObject* res, StmtNode* stmt )
    {
	PyObject *obj, *ret;
	for( var_list_t::iterator it = stmt->main_variables.begin();
	     it != stmt->main_variables.end(); ++ it ) {
	    (it->second)->visit( this );
	    obj = pop();
	    ret = PyObject_CallMethod( res, "add_main_variable", "sN", it->first.c_str(), obj );
	    pyassert(ret);
	    Py_DECREF(ret);
	}
    }

    void visitRelation( RelationNode* node )
    {
	PyObject *res, *not_;
	if (node->_not) {
	    not_ = PyInt_FromLong( 1 );
	} else {
	    not_ = PyInt_FromLong( 0 );
	}
	res = PyObject_CallFunction( relation, "sN", node->rtype.c_str(), not_ );

	addChildren( res, node->get_children() );

	push(res);
    }


    void visitVar( VarNode* node )
    {
	PyObject *var=0, *res=0;

	var = get_var( node->name );
	pyassert( var );
	res = PyObject_CallFunction( variableref, "N", var );
	push(res);
    }

    void visitSort( SortNode* node )
    {
	PyObject *res;
	res = PyObject_CallFunction( sort, "" );

	addChildren( res, node->get_children() );

	push(res);
    }

    void visitSortTerm( SortTermNode* node )
    {
	PyObject *res, *expr;
	
	node->expr->visit( this );
	expr = pop();
	pyassert(expr);
	res = PyObject_CallFunction( sortterm, "Oi", expr, node->ordering );
	push(res);
    }

    void visitGroup( GroupNode* node )
    {
	PyObject *res;
	res = PyObject_CallFunction( group, "" );
	addChildren( res, node->get_children() );
	push(res);
    }
    
    virtual void defaultVisit( RQLNode* node )
    {
	throw pyrqlerror(std::string(typeid(*node).name()) + ": Unexpected node");
    }
    

    PyObject* get_var( const std::string& name )
    {
	PyObject* res;
	res = PyObject_CallMethod( pystmt, "get_variable", "s", name.c_str() );
	if (!res) {
	    throw pyexception();
	}
	return res;
    }

    PyObject* pop()
    {
	PyObject *top;
	if (stack.size()==0) {
	    throw pyrqlerror("Empty stack");
	}
	top = stack.back();
	stack.pop_back();
	return top;
    }

    void push( PyObject* obj )
    {
	pyassert( obj );
	stack.push_back( obj );
    }

public:
    void setup_types( PyObject* classes ) throw(pyrqlerror)
    {
	constant = get_object( classes, "Constant" );
	function = get_object( classes, "Function" );
	relation = get_object( classes, "Relation" );
	comparison = get_object( classes, "Comparison" );
	and_ = get_object( classes, "AND" );
	or_ = get_object( classes, "OR" );
	variableref = get_object( classes, "VariableRef" );
	insert = get_object( classes, "Insert" );
	select = get_object( classes, "Select" );
	delete_ = get_object( classes, "Delete" );
	update = get_object( classes, "Update" );
	mathexpression = get_object( classes, "MathExpression" );
	sort = get_object( classes, "Sort" );
	sortterm = get_object( classes, "SortTerm" );
	PyExc_BadRQLQuery = get_object( classes, "BadRQLQuery" );
	PyExc_RQLSyntaxError = get_object( classes, "RQLSyntaxError" );
	group = get_object( classes, "Group" );
    }

    PyObject* PyExc_RQLSyntaxError;
    PyObject* PyExc_BadRQLQuery;

protected:
    PyObject* get_object( PyObject* classes, const char* name ) throw(pyrqlerror)
    {
	PyObject* itm;
	static const std::string err = "Need a factory for ";
	itm = PyDict_GetItemString( classes, name );
	if (!itm) throw pyrqlerror( err + name );
	return itm;
    }
	
    std::list<PyObject*> stack;
    PyObject* constant;
    PyObject* function;
    PyObject* variableref;
    PyObject* relation;
    PyObject* comparison;
    PyObject* and_;
    PyObject* or_;
    PyObject* select;
    PyObject* delete_;
    PyObject* insert;
    PyObject* update;
    PyObject* mathexpression;
    PyObject* sort;
    PyObject* sortterm;
    PyObject* group;

    // the type dictionary
    PyObject* e_types;
    PyObject* pystmt;
    StmtNode* statement;
};


static void set_available_types( TypeDict* types, PyObject* dict )
{
    PyObject* keys;
    PyObject* name;
    char* str;
    int i,len;

    keys = PyMapping_Keys(dict);
    len = PyList_Size(keys);
    for(i=0;i<len;++i) {
	name = PyList_GetItem(keys,i);
	str = PyString_AsString( name );
	types->add_type( str );
    }
    Py_DECREF(keys);
}

static PyObject* rql_parse( PyObject* self, PyObject* args )
{
    PyObject *e_types=Py_None;
    PyObject *classes;
    PyObject *result;
    TypeDict *types = 0;
    StmtNode *goal;
    int errors=false;
    char *str;
    int  nstr;

    if (!PyArg_ParseTuple( args, "s#O|Oi", &str, &nstr, &classes, &e_types, &errors ))
    {
	return NULL;
    }
    if (!PyDict_Check(classes)) {
	PyErr_SetString( PyExc_TypeError, "Expected a dictionnary" );
	return NULL;
    }

    if (e_types != Py_None) {
	if (!PyDict_Check(e_types)) {
	    PyErr_SetString( PyExc_TypeError, "Expected a dictionnary or None for e_types" );
	    return NULL;
	}
	types = new TypeDict();
	set_available_types( types, e_types );
    }
    PyRQLVisitor builder(e_types);

    try {
	builder.setup_types( classes );
    } catch( pyrqlerror& exc ) {
	PyErr_SetString( PyExc_RuntimeError, exc.what() );
	return NULL;
    }
    std::istringstream istr( std::string( str, nstr ) );
    RqlParser s( &istr );

    try {
	goal = s.Goal( types );
    } catch( ScanException& exc ) {
	PyErr_SetString( builder.PyExc_RQLSyntaxError, std::string(exc).c_str() );	
	return NULL;
    }
    catch( UnknownTypeException& exc ) {
	PyErr_SetString( builder.PyExc_BadRQLQuery, std::string(exc).c_str() );
	return NULL;
    }
    catch( ParseException& exc ) {
	PyErr_SetString( builder.PyExc_RQLSyntaxError, std::string(exc).c_str() );
	return NULL;
    }
    if (errors>2) {
	std::cout << *goal << std::endl;
	DisplayVisitor disp( std::cout );
	goal->visit( &disp );
	std::cout << std::endl;
    }

    try {
	goal->visit( &builder );
	result = builder.pop();
    } catch( pyrqlerror& exc ) {
	PyErr_SetString( PyExc_RuntimeError, exc.what() );
	result = NULL;
    }
    catch( pyexception& exc ) {
	result = NULL;
    }
    delete goal;
    return result;
}

static PyMethodDef methods[] = {
    { "parse", rql_parse, METH_VARARGS, "parse(str,classes,[etypes]) parses a RQL command and generate a python tree using classes in classes" },
    { NULL, NULL, 0, NULL }
};

extern "C" {
void initrqlparse(void)
{
    PyObject* module;

    module = Py_InitModule("rqlparse", methods);
    
}
}
