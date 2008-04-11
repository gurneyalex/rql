"""yapps input grammar for RQL.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""


from rql.stmts import Union, Select, Delete, Insert, Update
from rql.nodes import *

_OR = OR
_AND = AND


def unquote(string):
    """Remove quotes from a string."""
    if string.startswith('"'):
        return string[1:-1].replace('\\\\', '\\').replace('\\"', '"')
    elif string.startswith("'"):
        return string[1:-1].replace('\\\\', '\\').replace("\\'", "'")

# Begin -- grammar generated by Yapps
import sys, re
from yapps import runtime

class HerculeScanner(runtime.Scanner):
    patterns = [
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
        ('FROM', re.compile('(?i)FROM')),
        ('WHERE', re.compile('(?i)WHERE')),
        ('AS', re.compile('(?i)AS')),
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
        ('CMP_OP', re.compile('(?i)<=|<|>=|>|~=|=|LIKE|ILIKE')),
        ('ADD_OP', re.compile('\\+|-')),
        ('MUL_OP', re.compile('\\*|/')),
        ('FUNCTION', re.compile('[A-Za-z_]+\\s*(?=\\()')),
        ('R_TYPE', re.compile('[a-z][a-z0-9_]*')),
        ('E_TYPE', re.compile('[A-Z][A-Za-z0-9]*[a-z]+[0-9]*')),
        ('VARIABLE', re.compile('[A-Z][A-Z0-9_]*')),
        ('COLALIAS', re.compile('[A-Z][A-Z0-9_]*\\.\\d+')),
        ('QMARK', re.compile('\\?')),
        ('STRING', re.compile('\'([^\\\'\\\\]|\\\\.)*\'|\\"([^\\\\\\"\\\\]|\\\\.)*\\"')),
        ('FLOAT', re.compile('\\d+\\.\\d*')),
        ('INT', re.compile('-?\\d+')),
        ('SUBSTITUTE', re.compile('%\\([A-Za-z_0-9]+\\)s')),
    ]
    def __init__(self, str,*args,**kw):
        runtime.Scanner.__init__(self,None,{'\\s+':None,'/\\*(?:[^*]|\\*(?!/))*\\*/':None,},str,*args,**kw)

class Hercule(runtime.Parser):
    Context = runtime.Context
    def goal(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'goal', [])
        _token = self._peek('DELETE', 'INSERT', 'SET', 'DISTINCT', 'E_TYPE', context=_context)
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
            update = self.update(Update(), _context)
            self._scan("';'", context=_context)
            return update
        else: # in ['DISTINCT', 'E_TYPE']
            union = self.union(_context)
            sort = self.sort(union, _context)
            limit_offset = self.limit_offset(union, _context)
            self._scan("';'", context=_context)
            return union

    def _delete(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, '_delete', [V])
        _token = self._peek('E_TYPE', 'VARIABLE', 'COLALIAS', context=_context)
        if _token != 'E_TYPE':
            rels_decl = self.rels_decl(V, _context)
            restr = self.restr(V, _context)
            return V
        else: # == 'E_TYPE'
            vars_decl = self.vars_decl(V, _context)
            restr = self.restr(V, _context)
            return V

    def _insert(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, '_insert', [V])
        vars_decl = self.vars_decl(V, _context)
        insert_rels = self.insert_rels(V, _context)
        return V

    def insert_rels(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'insert_rels', [V])
        _token = self._peek('":"', "';'", context=_context)
        if _token == '":"':
            self._scan('":"', context=_context)
            rels_decl = self.rels_decl(V, _context)
            restr = self.restr(V, _context)
            return V
        else: # == "';'"
            pass

    def update(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'update', [V])
        rels_decl = self.rels_decl(V, _context)
        restr = self.restr(V, _context)
        return V

    def union(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'union', [])
        select = self.select(Select(), _context)
        root = Union(); root.append(select)
        while self._peek('UNION', 'r"\\)"', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', context=_context) == 'UNION':
            UNION = self._scan('UNION', context=_context)
            select = self.select(Select(), _context)
            root.append(select)
        return root

    def select(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'select', [V])
        _token = self._peek('DISTINCT', 'E_TYPE', context=_context)
        if _token == 'DISTINCT':
            DISTINCT = self._scan('DISTINCT', context=_context)
            select_base = self.select_base(V, _context)
            V.distinct = True ; return V
        else: # == 'E_TYPE'
            select_base = self.select_base(V, _context)
            return V

    def select_base(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'select_base', [V])
        E_TYPE = self._scan('E_TYPE', context=_context)
        selected_terms = self.selected_terms(V, _context)
        select_from = self.select_from(V, _context)
        restr = self.restr(V, _context)
        group = self.group(V, _context)
        having = self.having(V, _context)
        V.set_statement_type(E_TYPE) ; return V

    def select_from(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'select_from', [V])
        _token = self._peek('FROM', 'WHERE', 'GROUPBY', 'HAVING', "';'", 'UNION', 'r"\\)"', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context)
        if _token == 'FROM':
            FROM = self._scan('FROM', context=_context)
            self._scan('r"\\("', context=_context)
            union = self.union(_context)
            self._scan('r"\\)"', context=_context)
            AS = self._scan('AS', context=_context)
            VARIABLE = self._scan('VARIABLE', context=_context)
            V.set_from(union, VARIABLE)
        else:
            pass

    def selected_terms(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'selected_terms', [V])
        added_expr = self.added_expr(V, _context)
        while self._peek("','", 'r"\\)"', 'CMP_OP', 'SORT_DESC', 'SORT_ASC', 'FROM', 'WHERE', 'GROUPBY', 'QMARK', 'HAVING', "';'", 'LIMIT', 'OFFSET', 'UNION', 'AND', 'ORDERBY', 'OR', context=_context) == "','":
            V.append_selected(added_expr)
            self._scan("','", context=_context)
            added_expr = self.added_expr(V, _context)
        V.append_selected(added_expr)

    def group(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'group', [V])
        _token = self._peek('GROUPBY', 'HAVING', 'UNION', 'r"\\)"', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', context=_context)
        if _token == 'GROUPBY':
            GROUPBY = self._scan('GROUPBY', context=_context)
            G = Group()
            var = self.var(V, _context)
            while self._peek("','", 'R_TYPE', 'QMARK', 'HAVING', 'WHERE', '":"', 'MUL_OP', 'GROUPBY', "';'", 'ADD_OP', 'UNION', 'r"\\)"', 'CMP_OP', 'SORT_DESC', 'SORT_ASC', 'ORDERBY', 'LIMIT', 'OFFSET', 'FROM', 'AND', 'OR', context=_context) == "','":
                G.append(var)
                self._scan("','", context=_context)
                var = self.var(V, _context)
            G.append(var) ; V.append(G)
        else:
            pass

    def having(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'having', [V])
        _token = self._peek('HAVING', 'UNION', 'r"\\)"', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', context=_context)
        if _token == 'HAVING':
            HAVING = self._scan('HAVING', context=_context)
            G = Having()
            cmp_expr = self.cmp_expr(V, _context)
            while self._peek("','", 'UNION', 'r"\\)"', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', context=_context) == "','":
                G.append(cmp_expr)
                self._scan("','", context=_context)
                cmp_expr = self.cmp_expr(V, _context)
            G.append(cmp_expr) ; V.append(G)
        else: # in ['UNION', 'r"\\)"', 'ORDERBY', "';'", 'LIMIT', 'OFFSET']
            pass

    def cmp_expr(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'cmp_expr', [V])
        added_expr = self.added_expr(V, _context)
        c1 = added_expr
        CMP_OP = self._scan('CMP_OP', context=_context)
        cmp = Comparison(CMP_OP.upper(), c1);
        added_expr = self.added_expr(V, _context)
        cmp.append(added_expr); return cmp

    def sort(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'sort', [V])
        _token = self._peek('ORDERBY', "';'", 'LIMIT', 'OFFSET', context=_context)
        if _token == 'ORDERBY':
            ORDERBY = self._scan('ORDERBY', context=_context)
            S = Sort(); V.set_sortterms(S)
            sort_term = self.sort_term(V, _context)
            while self._peek("','", "';'", 'LIMIT', 'OFFSET', context=_context) == "','":
                S.append(sort_term)
                self._scan("','", context=_context)
                sort_term = self.sort_term(V, _context)
            S.append(sort_term)
        else: # in ["';'", 'LIMIT', 'OFFSET']
            pass

    def sort_term(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'sort_term', [V])
        added_expr = self.added_expr(V, _context)
        sort_meth = self.sort_meth(_context)
        return SortTerm(added_expr, sort_meth)

    def sort_meth(self, _parent=None):
        _context = self.Context(_parent, self._scanner, 'sort_meth', [])
        _token = self._peek('SORT_DESC', 'SORT_ASC', "','", "';'", 'LIMIT', 'OFFSET', context=_context)
        if _token == 'SORT_DESC':
            SORT_DESC = self._scan('SORT_DESC', context=_context)
            return 0
        elif _token == 'SORT_ASC':
            SORT_ASC = self._scan('SORT_ASC', context=_context)
            return 1
        else: # in ["','", "';'", 'LIMIT', 'OFFSET']
            return 1 # default to SORT_ASC

    def limit_offset(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'limit_offset', [V])
        limit = self.limit(V, _context)
        offset = self.offset(V, _context)

    def limit(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'limit', [V])
        _token = self._peek('LIMIT', 'OFFSET', "';'", context=_context)
        if _token == 'LIMIT':
            LIMIT = self._scan('LIMIT', context=_context)
            INT = self._scan('INT', context=_context)
            V.set_limit(int(INT))
        else: # in ['OFFSET', "';'"]
            pass

    def offset(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'offset', [V])
        _token = self._peek('OFFSET', "';'", context=_context)
        if _token == 'OFFSET':
            OFFSET = self._scan('OFFSET', context=_context)
            INT = self._scan('INT', context=_context)
            V.set_offset(int(INT))
        else: # == "';'"
            pass

    def restr(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'restr', [V])
        _token = self._peek('WHERE', 'GROUPBY', "';'", 'HAVING', 'UNION', 'r"\\)"', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context)
        if _token == 'WHERE':
            WHERE = self._scan('WHERE', context=_context)
            rels = self.rels(V, _context)
            V.append(rels)
        else:
            pass

    def rels(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rels', [V])
        ored_rels = self.ored_rels(V, _context)
        lhs = ored_rels
        while self._peek("','", 'r"\\)"', 'GROUPBY', "';'", 'HAVING', 'UNION', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context) == "','":
            self._scan("','", context=_context)
            ored_rels = self.ored_rels(V, _context)
            lhs = AND(lhs, ored_rels)
        return lhs

    def ored_rels(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'ored_rels', [V])
        anded_rels = self.anded_rels(V, _context)
        lhs = anded_rels
        while self._peek('OR', "','", 'r"\\)"', 'GROUPBY', "';'", 'HAVING', 'UNION', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context) == 'OR':
            OR = self._scan('OR', context=_context)
            anded_rels = self.anded_rels(V, _context)
            lhs = _OR(lhs,anded_rels)
        return lhs

    def anded_rels(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'anded_rels', [V])
        not_rels = self.not_rels(V, _context)
        lhs = not_rels
        while self._peek('AND', 'OR', "','", 'r"\\)"', 'GROUPBY', "';'", 'HAVING', 'UNION', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context) == 'AND':
            AND = self._scan('AND', context=_context)
            not_rels = self.not_rels(V, _context)
            lhs = _AND(lhs, not_rels)
        return lhs

    def not_rels(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'not_rels', [V])
        _token = self._peek('NOT', 'r"\\("', 'EXISTS', 'VARIABLE', 'COLALIAS', context=_context)
        if _token == 'NOT':
            NOT = self._scan('NOT', context=_context)
            rel = self.rel(V, _context)
            not_ = Not(); not_.append(rel); return not_
        else: # in ['r"\\("', 'EXISTS', 'VARIABLE', 'COLALIAS']
            rel = self.rel(V, _context)
            return rel

    def rel(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rel', [V])
        _token = self._peek('r"\\("', 'EXISTS', 'VARIABLE', 'COLALIAS', context=_context)
        if _token != 'r"\\("':
            base_rel = self.base_rel(V, _context)
            return base_rel
        else: # == 'r"\\("'
            self._scan('r"\\("', context=_context)
            rels = self.rels(V, _context)
            self._scan('r"\\)"', context=_context)
            return rels

    def base_rel(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'base_rel', [V])
        _token = self._peek('EXISTS', 'VARIABLE', 'COLALIAS', context=_context)
        if _token != 'EXISTS':
            var = self.var(V, _context)
            opt_left = self.opt_left(V, _context)
            rtype = self.rtype(V, _context)
            rtype.append(var) ; rtype.set_optional(opt_left)
            expr = self.expr(V, _context)
            opt_right = self.opt_right(V, _context)
            rtype.append(expr) ; rtype.set_optional(opt_right) ; return rtype
        else: # == 'EXISTS'
            EXISTS = self._scan('EXISTS', context=_context)
            self._scan('r"\\("', context=_context)
            rels = self.rels(V, _context)
            self._scan('r"\\)"', context=_context)
            return Exists(rels)

    def rtype(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rtype', [V])
        R_TYPE = self._scan('R_TYPE', context=_context)
        return Relation(R_TYPE)

    def opt_left(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'opt_left', [V])
        _token = self._peek('QMARK', 'R_TYPE', context=_context)
        if _token == 'QMARK':
            QMARK = self._scan('QMARK', context=_context)
            return 'left'
        else: # == 'R_TYPE'
            pass

    def opt_right(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'opt_right', [V])
        _token = self._peek('QMARK', 'AND', 'OR', "','", 'r"\\)"', 'GROUPBY', "';'", 'HAVING', 'UNION', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context)
        if _token == 'QMARK':
            QMARK = self._scan('QMARK', context=_context)
            return 'right'
        else:
            pass

    def vars_decl(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'vars_decl', [V])
        E_TYPE = self._scan('E_TYPE', context=_context)
        var = self.var(V, _context)
        while self._peek("','", 'R_TYPE', 'QMARK', 'WHERE', '":"', 'GROUPBY', "';'", 'MUL_OP', 'HAVING', 'ADD_OP', 'UNION', 'r"\\)"', 'CMP_OP', 'SORT_DESC', 'SORT_ASC', 'ORDERBY', 'FROM', 'LIMIT', 'OFFSET', 'AND', 'OR', context=_context) == "','":
            V.add_main_variable(E_TYPE, var)
            self._scan("','", context=_context)
            E_TYPE = self._scan('E_TYPE', context=_context)
            var = self.var(V, _context)
        V.add_main_variable(E_TYPE, var)

    def rels_decl(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'rels_decl', [V])
        simple_rel = self.simple_rel(V, _context)
        while self._peek("','", 'WHERE', 'GROUPBY', "';'", 'HAVING', 'UNION', 'r"\\)"', 'ORDERBY', 'LIMIT', 'OFFSET', context=_context) == "','":
            V.add_main_relation(simple_rel)
            self._scan("','", context=_context)
            simple_rel = self.simple_rel(V, _context)
        V.add_main_relation(simple_rel)

    def simple_rel(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'simple_rel', [V])
        var = self.var(V, _context)
        R_TYPE = self._scan('R_TYPE', context=_context)
        e = Relation(R_TYPE) ; e.append(var)
        added_expr = self.added_expr(V, _context)
        e.append(Comparison('=', added_expr)) ; return e

    def expr(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'expr', [V])
        _token = self._peek('CMP_OP', 'r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'COLALIAS', 'E_TYPE', 'FUNCTION', context=_context)
        if _token == 'CMP_OP':
            CMP_OP = self._scan('CMP_OP', context=_context)
            added_expr = self.added_expr(V, _context)
            return Comparison(CMP_OP.upper(), added_expr)
        else:
            added_expr = self.added_expr(V, _context)
            return Comparison('=', added_expr)

    def added_expr(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'added_expr', [V])
        muled_expr = self.muled_expr(V, _context)
        lhs = muled_expr
        while self._peek('ADD_OP', "','", 'r"\\)"', 'CMP_OP', 'SORT_DESC', 'SORT_ASC', 'FROM', 'QMARK', 'WHERE', 'GROUPBY', 'HAVING', "';'", 'LIMIT', 'OFFSET', 'UNION', 'AND', 'ORDERBY', 'OR', context=_context) == 'ADD_OP':
            ADD_OP = self._scan('ADD_OP', context=_context)
            muled_expr = self.muled_expr(V, _context)
            lhs = MathExpression( ADD_OP, lhs, muled_expr )
        return lhs

    def muled_expr(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'muled_expr', [V])
        base_expr = self.base_expr(V, _context)
        lhs = base_expr
        while self._peek('MUL_OP', 'ADD_OP', "','", 'r"\\)"', 'CMP_OP', 'SORT_DESC', 'SORT_ASC', 'FROM', 'QMARK', 'WHERE', 'GROUPBY', 'HAVING', "';'", 'LIMIT', 'OFFSET', 'UNION', 'AND', 'ORDERBY', 'OR', context=_context) == 'MUL_OP':
            MUL_OP = self._scan('MUL_OP', context=_context)
            base_expr = self.base_expr(V, _context)
            lhs = MathExpression( MUL_OP, lhs, base_expr)
        return lhs

    def base_expr(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'base_expr', [V])
        _token = self._peek('r"\\("', 'NULL', 'DATE', 'DATETIME', 'TRUE', 'FALSE', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'COLALIAS', 'E_TYPE', 'FUNCTION', context=_context)
        if _token not in ['r"\\("', 'VARIABLE', 'COLALIAS', 'E_TYPE', 'FUNCTION']:
            const = self.const(_context)
            return const
        elif _token not in ['r"\\("', 'E_TYPE', 'FUNCTION']:
            var = self.var(V, _context)
            return var
        elif _token == 'E_TYPE':
            etype = self.etype(V, _context)
            return etype
        elif _token == 'FUNCTION':
            func = self.func(V, _context)
            return func
        else: # == 'r"\\("'
            self._scan('r"\\("', context=_context)
            added_expr = self.added_expr(V, _context)
            self._scan('r"\\)"', context=_context)
            return added_expr

    def func(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'func', [V])
        FUNCTION = self._scan('FUNCTION', context=_context)
        self._scan('r"\\("', context=_context)
        F = Function(FUNCTION)
        added_expr = self.added_expr(V, _context)
        while self._peek("','", 'r"\\)"', 'CMP_OP', 'SORT_DESC', 'SORT_ASC', 'FROM', 'QMARK', 'WHERE', 'GROUPBY', 'HAVING', "';'", 'LIMIT', 'OFFSET', 'UNION', 'AND', 'ORDERBY', 'OR', context=_context) == "','":
            F.append(added_expr)
            self._scan("','", context=_context)
            added_expr = self.added_expr(V, _context)
        F.append(added_expr)
        self._scan('r"\\)"', context=_context)
        return F

    def var(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'var', [V])
        _token = self._peek('VARIABLE', 'COLALIAS', context=_context)
        if _token == 'VARIABLE':
            VARIABLE = self._scan('VARIABLE', context=_context)
            return VariableRef(V.get_variable(VARIABLE))
        else: # == 'COLALIAS'
            COLALIAS = self._scan('COLALIAS', context=_context)
            return ColumnAlias(COLALIAS)

    def etype(self, V, _parent=None):
        _context = self.Context(_parent, self._scanner, 'etype', [V])
        E_TYPE = self._scan('E_TYPE', context=_context)
        return V.get_etype(E_TYPE)

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

if __name__ == 'old__main__':
    from sys import argv, stdin
    if len(argv) >= 2:
        if len(argv) >= 3:
            f = open(argv[2],'r')
        else:
            f = stdin
        print parse(argv[1], f.read())
    else: print >>sys.stderr, 'Args:  <rule> [<filename>]'
# End -- grammar generated by Yapps

if __name__ == '__main__':
    from sys import argv
    
    parser = Hercule(HerculeScanner(argv[1]))
    e_types = {}
    # parse the RQL string
    try:
        tree = parser.goal(e_types)
        print '-'*80
        print tree
        print '-'*80
        print repr(tree)
        print e_types
    except SyntaxError, ex:
        # try to get error message from yapps
        from yapps.runtime import print_error
        print_error(ex, parser._scanner)
