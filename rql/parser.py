"""yapps input grammar for RQL.

:organization: Logilab
:copyright: 2003-2011 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr


Select statement grammar
------------------------

query = <squery> | <union>

union = (<squery>) UNION (<squery>) [UNION (<squery>)]*

squery = Any <selection>
        [GROUPBY <variables>]
        [ORDERBY <sortterms>]
        [LIMIT <nb> OFFSET <nb>]
        [WHERE <restriction>]
        [HAVING <aggregat restriction>]
        [WITH <subquery> [,<subquery]*]

subquery = <variables> BEING (<query>)

variables = <variable> [, <variable>]*


Abbreviations in this code
--------------------------

rules:
* rel -> relation
* decl -> declaration
* expr -> expression
* restr -> restriction
* var -> variable
* func -> function
* const -> constant
* cmp -> comparison

variables:
* R -> syntax tree root
* S -> select node
* P -> parent node

"""

# Begin -- grammar generated by Yapps
from __future__ import print_function
import sys, re
from yapps import runtime

class HerculeScanner(runtime.Scanner):
    patterns = [
        ("'IN'", re.compile('IN')),
        ("','", re.compile(',')),
        ('r"\\)"', re.compile('\\)')),
        ('r"\\("', re.compile('\\(')),
        ('":"', re.compile(':')),
        ("';'", re.compile(';')),
        ('\\s+', re.compile('\\s+')),
        ('/\\*(?:[^*]|\\*(?!/))*\\*/', re.compile('/\\*(?:[^*]|\\*(?!/))*\\*/')),
        ('DELETE', re.compile('(?i)DELETE')),
        ('SET', re.compile('(?i)SET')),
        ('INSERT', re.compile('(?i)INSERT')),
        ('UNION', re.compile('(?i)UNION')),
        ('DISTINCT', re.compile('(?i)DISTINCT')),
        ('WITH', re.compile('(?i)WITH')),
        ('WHERE', re.compile('(?i)WHERE')),
        ('BEING', re.compile('(?i)BEING')),
        ('OR', re.compile('(?i)OR')),
        ('AND', re.compile('(?i)AND')),
        ('NOT', re.compile('(?i)NOT')),
        ('GROUPBY', re.compile('(?i)GROUPBY')),
        ('HAVING', re.compile('(?i)HAVING')),
        ('ORDERBY', re.compile('(?i)ORDERBY')),
        ('SORT_ASC', re.compile('(?i)ASC')),
        ('SORT_DESC', re.compile('(?i)DESC')),
        ('LIMIT', re.compile('(?i)LIMIT')),
        ('OFFSET', re.compile('(?i)OFFSET')),
        ('DATE', re.compile('(?i)TODAY')),
        ('DATETIME', re.compile('(?i)NOW')),
        ('TRUE', re.compile('(?i)TRUE')),
        ('FALSE', re.compile('(?i)FALSE')),
        ('NULL', re.compile('(?i)NULL')),
        ('EXISTS', re.compile('(?i)EXISTS')),
        ('CMP_OP', re.compile('(?i)<=|<|>=|>|!=|=|~=|LIKE|ILIKE|REGEXP')),
        ('ADD_OP', re.compile('\\+|-|\\||#')),
        ('MUL_OP', re.compile('\\*|/|%|&')),
        ('POW_OP', re.compile('\\^|>>|<<')),
        ('UNARY_OP', re.compile('-|~')),
        ('FUNCTION', re.compile('[A-Za-z_]+\\s*(?=\\()')),
        ('R_TYPE', re.compile('[a-z_][a-z0-9_]*')),
        ('E_TYPE', re.compile('[A-Z][A-Za-z0-9]*[a-z]+[A-Z0-9]*')),
        ('VARIABLE', re.compile('[A-Z][A-Z0-9_]*')),
        ('COLALIAS', re.compile('[A-Z][A-Z0-9_]*\\.\\d+')),
        ('QMARK', re.compile('\\?')),
        ('STRING', re.compile('\'([^\\\'\\\\]|\\\\.)*\'|\\"([^\\\\\\"\\\\]|\\\\.)*\\"')),
        ('FLOAT', re.compile('-?\\d+\\.\\d*')),
        ('INT', re.compile('-?\\d+')),
        ('SUBSTITUTE', re.compile('%\\([A-Za-z_0-9]+\\)s')),
    ]
    def __init__(self, str,*args,**kw):
        runtime.Scanner.__init__(self,None,{'\\s+':None,'/\\*(?:[^*]|\\*(?!/))*\\*/':None,},str,*args,**kw)

