"""yapps input grammar for RQL.

Copyright (c) 2002-2005 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: parser.g,v 1.17 2006-03-27 18:10:12 syt Exp $"


from rql.stmts import Select, Delete, Insert, Update
from rql.nodes import *

_OR = OR
_AND = AND


def unquote(string):
    """Remove quotes from a string."""
    if string.startswith('"'):
        return string[1:-1].replace('\\\\', '\\').replace('\\"', '"')
    elif string.startswith("'"):
        return string[1:-1].replace('\\\\', '\\').replace("\\'", "'")

from string import *
import re
from thirdparty.yappsrt import *

class HerculeScanner(Scanner):
    patterns = [
        ('r"\\)"', re.compile('\\)')),
        ('r"\\("', re.compile('\\(')),
        ("','", re.compile(',')),
        ('":"', re.compile(':')),
        ("';'", re.compile(';')),
        ('\\s+', re.compile('\\s+')),
        ('/\\*(?:[^*]|\\*(?!/))*\\*/', re.compile('/\\*(?:[^*]|\\*(?!/))*\\*/')),
        ('DELETE', re.compile('(?i)DELETE')),
        ('SET', re.compile('(?i)SET')),
        ('INSERT', re.compile('(?i)INSERT')),
        ('DISTINCT', re.compile('(?i)DISTINCT')),
        ('WHERE', re.compile('(?i)WHERE')),
        ('OR', re.compile('(?i)OR')),
        ('AND', re.compile('(?i)AND')),
        ('NOT', re.compile('(?i)NOT')),
        ('GROUPBY', re.compile('(?i)GROUPBY')),
        ('ORDERBY', re.compile('(?i)ORDERBY')),
        ('SORT_ASC', re.compile('(?i)ASC')),
        ('SORT_DESC', re.compile('(?i)DESC')),
        ('LIMIT', re.compile('(?i)LIMIT')),
        ('OFFSET', re.compile('(?i)OFFSET')),
        ('BOOLEAN', re.compile('(?i)TRUE|FALSE')),
        ('DATE', re.compile('(?i)TODAY')),
        ('DATETIME', re.compile('(?i)NOW')),
        ('NULL', re.compile('(?i)NULL')),
        ('CMP_OP', re.compile('(?i)<=|<|>=|>|~=|=|LIKE')),
        ('ADD_OP', re.compile('\\+|-')),
        ('MUL_OP', re.compile('\\*|/')),
        ('FUNCTION', re.compile('[A-Za-z_]+\\s*(?=\\()')),
        ('R_TYPE', re.compile('[a-z][a-z0-9_]+')),
        ('E_TYPE', re.compile('[A-Z][a-z]+[a-z0-9]*')),
        ('VARIABLE', re.compile('[A-Z][A-Z0-9_]*')),
        ('STRING', re.compile('\'([^\\\'\\\\]|\\\\.)*\'|\\"([^\\\\\\"\\\\]|\\\\.)*\\"')),
        ('FLOAT', re.compile('\\d+\\.\\d*')),
        ('INT', re.compile('\\d+')),
        ('SUBSTITUTE', re.compile('%\\([A-Za-z_0-9]+\\)s')),
    ]
    def __init__(self, str):
        Scanner.__init__(self,None,['\\s+', '/\\*(?:[^*]|\\*(?!/))*\\*/'],str)

class Hercule(Parser):
    def goal(self, T):
        _token_ = self._peek('DELETE', 'INSERT', 'SET', 'DISTINCT', 'E_TYPE')
        if _token_ == 'DELETE':
            DELETE = self._scan('DELETE')
            _delete = self._delete(Delete(T))
            self._scan("';'")
            return _delete
        elif _token_ == 'INSERT':
            INSERT = self._scan('INSERT')
            _insert = self._insert(Insert(T))
            self._scan("';'")
            return _insert
        elif _token_ == 'SET':
            SET = self._scan('SET')
            update = self.update(Update(T))
            self._scan("';'")
            return update
        else: # in ['DISTINCT', 'E_TYPE']
            select = self.select(Select(T))
            self._scan("';'")
            return select

    def _delete(self, V):
        _token_ = self._peek('E_TYPE', 'VARIABLE')
        if _token_ == 'VARIABLE':
            rels_decl = self.rels_decl(V)
            restr = self.restr(V)
            return V
        else: # == 'E_TYPE'
            vars_decl = self.vars_decl(V)
            restr = self.restr(V)
            return V

    def _insert(self, V):
        vars_decl = self.vars_decl(V)
        insert_rels = self.insert_rels(V)
        return V

    def insert_rels(self, V):
        _token_ = self._peek('":"', "';'")
        if _token_ == '":"':
            self._scan('":"')
            rels_decl = self.rels_decl(V)
            restr = self.restr(V)
            return V
        else: # == "';'"
            pass

    def update(self, V):
        rels_decl = self.rels_decl(V)
        restr = self.restr(V)
        return V

    def select(self, V):
        _token_ = self._peek('DISTINCT', 'E_TYPE')
        if _token_ == 'DISTINCT':
            DISTINCT = self._scan('DISTINCT')
            select_base = self.select_base(V)
            V.distinct = True ; return V
        else: # == 'E_TYPE'
            select_base = self.select_base(V)
            return V

    def select_base(self, V):
        E_TYPE = self._scan('E_TYPE')
        selected_terms = self.selected_terms(V)
        restr = self.restr(V)
        group = self.group(V)
        sort = self.sort(V)
        limit_offset = self.limit_offset(V)
        V.set_statement_type(E_TYPE) ; return V

    def selected_terms(self, V):
        added_expr = self.added_expr(V)
        while self._peek("','", 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'WHERE', 'GROUPBY', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', 'AND', 'OR') == "','":
            V.append_selected(added_expr)
            self._scan("','")
            added_expr = self.added_expr(V)
        V.append_selected(added_expr)

    def group(self, V):
        _token_ = self._peek('GROUPBY', 'ORDERBY', 'LIMIT', 'OFFSET', "';'")
        if _token_ == 'GROUPBY':
            GROUPBY = self._scan('GROUPBY')
            G = Group()
            var = self.var(V)
            while self._peek("','", 'R_TYPE', 'ORDERBY', 'WHERE', '":"', 'MUL_OP', 'LIMIT', 'OFFSET', 'GROUPBY', "';'", 'ADD_OP', 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'AND', 'OR') == "','":
                G.append(var)
                self._scan("','")
                var = self.var(V)
            G.append(var) ; V.append(G)
        else: # in ['ORDERBY', 'LIMIT', 'OFFSET', "';'"]
            pass

    def sort(self, V):
        _token_ = self._peek('ORDERBY', 'LIMIT', 'OFFSET', "';'")
        if _token_ == 'ORDERBY':
            ORDERBY = self._scan('ORDERBY')
            S = Sort()
            sort_term = self.sort_term(V)
            while self._peek("','", 'LIMIT', 'OFFSET', "';'") == "','":
                S.append(sort_term)
                self._scan("','")
                sort_term = self.sort_term(V)
            S.append(sort_term) ; V.append(S)
        else: # in ['LIMIT', 'OFFSET', "';'"]
            pass

    def sort_term(self, V):
        added_expr = self.added_expr(V)
        sort_meth = self.sort_meth()
        return SortTerm(added_expr, sort_meth)

    def sort_meth(self):
        _token_ = self._peek('SORT_DESC', 'SORT_ASC', "','", 'LIMIT', 'OFFSET', "';'")
        if _token_ == 'SORT_DESC':
            SORT_DESC = self._scan('SORT_DESC')
            return 0
        elif _token_ == 'SORT_ASC':
            SORT_ASC = self._scan('SORT_ASC')
            return 1
        else: # in ["','", 'LIMIT', 'OFFSET', "';'"]
            return 1 # default to SORT_ASC

    def limit_offset(self, V):
        limit = self.limit(V)
        offset = self.offset(V)

    def limit(self, V):
        _token_ = self._peek('LIMIT', 'OFFSET', "';'")
        if _token_ == 'LIMIT':
            LIMIT = self._scan('LIMIT')
            INT = self._scan('INT')
            V.limit = int(INT)
        else: # in ['OFFSET', "';'"]
            pass

    def offset(self, V):
        _token_ = self._peek('OFFSET', "';'")
        if _token_ == 'OFFSET':
            OFFSET = self._scan('OFFSET')
            INT = self._scan('INT')
            V.offset = int(INT)
        else: # == "';'"
            pass

    def restr(self, V):
        _token_ = self._peek('WHERE', 'GROUPBY', "';'", 'ORDERBY', 'LIMIT', 'OFFSET')
        if _token_ == 'WHERE':
            WHERE = self._scan('WHERE')
            rels = self.rels(V)
            V.append(rels)
        else: # in ['GROUPBY', "';'", 'ORDERBY', 'LIMIT', 'OFFSET']
            pass

    def rels(self, V):
        ored_rels = self.ored_rels(V)
        lhs = ored_rels
        while self._peek("','", 'r"\\)"', 'GROUPBY', "';'", 'ORDERBY', 'LIMIT', 'OFFSET') == "','":
            self._scan("','")
            ored_rels = self.ored_rels(V)
            lhs = AND(lhs, ored_rels)
        return lhs

    def ored_rels(self, V):
        anded_rels = self.anded_rels(V)
        lhs = anded_rels
        while self._peek('OR', "','", 'r"\\)"', 'GROUPBY', "';'", 'ORDERBY', 'LIMIT', 'OFFSET') == 'OR':
            OR = self._scan('OR')
            anded_rels = self.anded_rels(V)
            lhs = _OR(lhs,anded_rels)
        return lhs

    def anded_rels(self, V):
        rel = self.rel(V)
        lhs = rel
        while self._peek('AND', 'OR', "','", 'r"\\)"', 'GROUPBY', "';'", 'ORDERBY', 'LIMIT', 'OFFSET') == 'AND':
            AND = self._scan('AND')
            rel = self.rel(V)
            lhs = _AND(lhs,rel)
        return lhs

    def rel(self, V):
        _token_ = self._peek('NOT', 'r"\\("', 'VARIABLE')
        if _token_ == 'NOT':
            NOT = self._scan('NOT')
            base_rel = self.base_rel(V)
            base_rel._not = 1; return base_rel
        elif _token_ == 'VARIABLE':
            base_rel = self.base_rel(V)
            return base_rel
        else: # == 'r"\\("'
            self._scan('r"\\("')
            rels = self.rels(V)
            self._scan('r"\\)"')
            return rels

    def base_rel(self, V):
        var = self.var(V)
        R_TYPE = self._scan('R_TYPE')
        e = Relation(R_TYPE) ; e.append(var)
        expr = self.expr(V)
        e.append(expr) ; return e

    def vars_decl(self, V):
        E_TYPE = self._scan('E_TYPE')
        var = self.var(V)
        while self._peek("','", 'R_TYPE', 'WHERE', '":"', 'GROUPBY', "';'", 'MUL_OP', 'ORDERBY', 'LIMIT', 'OFFSET', 'ADD_OP', 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'AND', 'OR') == "','":
            V.add_main_variable(E_TYPE, var)
            self._scan("','")
            E_TYPE = self._scan('E_TYPE')
            var = self.var(V)
        V.add_main_variable(E_TYPE, var)

    def rels_decl(self, V):
        simple_rel = self.simple_rel(V)
        while self._peek("','", 'WHERE', 'GROUPBY', "';'", 'ORDERBY', 'LIMIT', 'OFFSET') == "','":
            V.add_main_relation(simple_rel)
            self._scan("','")
            simple_rel = self.simple_rel(V)
        V.add_main_relation(simple_rel)

    def simple_rel(self, V):
        var = self.var(V)
        R_TYPE = self._scan('R_TYPE')
        e = Relation(R_TYPE) ; e.append(var)
        added_expr = self.added_expr(V)
        e.append(added_expr) ; return e

    def expr(self, V):
        _token_ = self._peek('CMP_OP', 'r"\\("', 'NULL', 'DATE', 'DATETIME', 'BOOLEAN', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION')
        if _token_ == 'CMP_OP':
            CMP_OP = self._scan('CMP_OP')
            added_expr = self.added_expr(V)
            return Comparison(CMP_OP.upper(), added_expr)
        else: 
            added_expr = self.added_expr(V)
            return Comparison('=', added_expr)

    def added_expr(self, V):
        muled_expr = self.muled_expr(V)
        lhs = muled_expr
        while self._peek('ADD_OP', "','", 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'WHERE', 'GROUPBY', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', 'AND', 'OR') == 'ADD_OP':
            ADD_OP = self._scan('ADD_OP')
            muled_expr = self.muled_expr(V)
            lhs = MathExpression( ADD_OP, lhs, muled_expr )
        return lhs

    def muled_expr(self, V):
        base_expr = self.base_expr(V)
        lhs = base_expr
        while self._peek('MUL_OP', 'ADD_OP', "','", 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'WHERE', 'GROUPBY', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', 'AND', 'OR') == 'MUL_OP':
            MUL_OP = self._scan('MUL_OP')
            base_expr = self.base_expr(V)
            lhs = MathExpression( MUL_OP, lhs, base_expr)
        return lhs

    def base_expr(self, V):
        _token_ = self._peek('r"\\("', 'NULL', 'DATE', 'DATETIME', 'BOOLEAN', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE', 'VARIABLE', 'E_TYPE', 'FUNCTION')
        if _token_ not in ['r"\\("', 'VARIABLE', 'E_TYPE', 'FUNCTION']:
            const = self.const()
            return const
        elif _token_ == 'VARIABLE':
            var = self.var(V)
            return var
        elif _token_ == 'E_TYPE':
            e_type = self.e_type(V)
            return e_type
        elif _token_ == 'FUNCTION':
            func = self.func(V)
            return func
        else: # == 'r"\\("'
            self._scan('r"\\("')
            added_expr = self.added_expr(V)
            self._scan('r"\\)"')
            return added_expr

    def func(self, V):
        FUNCTION = self._scan('FUNCTION')
        self._scan('r"\\("')
        F = Function(FUNCTION)
        added_expr = self.added_expr(V)
        while self._peek("','", 'r"\\)"', 'SORT_DESC', 'SORT_ASC', 'WHERE', 'GROUPBY', 'ORDERBY', "';'", 'LIMIT', 'OFFSET', 'AND', 'OR') == "','":
            F.append(added_expr)
            self._scan("','")
            added_expr = self.added_expr(V)
        F.append(added_expr)
        self._scan('r"\\)"')
        return F

    def var(self, V):
        VARIABLE = self._scan('VARIABLE')
        return VariableRef(V.get_variable(VARIABLE))

    def e_type(self, V):
        E_TYPE = self._scan('E_TYPE')
        return V.get_type(E_TYPE)

    def const(self):
        _token_ = self._peek('NULL', 'DATE', 'DATETIME', 'BOOLEAN', 'FLOAT', 'INT', 'STRING', 'SUBSTITUTE')
        if _token_ == 'NULL':
            NULL = self._scan('NULL')
            return Constant('NULL', None)
        elif _token_ == 'DATE':
            DATE = self._scan('DATE')
            return Constant(DATE.upper(), 'Date')
        elif _token_ == 'DATETIME':
            DATETIME = self._scan('DATETIME')
            return Constant(DATETIME.upper(), 'Datetime')
        elif _token_ == 'BOOLEAN':
            BOOLEAN = self._scan('BOOLEAN')
            return Constant(BOOLEAN.lower(), 'Boolean')
        elif _token_ == 'FLOAT':
            FLOAT = self._scan('FLOAT')
            return Constant(float(FLOAT), 'Float')
        elif _token_ == 'INT':
            INT = self._scan('INT')
            return Constant(int(INT), 'Int')
        elif _token_ == 'STRING':
            STRING = self._scan('STRING')
            return Constant(unquote(STRING), 'String')
        else: # == 'SUBSTITUTE'
            SUBSTITUTE = self._scan('SUBSTITUTE')
            return Constant(SUBSTITUTE[2:-2], 'Substitute')


def parse(rule, text):
    P = Hercule(HerculeScanner(text))
    return wrap_error_reporter(P, rule)

if __name__=='old__main__':
    from sys import argv, stdin
    if len(argv) >= 2:
        if len(argv) >= 3:
            f = open(argv[2],'r')
        else:
            f = stdin
        print parse(argv[1], f.read())
    else: print 'Args:  <rule> [<filename>]'
""" Copyright (c) 2000-2003 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: parser_main.py,v 1.3 2005-06-09 00:02:37 ludal Exp $"


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
    except SyntaxError, s:
        # try to get error message from yapps
        data = parser._scanner.input
        print_error(data, s, parser._scanner)
