"""base classes for rql syntax tree nodes

NOTE: used of __slots__ since applications may create a large number of nodes
      and we want this (an memory usage) as cheapiest as possible
      
:organization: Logilab
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

class BaseNode(object):
    __slots__ = ('parent',)
    
    def __str__(self):
        return self.as_string(encoding='utf-8')

    def initargs(self, stmt):
        """return list of arguments to give to __init__ to clone this node

        I don't use __getinitargs__ because I'm not sure it should interfer with
        copy/pickle
        """
        return ()
    
    def root(self):
        """return the root node of the tree"""
        return self.parent.root()

    def exists_root(self):
        return self.parent.exists_root()

    def scope(self):
        return self.parent.scope

    def get_nodes(self, klass):
        """return the list of nodes of a given class in the subtree

        :type klass: a node class (Relation, Constant, etc.)
        :param klass: the class of nodes to return
        """
        stack = [self]
        result = []
        while stack:
            node = stack.pop()
            if isinstance(node, klass):
                result.append(node)
            else:
                stack += node.children
        return result

    def iget_nodes(self, klass):
        """return an iterator over nodes of a given class in the subtree

        :type klass: a node class (Relation, Constant, etc.)
        :param klass: the class of nodes to return
        """
        stack = [self]
        while stack:
            node = stack.pop()
            if isinstance(node, klass):
                yield node
            else:
                stack += node.children

    def is_equivalent(self, other):
        if not other.__class__ is self.__class__:
            return False
        for i, child in enumerate(self.children):
            try:
                if not child.is_equivalent(other.children[i]):
                    return False
            except IndexError:
                return False
        return True
    
    
class Node(BaseNode):
    """class for nodes of the tree which may have children (almost all...)"""
    __slots__ = ('children',)
    
    def __init__(self) :
        self.parent = None
        self.children = []
    
    def append(self, child):
        """add a node to children"""
        self.children.append(child)
        child.parent = self

    def remove(self, child):
        """remove a child node"""
        self.children.remove(child)
        child.parent = None

    def insert(self, index, child):
        """insert a child node"""
        self.children.insert(index, child)
        child.parent = self
        
    def replace(self, old_child, new_child):
        """replace a child node with another"""
        i = self.children.index(old_child)
        self.children.pop(i)
        self.children.insert(i, new_child)
        new_child.parent = self
    
    def copy(self, stmt):
        """create and return a copy of this node and its descendant

        stmt is the root node, which should be use to get new variables
        """
        new = self.__class__(*self.initargs(stmt))
        for child in self.children:
            new.append(child.copy(stmt))
        return new

class BinaryNode(Node):
    __slots__ = ()
    
    def __init__(self, lhs=None, rhs=None):
        Node.__init__(self)
        if not lhs is None:
            self.append(lhs)
        if not rhs is None:
            self.append(rhs)
            
    def remove(self, child):
        """remove the child and replace this node with the other child
        """
        self.children.remove(child)
        self.parent.replace(self, self.children[0])

    def get_parts(self):
        """
        return the left hand side and the right hand side of this node
        """
        return self.children[0], self.children[1]


class LeafNode(BaseNode):
    """class optimized for leaf nodes"""
    __slots__ = ()

    @property
    def children(self):
        return ()
    
    def copy(self, stmt):
        """create and return a copy of this node and its descendant

        stmt is the root node, which should be use to get new variables
        """
        return self.__class__(*self.initargs(stmt))
    
    