class Hercule(runtime.Parser):
    Context = runtime.Context
    def goal(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'goal', [])
        _token = self._peek('DELETE', 'INSERT', 'SET', 'r"\\("', 'DISTINCT', 'E_TYPE', context=_context)
        if _token == 'DELETE':
            DELETE = self._scan('DELETE', context=_context)
            _delete = self._delete(Delete(), _context)
            self._scan("';'", context=_context)
            return _delete
        elif _token == 'INSERT':
            INSERT = self._scan('INSERT', context=_context)
            _insert = self._insert(Insert(), _context)
            self._scan("';'", context=_context)
            return _insert
        elif _token == 'SET':
            SET = self._scan('SET', context=_context)
            update = self.update(Set(), _context)
            self._scan("';'", context=_context)
            return update
        else: # in ['r"\\("', 'DISTINCT', 'E_TYPE']
            union = self.union(Union(), _context)
            self._scan("';'", context=_context)
            return union

    def _delete(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, '_delete', [R])
        _token = self._peek('E_TYPE', 'VARIABLE', context=_context)
        if _token == 'VARIABLE':
            decl_rels = self.decl_rels(R, _context)
            where = self.where(R, _context)
            having = self.having(R, _context)
            return R
        else: # == 'E_TYPE'
            decl_vars = self.decl_vars(R, _context)
            where = self.where(R, _context)
            having = self.having(R, _context)
            return R

    def _insert(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, '_insert', [R])
        decl_vars = self.decl_vars(R, _context)
        insert_rels = self.insert_rels(R, _context)
        return R

    def insert_rels(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'insert_rels', [R])
        _token = self._peek('":"', "';'", context=_context)
        if _token == '":"':
            self._scan('":"', context=_context)
            decl_rels = self.decl_rels(R, _context)
            where = self.where(R, _context)
            having = self.having(R, _context)
            return R
        else: # == "';'"
            pass

    def update(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'update', [R])
        decl_rels = self.decl_rels(R, _context)
        where = self.where(R, _context)
        having = self.having(R, _context)
        return R

    def union(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'union', [R])
        _token = self._peek('r"\\("', 'DISTINCT', 'E_TYPE', context=_context)
        if _token != 'r"\\("':
            select = self.select(Select(), _context)
            R.append(select); return R
        else: # == 'r"\\("'
            self._scan('r"\\("', context=_context)
            select = self.select(Select(), _context)
            self._scan('r"\\)"', context=_context)
            R.append(select)
            while self._peek('UNION', "';'", 'r"\\)"', context=_context) == 'UNION':
                UNION = self._scan('UNION', context=_context)
                self._scan('r"\\("', context=_context)
                select = self.select(Select(), _context)
                self._scan('r"\\)"', context=_context)
                R.append(select)
            return R

    def select(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'select', [S])
        _token = self._peek('DISTINCT', 'E_TYPE', context=_context)
        if _token == 'DISTINCT':
            DISTINCT = self._scan('DISTINCT', context=_context)
            select_ = self.select_(S, _context)
            S.distinct = True ; return S
        else: # == 'E_TYPE'
            select_ = self.select_(S, _context)
            return S

    def select_(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'select_', [S])
        E_TYPE = self._scan('E_TYPE', context=_context)
        selection = self.selection(S, _context)
        groupby = self.groupby(S, _context)
        orderby = self.orderby(S, _context)
        limit_offset = self.limit_offset(S, _context)
        where = self.where(S, _context)
        having = self.having(S, _context)
        with_ = self.with_(S, _context)
        S.set_statement_type(E_TYPE); return S

    def selection(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'selection', [S])
        expr_add = self.expr_add(S, _context)
        S.append_selected(expr_add)
        while self._peek("','", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context) == "','":
            self._scan("','", context=_context)
            expr_add = self.expr_add(S, _context)
            S.append_selected(expr_add)

    def groupby(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'groupby', [S])
        _token = self._peek('GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'GROUPBY':
            GROUPBY = self._scan('GROUPBY', context=_context)
            nodes = []
            expr_add = self.expr_add(S, _context)
            nodes.append(expr_add)
            while self._peek("','", 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context) == "','":
                self._scan("','", context=_context)
                expr_add = self.expr_add(S, _context)
                nodes.append(expr_add)
            S.set_groupby(nodes); return True
        else:
            pass

    def having(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'having', [S])
        _token = self._peek('HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'HAVING':
            HAVING = self._scan('HAVING', context=_context)
            logical_expr = self.logical_expr(S, _context)
            S.set_having([logical_expr])
        else: # in ['WITH', "';'", 'r"\\)"']
            pass

    def orderby(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'orderby', [S])
        _token = self._peek('ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'ORDERBY':
            ORDERBY = self._scan('ORDERBY', context=_context)
            nodes = []
            sort_term = self.sort_term(S, _context)
            nodes.append(sort_term)
            while self._peek("','", 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context) == "','":
                self._scan("','", context=_context)
                sort_term = self.sort_term(S, _context)
                nodes.append(sort_term)
            S.set_orderby(nodes); return True
        else:
            pass

    def with_(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'with_', [S])
        _token = self._peek('WITH', 'r"\\)"', "';'", context=_context)
        if _token == 'WITH':
            WITH = self._scan('WITH', context=_context)
            nodes = []
            subquery = self.subquery(S, _context)
            nodes.append(subquery)
            while self._peek("','", 'r"\\)"', "';'", context=_context) == "','":
                self._scan("','", context=_context)
                subquery = self.subquery(S, _context)
                nodes.append(subquery)
            S.set_with(nodes)
        else: # in ['r"\\)"', "';'"]
            pass

    def subquery(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'subquery', [S])
        variables = self.variables(S, _context)
        node = SubQuery() ; node.set_aliases(variables)
        BEING = self._scan('BEING', context=_context)
        self._scan('r"\\("', context=_context)
        union = self.union(Union(), _context)
        self._scan('r"\\)"', context=_context)
        node.set_query(union); return node

    def sort_term(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'sort_term', [S])
        expr_add = self.expr_add(S, _context)
        sort_meth = self.sort_meth(_context)
        return SortTerm(expr_add, sort_meth)

    def sort_meth(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'sort_meth', [])
        _token = self._peek('SORT_DESC', 'SORT_ASC', "','", 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'SORT_DESC':
            SORT_DESC = self._scan('SORT_DESC', context=_context)
            return 0
        elif _token == 'SORT_ASC':
            SORT_ASC = self._scan('SORT_ASC', context=_context)
            return 1
        else:
            return 1 # default to SORT_ASC

    def limit_offset(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'limit_offset', [R])
        limit = self.limit(R, _context)
        offset = self.offset(R, _context)
        return limit or offset

    def limit(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'limit', [R])
        _token = self._peek('LIMIT', 'OFFSET', 'WHERE', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'LIMIT':
            LIMIT = self._scan('LIMIT', context=_context)
            INT = self._scan('INT', context=_context)
            R.set_limit(int(INT)); return True
        else: # in ['OFFSET', 'WHERE', 'HAVING', 'WITH', "';'", 'r"\\)"']
            pass

    def offset(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'offset', [R])
        _token = self._peek('OFFSET', 'WHERE', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'OFFSET':
            OFFSET = self._scan('OFFSET', context=_context)
            INT = self._scan('INT', context=_context)
            R.set_offset(int(INT)); return True
        else: # in ['WHERE', 'HAVING', 'WITH', "';'", 'r"\\)"']
            pass

    def where(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'where', [S])
        _token = self._peek('WHERE', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context)
        if _token == 'WHERE':
            WHERE = self._scan('WHERE', context=_context)
            restriction = self.restriction(S, _context)
            S.set_where(restriction)
        else: # in ['HAVING', 'WITH', "';'", 'r"\\)"']
            pass

    def restriction(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'restriction', [S])
        rels_or = self.rels_or(S, _context)
        node = rels_or
        while self._peek("','", 'r"\\)"', 'HAVING', 'WITH', "';'", context=_context) == "','":
            self._scan("','", context=_context)
            rels_or = self.rels_or(S, _context)
            node = And(node, rels_or)
        return node

    def rels_or(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rels_or', [S])
        rels_and = self.rels_and(S, _context)
        node = rels_and
        while self._peek('OR', "','", 'r"\\)"', 'HAVING', 'WITH', "';'", context=_context) == 'OR':
            OR = self._scan('OR', context=_context)
            rels_and = self.rels_and(S, _context)
            node = Or(node, rels_and)
        return node

    def rels_and(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rels_and', [S])
        rels_not = self.rels_not(S, _context)
        node = rels_not
        while self._peek('AND', 'OR', "','", 'r"\\)"', 'HAVING', 'WITH', "';'", context=_context) == 'AND':
            AND = self._scan('AND', context=_context)
            rels_not = self.rels_not(S, _context)
            node = And(node, rels_not)
        return node

    def rels_not(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rels_not', [S])
        _token = self._peek('NOT', 'r"\\("', 'EXISTS', 'VARIABLE', context=_context)
        if _token == 'NOT':
            NOT = self._scan('NOT', context=_context)
            rel = self.rel(S, _context)
            return Not(rel)
        else: # in ['r"\\("', 'EXISTS', 'VARIABLE']
            rel = self.rel(S, _context)
            return rel

    def rel(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rel', [S])
        _token = self._peek('r"\\("', 'EXISTS', 'VARIABLE', context=_context)
        if _token != 'r"\\("':
            rel_base = self.rel_base(S, _context)
            return rel_base
        else: # == 'r"\\("'
            self._scan('r"\\("', context=_context)
            restriction = self.restriction(S, _context)
            self._scan('r"\\)"', context=_context)
            return restriction

    def rel_base(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rel_base', [S])
        _token = self._peek('EXISTS', 'VARIABLE', context=_context)
        if _token == 'VARIABLE':
            var = self.var(S, _context)
            opt_left = self.opt_left(S, _context)
            rtype = self.rtype(_context)
            rtype.append(var) ; rtype.set_optional(opt_left)
            expr = self.expr(S, _context)
            opt_right = self.opt_right(S, _context)
            rtype.append(expr) ; rtype.set_optional(opt_right) ; return rtype
        else: # == 'EXISTS'
            EXISTS = self._scan('EXISTS', context=_context)
            self._scan('r"\\("', context=_context)
            restriction = self.restriction(S, _context)
            self._scan('r"\\)"', context=_context)
            return Exists(restriction)

    def rtype(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rtype', [])
        R_TYPE = self._scan('R_TYPE', context=_context)
        return Relation(R_TYPE)

    def opt_left(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'opt_left', [S])
        _token = self._peek('QMARK', 'R_TYPE', 'CMP_OP', "'IN'", context=_context)
        if _token == 'QMARK':
            QMARK = self._scan('QMARK', context=_context)
            return 'left'
        else: # in ['R_TYPE', 'CMP_OP', "'IN'"]
            pass

    def opt_right(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'opt_right', [S])
        _token = self._peek('QMARK', 'AND', 'OR', "','", 'r"\\)"', 'WITH', "';'", 'HAVING', context=_context)
        if _token == 'QMARK':
            QMARK = self._scan('QMARK', context=_context)
            return 'right'
        else: # in ['AND', 'OR', "','", 'r"\\)"', 'WITH', "';'", 'HAVING']
            pass

    def logical_expr(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'logical_expr', [S])
        exprs_or = self.exprs_or(S, _context)
        node = exprs_or
        while self._peek("','", 'r"\\)"', 'WITH', "';'", context=_context) == "','":
            self._scan("','", context=_context)
            exprs_or = self.exprs_or(S, _context)
            node = And(node, exprs_or)
        return node

    def exprs_or(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'exprs_or', [S])
        exprs_and = self.exprs_and(S, _context)
        node = exprs_and
        while self._peek('OR', "','", 'r"\\)"', 'WITH', "';'", context=_context) == 'OR':
            OR = self._scan('OR', context=_context)
            exprs_and = self.exprs_and(S, _context)
            node = Or(node, exprs_and)
        return node

    def exprs_and(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'exprs_and', [S])
        exprs_not = self.exprs_not(S, _context)
        node = exprs_not
        while self._peek('AND', 'OR', "','", 'r"\\)"', 'WITH', "';'", context=_context) == 'AND':
            AND = self._scan('AND', context=_context)
            exprs_not = self.exprs_not(S, _context)
            node = And(node, exprs_not)
        return node

    def exprs_not(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'exprs_not', [S])
        _token = self._peek('NOT', 'r"\\("', 'UNARY_OP', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context)
        if _token == 'NOT':
            NOT = self._scan('NOT', context=_context)
            balanced_expr = self.balanced_expr(S, _context)
            return Not(balanced_expr)
        else:
            balanced_expr = self.balanced_expr(S, _context)
            return balanced_expr

    def balanced_expr(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'balanced_expr', [S])
        _token = self._peek('r"\\("', 'UNARY_OP', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context)
        if _token == 'r"\\("':
            self._scan('r"\\("', context=_context)
            logical_expr = self.logical_expr(S, _context)
            self._scan('r"\\)"', context=_context)
            return logical_expr
        elif 1:
            expr_add = self.expr_add(S, _context)
            opt_left = self.opt_left(S, _context)
            expr_op = self.expr_op(S, _context)
            opt_right = self.opt_right(S, _context)
            expr_op.insert(0, expr_add); expr_op.set_optional(opt_left, opt_right); return expr_op
        else:
            raise runtime.SyntaxError(_token[0], 'Could not match balanced_expr')

    def expr_op(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr_op', [S])
        _token = self._peek('CMP_OP', "'IN'", context=_context)
        if _token == 'CMP_OP':
            CMP_OP = self._scan('CMP_OP', context=_context)
            expr_add = self.expr_add(S, _context)
            return Comparison(CMP_OP.upper(), expr_add)
        else: # == "'IN'"
            in_expr = self.in_expr(S, _context)
            return Comparison('=', in_expr)

    def variables(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'variables', [S])
        vars = []
        var = self.var(S, _context)
        vars.append(var)
        while self._peek("','", 'BEING', context=_context) == "','":
            self._scan("','", context=_context)
            var = self.var(S, _context)
            vars.append(var)
        return vars

    def decl_vars(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'decl_vars', [R])
        E_TYPE = self._scan('E_TYPE', context=_context)
        var = self.var(R, _context)
        while self._peek("','", 'R_TYPE', 'QMARK', 'WHERE', '":"', 'CMP_OP', 'HAVING', "'IN'", "';'", 'POW_OP', 'BEING', 'WITH', 'MUL_OP', 'r"\\)"', 'ADD_OP', 'SORT_DESC', 'SORT_ASC', 'GROUPBY', 'ORDERBY', 'LIMIT', 'OFFSET', 'AND', 'OR', context=_context) == "','":
            R.add_main_variable(E_TYPE, var)
            self._scan("','", context=_context)
            E_TYPE = self._scan('E_TYPE', context=_context)
            var = self.var(R, _context)
        R.add_main_variable(E_TYPE, var)

    def decl_rels(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'decl_rels', [R])
        simple_rel = self.simple_rel(R, _context)
        while self._peek("','", 'WHERE', 'HAVING', 'WITH', "';'", 'r"\\)"', context=_context) == "','":
            R.add_main_relation(simple_rel)
            self._scan("','", context=_context)
            simple_rel = self.simple_rel(R, _context)
        R.add_main_relation(simple_rel)

    def simple_rel(self, R, _parent=None):
        _context = self.Context(_parent, self._scanner, 'simple_rel', [R])
        var = self.var(R, _context)
        R_TYPE = self._scan('R_TYPE', context=_context)
        e = Relation(R_TYPE) ; e.append(var)
        expr_add = self.expr_add(R, _context)
        e.append(Comparison('=', expr_add)) ; return e

    def expr(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr', [S])
        _token = self._peek('CMP_OP', 'UNARY_OP', 'r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context)
        if _token == 'CMP_OP':
            CMP_OP = self._scan('CMP_OP', context=_context)
            expr_add = self.expr_add(S, _context)
            return Comparison(CMP_OP.upper(), expr_add)
        else:
            expr_add = self.expr_add(S, _context)
            return Comparison('=', expr_add)

    def expr_add(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr_add', [S])
        _token = self._peek('UNARY_OP', 'r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context)
        if _token != 'UNARY_OP':
            expr_mul = self.expr_mul(S, _context)
            node = expr_mul
            while self._peek('ADD_OP', 'QMARK', 'r"\\)"', "','", 'SORT_DESC', 'SORT_ASC', 'CMP_OP', 'R_TYPE', "'IN'", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'AND', 'OR', context=_context) == 'ADD_OP':
                ADD_OP = self._scan('ADD_OP', context=_context)
                expr_mul = self.expr_mul(S, _context)
                node = MathExpression(ADD_OP, node, expr_mul )
            return node
        else: # == 'UNARY_OP'
            UNARY_OP = self._scan('UNARY_OP', context=_context)
            expr_mul = self.expr_mul(S, _context)
            node = UnaryExpression(UNARY_OP, expr_mul )
            while self._peek('ADD_OP', 'QMARK', 'r"\\)"', "','", 'SORT_DESC', 'SORT_ASC', 'CMP_OP', 'R_TYPE', "'IN'", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'AND', 'OR', context=_context) == 'ADD_OP':
                ADD_OP = self._scan('ADD_OP', context=_context)
                expr_mul = self.expr_mul(S, _context)
                node = MathExpression(ADD_OP, node, expr_mul )
            return node

    def expr_mul(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr_mul', [S])
        expr_pow = self.expr_pow(S, _context)
        node = expr_pow
        while self._peek('MUL_OP', 'ADD_OP', 'QMARK', 'r"\\)"', "','", 'SORT_DESC', 'SORT_ASC', 'CMP_OP', 'R_TYPE', "'IN'", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'AND', 'OR', context=_context) == 'MUL_OP':
            MUL_OP = self._scan('MUL_OP', context=_context)
            expr_pow = self.expr_pow(S, _context)
            node = MathExpression(MUL_OP, node, expr_pow)
        return node

    def expr_pow(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr_pow', [S])
        expr_base = self.expr_base(S, _context)
        node = expr_base
        while self._peek('POW_OP', 'MUL_OP', 'ADD_OP', 'QMARK', 'r"\\)"', "','", 'SORT_DESC', 'SORT_ASC', 'CMP_OP', 'R_TYPE', "'IN'", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'AND', 'OR', context=_context) == 'POW_OP':
            POW_OP = self._scan('POW_OP', context=_context)
            expr_base = self.expr_base(S, _context)
            node = MathExpression(MUL_OP, node, expr_base)
        return node

    def expr_base(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr_base', [S])
        _token = self._peek('r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context)
        if _token not in ['r"\\("', 'VARIABLE', 'E_TYPE', 'FUNCTION']:
            const = self.const(_context)
            return const
        elif _token == 'VARIABLE':
            var = self.var(S, _context)
            return var
        elif _token == 'E_TYPE':
            etype = self.etype(S, _context)
            return etype
        elif _token == 'FUNCTION':
            func = self.func(S, _context)
            return func
        else: # == 'r"\\("'
            self._scan('r"\\("', context=_context)
            expr_add = self.expr_add(S, _context)
            self._scan('r"\\)"', context=_context)
            return expr_add

    def func(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'func', [S])
        FUNCTION = self._scan('FUNCTION', context=_context)
        self._scan('r"\\("', context=_context)
        F = Function(FUNCTION)
        if self._peek('UNARY_OP', 'r"\\)"', 'r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context) != 'r"\\)"':
            expr_add = self.expr_add(S, _context)
            while self._peek("','", 'QMARK', 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'CMP_OP', 'R_TYPE', "'IN'", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'AND', 'OR', context=_context) == "','":
                F.append(expr_add)
                self._scan("','", context=_context)
                expr_add = self.expr_add(S, _context)
            F.append(expr_add)
        self._scan('r"\\)"', context=_context)
        return F

    def in_expr(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'in_expr', [S])
        self._scan("'IN'", context=_context)
        self._scan('r"\\("', context=_context)
        F = Function('IN')
        if self._peek('UNARY_OP', 'r"\\)"', 'r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION', context=_context) != 'r"\\)"':
            expr_add = self.expr_add(S, _context)
            while self._peek("','", 'QMARK', 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'CMP_OP', 'R_TYPE', "'IN'", 'GROUPBY', 'ORDERBY', 'WHERE', 'LIMIT', 'OFFSET', 'HAVING', 'WITH', "';'", 'AND', 'OR', context=_context) == "','":
                F.append(expr_add)
                self._scan("','", context=_context)
                expr_add = self.expr_add(S, _context)
            F.append(expr_add)
        self._scan('r"\\)"', context=_context)
        return F

    def var(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'var', [S])
        VARIABLE = self._scan('VARIABLE', context=_context)
        return VariableRef(S.get_variable(VARIABLE))

    def etype(self, S, _parent=None):
        _context = self.Context(_parent, self._scanner, 'etype', [S])
        E_TYPE = self._scan('E_TYPE', context=_context)
        return S.get_etype(E_TYPE)

    def const(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'const', [])
        _token = self._peek('NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', context=_context)
        if _token == 'NULL':
            NULL = self._scan('NULL', context=_context)
            return Constant(None, None)
        elif _token == 'DATE':
            DATE = self._scan('DATE', context=_context)
            return Constant(DATE.upper(), 'Date')
        elif _token == 'DATETIME':
            DATETIME = self._scan('DATETIME', context=_context)
            return Constant(DATETIME.upper(), 'Datetime')
        elif _token == 'TRUE':
            TRUE = self._scan('TRUE', context=_context)
            return Constant(True, 'Boolean')
        elif _token == 'FALSE':
            FALSE = self._scan('FALSE', context=_context)
            return Constant(False, 'Boolean')
        elif _token == 'FLOAT':
            FLOAT = self._scan('FLOAT', context=_context)
            return Constant(float(FLOAT), 'Float')
        elif _token == 'INT':
            INT = self._scan('INT', context=_context)
            return Constant(int(INT), 'Int')
        elif _token == 'STRING':
            STRING = self._scan('STRING', context=_context)
            return Constant(unquote(STRING), 'String')
        else: # == 'SUBSTITUTE'
            SUBSTITUTE = self._scan('SUBSTITUTE', context=_context)
            return Constant(SUBSTITUTE[2:-2], 'Substitute')


def parse(rule, text):
    P = Hercule(HerculeScanner(text))
    return runtime.wrap_error_reporter(P, rule)

# End -- grammar generated by Yapps


from warnings import warn
from rql.stmts import Union, Select, Delete, Insert, Set
from rql.nodes import *


def unquote(string):
    """Remove quotes from a string."""
    if string.startswith('"'):
        return string[1:-1].replace('\\\\', '\\').replace('\\"', '"')
    elif string.startswith("'"):
        return string[1:-1].replace('\\\\', '\\').replace("\\'", "'")
