"""interfaces used by the rql package

 Copyright (c) 2003-2004 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""


from logilab.common.interface import Interface

class ISchema(Interface):
    """RQL expects some base types to exists: String, Float, Int, Boolean, Date
    and a base relation : is
    """
    
    def has_entity(self, etype):
        """return true if the given type is defined in the schema
        """
        
    def has_relation(self, rtype):
        """return true if the given relation's type is defined in the schema
        """
    
    def entities(self, schema=None):
        """return the list of possible types
        
        If schema is not None, return a list of schemas instead of types.
        """

    def relations(self, schema=None):
        """return the list of possible relations
        
        If schema is not None, return a list of schemas instead of relation's
        types.
        """

    def relation_schema(self, rtype):
        """return the relation schema for the given relation type
        """
        

class IRelationSchema(Interface):
    """interface for Relation schema (a relation is a named oriented link
    between two entities)
    """
    def associations(self):
        """return a list of (fromtype, [totypes]) defining between which types
        this relation may exists
        """
        
    def subjects(self):
        """return a list of types which can be subject of this relation
        """
        
    def objects(self):
        """return a list of types which can be object of this relation
        """

class IEntitySchema(Interface):
    """interface for Entity schema
    """
    
    def is_final(self):
        """return true if the entity is a final entity (ie cannot be used
        as subject of a relation)
        """
        
