"""
 Copyright (c) 2000-2003 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr

 defines exception used in the rql package
"""

__revision__ = "$Id: _exceptions.py,v 1.2 2003-11-24 15:30:52 syt Exp $"

class RQLException(Exception):
    """base exception for exceptions of the rql module"""


class MissingType(RQLException):
    """raised when there is some expected type missing from a schema"""

class UsesReservedWord(RQLException):
    """raised when the schema uses a reserved word as type or relation"""

class RQLSyntaxError(RQLException):
    """raised when there is a syntax error in the rql string"""

class TypeResolverException(RQLException):
    """raised when we are unable to guess variables'type"""

class BadRQLQuery(RQLException):
    """raised when there is a no sense in the rql query"""
