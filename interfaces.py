"""Interfaces used by the RQL package.

:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from logilab.common.interface import Interface

class ISchema(Interface):
    """RQL expects some base types to exists: String, Float, Int, Boolean, Date
    and a base relation : is
    """

    def has_entity(self, etype):
        """Return true if the given type is defined in the schema.
        """

    def has_relation(self, rtype):
        """Return true if the given relation's type is defined in the schema.
        """

    def entities(self, schema=None):
        """Return the list of possible types.

        If schema is not None, return a list of schemas instead of types.
        """

    def relations(self, schema=None):
        """Return the list of possible relations.

        If schema is not None, return a list of schemas instead of relation's
        types.
        """

    def relation_schema(self, rtype):
        """Return the relation schema for the given relation type.
        """


class IRelationSchema(Interface):
    """Interface for Relation schema (a relation is a named oriented link
    between two entities).
    """

    def associations(self):
        """Return a list of (fromtype, [totypes]) defining between which types
        this relation may exists.
        """

    def subjects(self):
        """Return a list of types which can be subject of this relation.
        """

    def objects(self):
        """Return a list of types which can be object of this relation.
        """

class IEntitySchema(Interface):
    """Interface for Entity schema."""

    def is_final(self):
        """Return true if the entity is a final entity (ie cannot be used
        as subject of a relation).
        """

