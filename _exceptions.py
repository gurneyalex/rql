"""
 Copyright (c) 2004-2007 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr

 defines exception used in the rql package
"""

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
