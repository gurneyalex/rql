

#include <Python.h>
#include <boost/python.hpp>
#include <string>
#include <sstream>
#include <iostream>
#include <list>
#include <exception>
#include "rql_parser.hh"
#include "nodes.hh"
using namespace boost::python;
using namespace cppcc;

static void translate_scan( const cppcc::ScanException& exc )
{
	PyErr_SetString( PyExc_RuntimeError, exc.what() );	
}
static void translate_parse( const cppcc::ParseException& exc )
{
	PyErr_SetString( PyExc_RuntimeError, exc.what() );	
}

void my_set_types( RQLExpression& expr, dict d )
{
    TypeDict td;
    object keys = d.keys();
    int len = extract<int>(keys.attr("__len__")() );
    for(int i=0;i<len;++i) {
	td.add_type( extract<const char*>(keys[i]) );
    }
    expr.set_types( td );
}

BOOST_PYTHON_MODULE(rqlparser)
{


    class_<RQLNode>("Node")
	.def("get_children",&RQLNode::get_children, return_internal_reference<1>() )
	.def("append", &RQLNode::append )
	.def("visit", &RQLNode::visit )
	;
    class_< nodes_list_t >("NodeList")
	.def("__iter__", iterator< nodes_list_t >());

    class_<RQLVisitor>("RQLVisitor") ;
    class_<BinaryOp, bases<RQLNode> >("BinaryOp", no_init);
    class_<ExprNode, bases<RQLNode> >("ExprNode", no_init);
    class_<VarNode, bases<RQLNode> >("VarNode", no_init )
	.add_property("name", make_function( &VarNode::getname, return_value_policy<copy_const_reference>() ) )
	;

    class_<StmtNode,bases<RQLNode> >("stmt", no_init)
	.def("add_main_variable", &StmtNode::add_main_variable )
	.def("add_main_relation", &StmtNode::add_main_relation )
	.def("get_variable", &StmtNode::get_variable, return_internal_reference<1>() )
	.def("get_type", &StmtNode::get_type, return_internal_reference<1>() )
	
	;

    register_exception_translator<cppcc::ScanException>(&translate_scan);
    register_exception_translator<cppcc::ParseException>(&translate_parse);
    
    class_<RQLExpression>("RQLExpression")
	.def("parse",(int (RQLExpression::*)(const std::string&))&RQLExpression::parse )
	.def("root", &RQLExpression::RootNode, return_internal_reference<1>() )
	.def("set_types", my_set_types )
	.def("show_types", &RQLExpression::show_types )
	;

}
