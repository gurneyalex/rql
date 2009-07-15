"""Exceptions used in the RQL package.

:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

class RQLException(Exception):
    """Base exception for exceptions of the rql module."""

class MissingType(RQLException):
    """Raised when there is some expected type missing from a schema."""

class UsesReservedWord(RQLException):
    """Raised when the schema uses a reserved word as type or relation."""

class RQLSyntaxError(RQLException):
    """Raised when there is a syntax error in the rql string."""

class TypeResolverException(RQLException):
    """Raised when we are unable to guess variables' type."""

class BadRQLQuery(RQLException):
    """Raised when there is a no sense in the rql query."""

class CoercionError(RQLException):
    """Failed to infer type of a math expression."""
