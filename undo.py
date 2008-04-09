"""manages undos on rql syntax trees


:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from rql.nodes import VariableRef, Variable, BinaryNode

class SelectionManager:
    """manage the operation stacks"""
    
    def __init__(self, selection):
        self._selection = selection # The selection tree
        self.op_list = []           # The operations we'll have to undo
        self.state_stack = []       # The save_state()'s index stack
    
    def push_state(self):
        """defines current state as the new 'start' state"""
        self.state_stack.append(len(self.op_list))
        
    def recover(self):
        """recover to the latest pushed state"""
        last_state_index = self.state_stack.pop()
        # if last_index == 0, then there's no intermediate state => undo all !
        for i in self.op_list[:-last_state_index] or self.op_list[:]:
            self.undo()
    
    def add_operation(self, operation):
        """add an operation to the current ones"""
        # stores operations in reverse order :
        self.op_list.insert(0, operation)
        
    def undo(self):
        """undo the latest operation"""
        assert len(self.op_list) > 0
        op = self.op_list.pop(0)
        self._selection.undoing = 1
        op.undo(self._selection)
        self._selection.undoing = 0

    def flush(self):
        """flush the current operations"""
        self.op_list = []

class NodeOperation:
    """abstract class for node manipulation operations"""
    def __init__(self, node):
        self.node = node
        if isinstance(node, Variable):
            self.root = node.stmt
        else:
            self.root = node.root()
        
    def __str__(self):
        """undo the operation on the selection"""
        return "%s %s" % (self.__class__.__name__, self.node)    

# Undo for variable manipulation operations  ##################################
        
class MakeVarOperation(NodeOperation):
    """defines how to undo make_variable"""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.root.undefine_variable(self.node)

class UndefineVarOperation(NodeOperation):
    """defines how to undo 'undefine_variable()'"""

    def undo(self, selection):
        """undo the operation on the selection"""
        var = self.node
        self.root.defined_vars[var.name] = var

class SelectVarOperation(NodeOperation):
    """defines how to undo add_selected()"""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.root.remove_selected(self.node)

class UnselectVarOperation(NodeOperation):
    """defines how to undo 'unselect_var()'"""
    def __init__(self, var, pos):
        NodeOperation.__init__(self, var)
        self.index = pos

    def undo(self, selection):
        """undo the operation on the selection"""
        self.root.add_selected(self.node, self.index)


# Undo for node operations ####################################################

class AddNodeOperation(NodeOperation):
    """defines how to undo 'add node'"""   

    def undo(self, selection):
        """undo the operation on the selection"""
        selection.remove_node(self.node)

class ReplaceNodeOperation:
    """defines how to undo 'replace node'"""
    def __init__(self, old_node, new_node):
        self.old_node = old_node
        self.new_node = new_node

    def undo(self, selection):
        """undo the operation on the selection"""
        # unregister reference from the inserted node
        for varref in self.new_node.iget_nodes(VariableRef):
            varref.unregister_reference()
        # register reference from the removed node
        for varref in self.old_node.iget_nodes(VariableRef):
            varref.register_reference()
        self.new_node.parent.replace(self.new_node, self.old_node)

    def __str__(self):
        return "ReplaceNodeOperation %s by %s" % (self.old_node, self.new_node)

class RemoveNodeOperation(NodeOperation):
    """defines how to undo remove_node()"""
    
    def __init__(self, node):
        NodeOperation.__init__(self, node)
        self.node_parent = node.parent
        self.index = node.parent.children.index(node)
        # XXX FIXME : find a better way to do that
        # needed when removing a BinaryNode's child
        self.binary_remove = isinstance(self.node_parent, BinaryNode)
        if self.binary_remove:
            self.gd_parent = self.node_parent.parent
            self.parent_index = self.gd_parent.children.index(self.node_parent)
            
    def undo(self, selection):
        """undo the operation on the selection"""
        if self.binary_remove:
            # if 'parent' was a BinaryNode, then first reinsert the removed node
            # at the same pos in the original 'parent' Binary Node, and then
            # reinsert this BinaryNode in its parent's children list
            # WARNING : the removed node sibling's parent is no longer the
            # 'node_parent'. We must Reparent it manually !
            node_sibling = self.node_parent.children[0]
            node_sibling.parent = self.node_parent
            self.node_parent.insert(self.index, self.node) 
            self.gd_parent.children[self.parent_index] = self.node_parent
        else:
            self.node_parent.insert(self.index, self.node)
        # register reference from the removed node
        for varref in self.node.iget_nodes(VariableRef):
            varref.register_reference()
    
class AddSortOperation(NodeOperation):
    """defines how to undo 'add sort'"""

    def undo(self, selection):
        """undo the operation on the selection"""
        selection.remove_sort_term(self.node)
    
class RemoveSortOperation(NodeOperation):
    """defines how to undo 'add sort'"""

    def undo(self, selection):
        """undo the operation on the selection"""
        selection.add_sort_term(self.node)
    
class AddGroupOperation(NodeOperation):
    """defines how to undo 'add group'"""

    def undo(self, selection):
        """undo the operation on the selection"""
        selection.remove_group_variable(self.node)

# misc operations #############################################################

class ChangeValueOperation:    
    def __init__(self, previous_value):
        self.value = previous_value

class SetDistinctOperation(ChangeValueOperation):
    """defines how to undo 'set_distinct'"""
        
    def undo(self, selection):
        """undo the operation on the selection"""
        selection.distinct = self.value

class SetOffsetOperation(ChangeValueOperation):
    """defines how to undo 'set_offset'"""
        
    def undo(self, selection):
        """undo the operation on the selection"""
        selection.offset = self.value

class SetLimitOperation(ChangeValueOperation):
    """defines how to undo 'set_limit'"""
        
    def undo(self, selection):
        """undo the operation on the selection"""
        selection.limit = self.value

class ChangeOptionalOperation(ChangeValueOperation):
    """defines how to undo 'set_optional'"""
        
    def undo(self, selection):
        """undo the operation on the selection"""
        selection.offset = self.value

class SetOptionalOperation(ChangeValueOperation):
    """defines how to undo 'set_limit'"""
    def __init__(self, rel, previous_value):
        self.rel = rel
        self.value = previous_value
        
    def undo(self, selection):
        """undo the operation on the selection"""
        self.rel.optional = self.value
    
__all__ = ('SelectionManager', 'MakeVarOperation', 'UndefineVarOperation',
           'SelectVarOperation', 'UnselectVarOperation', 'AddNodeOperation',
           'ReplaceNodeOperation', 'RemoveNodeOperation', 
           'AddSortOperation', 'AddGroupOperation',
           'SetOptionalOperation', 'SetDistinctOperation')
