"""Manages undos on RQL syntax trees.

:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from rql.nodes import VariableRef, Variable, BinaryNode
from rql.stmts import Select

class SelectionManager(object):
    """Manage the operation stacks."""

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

class NodeOperation(object):
    """Abstract class for node manipulation operations."""
    def __init__(self, node):
        self.node = node
        self.stmt = node.stmt

    def __str__(self):
        """undo the operation on the selection"""
        return "%s %s" % (self.__class__.__name__, self.node)

# Undo for variable manipulation operations  ##################################

class MakeVarOperation(NodeOperation):
    """Defines how to undo make_variable()."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.undefine_variable(self.node)

class UndefineVarOperation(NodeOperation):
    """Defines how to undo undefine_variable()."""

    def undo(self, selection):
        """undo the operation on the selection"""
        var = self.node
        self.stmt.defined_vars[var.name] = var

class SelectVarOperation(NodeOperation):
    """Defines how to undo add_selected()."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.remove_selected(self.node)

class UnselectVarOperation(NodeOperation):
    """Defines how to undo unselect_var()."""
    def __init__(self, var, pos):
        NodeOperation.__init__(self, var)
        self.index = pos

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.add_selected(self.node, self.index)


# Undo for node operations ####################################################

class AddNodeOperation(NodeOperation):
    """Defines how to undo add_node()."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.remove_node(self.node)

class ReplaceNodeOperation(object):
    """Defines how to undo 'replace node'."""
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
    """Defines how to undo remove_node()."""

    def __init__(self, node):
        NodeOperation.__init__(self, node)
        self.node_parent = node.parent
        if isinstance(self.node_parent, Select):
            assert self.node is self.node_parent.where
        else:
            self.index = node.parent.children.index(node)
        # XXX FIXME : find a better way to do that
        # needed when removing a BinaryNode's child
        self.binary_remove = isinstance(self.node_parent, BinaryNode)
        if self.binary_remove:
            self.gd_parent = self.node_parent.parent
            if isinstance(self.gd_parent, Select):
                assert self.node_parent is self.gd_parent.where
            else:
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
            if isinstance(self.gd_parent, Select):
                self.gd_parent.where = self.node_parent
            else:
                self.gd_parent.children[self.parent_index] = self.node_parent
                self.node_parent.parent = self.gd_parent
        elif isinstance(self.node_parent, Select):
            self.node_parent.where = self.node
            self.node.parent = self.node_parent
        else:
            self.node_parent.insert(self.index, self.node)
        # register reference from the removed node
        for varref in self.node.iget_nodes(VariableRef):
            varref.register_reference()

class AddSortOperation(NodeOperation):
    """Defines how to undo 'add sort'."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.remove_sort_term(self.node)

class RemoveSortOperation(NodeOperation):
    """Defines how to undo 'remove sort'."""
    def __init__(self, node):
        NodeOperation.__init__(self, node)
        self.index = self.stmt.orderby.index(self.node)

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.add_sort_term(self.node, self.index)

class AddGroupOperation(NodeOperation):
    """Defines how to undo 'add group'."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.remove_group_var(self.node)

class RemoveGroupOperation(NodeOperation):
    """Defines how to undo 'remove group'."""

    def __init__(self, node):
        NodeOperation.__init__(self, node)
        self.index = self.stmt.groupby.index(self.node)

    def undo(self, selection):
        """undo the operation on the selection"""
        self.stmt.add_group_var(self.node, self.index)

# misc operations #############################################################

class ChangeValueOperation(object):
    def __init__(self, previous_value, node=None):
        self.value = previous_value
        self.node = node

class SetDistinctOperation(ChangeValueOperation):
    """Defines how to undo 'set_distinct'."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.node.distinct = self.value

class SetOffsetOperation(ChangeValueOperation):
    """Defines how to undo 'set_offset'."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.node.offset = self.value

class SetLimitOperation(ChangeValueOperation):
    """Defines how to undo 'set_limit'."""

    def undo(self, selection):
        """undo the operation on the selection"""
        self.node.limit = self.value

class SetOptionalOperation(ChangeValueOperation):
    """Defines how to undo 'set_limit'."""
    def __init__(self, rel, previous_value):
        self.rel = rel
        self.value = previous_value

    def undo(self, selection):
        """undo the operation on the selection"""
        self.rel.optional = self.value

# Union operations ############################################################

class AppendSelectOperation(object):
    """Defines how to undo append_select()."""
    def __init__(self, union, select):
        self.union = union
        self.select = select

    def undo(self, selection):
        """undo the operation on the union's children"""
        self.select.parent = self.union
        self.union.children.remove(self.select)

class RemoveSelectOperation(AppendSelectOperation):
    """Defines how to undo append_select()."""
    def __init__(self, union, select, origindex):
        AppendSelectOperation.__init__(self, union, select)
        self.origindex = origindex

    def undo(self, selection):
        """undo the operation on the union's children"""
        self.union.insert(self.origindex, self.select)

__all__ = ('SelectionManager', 'MakeVarOperation', 'UndefineVarOperation',
           'SelectVarOperation', 'UnselectVarOperation', 'AddNodeOperation',
           'ReplaceNodeOperation', 'RemoveNodeOperation',
           'AddSortOperation', 'AddGroupOperation',
           'SetOptionalOperation', 'SetDistinctOperation')
