/* -*- mode:c++ -*- */

#ifndef __NODE_EXCEPTIONS_HH__
#define __NODE_EXCEPTIONS_HH__

#include "rql_parser.hh"

class UnknownTypeException : public cppcc::ParseException
{
  public:
    
    UnknownTypeException (const std::string &type_ ) :
      message("Unknown type:")
    {
	message += type_;
    }
    
    ~UnknownTypeException () throw ()
    {}
    
    virtual operator std::string () const
    {
      return message;
    }
    
    virtual const char* what () throw ()
    {
      return message.c_str();
    }
    
  private:
  
    std::string message;
};

#endif
