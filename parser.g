"""yapps input grammar for RQL.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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

from warnings import warn
from rql.stmts import Union, Select, Delete, Insert, Set
from rql.nodes import *


def unquote(string):
    """Remove quotes from a string."""
    if string.startswith('"'):
        return string[1:-1].replace('\\\\', '\\').replace('\\"', '"')
    elif string.startswith("'"):
        return string[1:-1].replace('\\\\', '\\').replace("\\'", "'")
%%

parser Hercule:

    ignore:            r'\s+'
    # C-like comments
    ignore:            r'/\*(?:[^*]|\*(?!/))*\*/'

    token DELETE:      r'(?i)DELETE'
    token SET:         r'(?i)SET'
    token INSERT:      r'(?i)INSERT'
    token UNION:       r'(?i)UNION'
    token DISTINCT:    r'(?i)DISTINCT'
    token WITH:        r'(?i)WITH'
    token WHERE:       r'(?i)WHERE'
    token BEING:          r'(?i)BEING'
    token OR:          r'(?i)OR'
    token AND:         r'(?i)AND'
    token NOT:         r'(?i)NOT'
    token GROUPBY:     r'(?i)GROUPBY'
    token HAVING:      r'(?i)HAVING'
    token ORDERBY:     r'(?i)ORDERBY'
    token SORT_ASC:    r'(?i)ASC'
    token SORT_DESC:   r'(?i)DESC'
    token LIMIT:       r'(?i)LIMIT'
    token OFFSET:      r'(?i)OFFSET'
    token DATE:        r'(?i)TODAY'
    token DATETIME:    r'(?i)NOW'
    token TRUE:        r'(?i)TRUE'
    token FALSE:       r'(?i)FALSE'
    token NULL:        r'(?i)NULL'
    token EXISTS:      r'(?i)EXISTS'
    token CMP_OP:      r'(?i)<=|<|>=|>|~=|=|LIKE|ILIKE|IS'
    token ADD_OP:      r'\+|-'
    token MUL_OP:      r'\*|/'
    token FUNCTION:    r'[A-Za-z_]+\s*(?=\()'
    token R_TYPE:      r'[a-z_][a-z0-9_]*'
    token E_TYPE:      r'[A-Z][A-Za-z0-9]*[a-z]+[0-9]*'
    token VARIABLE:    r'[A-Z][A-Z0-9_]*'
    token COLALIAS:    r'[A-Z][A-Z0-9_]*\.\d+'
    token QMARK:       r'\?'

    token STRING:      r"'([^\'\\]|\\.)*'|\"([^\\\"\\]|\\.)*\""
    token FLOAT:       r'\d+\.\d*'
    token INT:         r'-?\d+'
    token SUBSTITUTE:  r'%\([A-Za-z_0-9]+\)s'


#// Grammar entry ###############################################################


rule goal: DELETE _delete<<Delete()>> ';'             {{ return _delete }}

         | INSERT _insert<<Insert()>> ';'             {{ return _insert }}

         | SET update<<Set()>> ';'                    {{ return update }}

         | union<<Union()>> ';'                       {{ return union }}

#// Deletion  ###################################################################

rule _delete<<R>>: decl_rels<<R>> where<<R>> {{ return R }}

                 | decl_vars<<R>> where<<R>> {{ return R }}


#// Insertion  ##################################################################

rule _insert<<R>>: decl_vars<<R>> insert_rels<<R>> {{ return R }}


rule insert_rels<<R>>: ":" decl_rels<<R>> where<<R>> {{ return R }}

                     |


#// Update  #####################################################################

rule update<<R>>: decl_rels<<R>> where<<R>> {{ return R }}


#// Selection  ##################################################################

rule union<<R>>: select<<Select()>>               {{ R.append(select); return R }}

               | r"\(" select<<Select()>> r"\)"   {{ R.append(select) }}
                 ( UNION
                   r"\(" select<<Select()>> r"\)" {{ R.append(select) }}
                 )*                               {{ return R }}

rule select<<S>>: DISTINCT select_<<S>>  {{ S.distinct = True ; return S }}
                 | select_<<S>>          {{ return S }}

rule select_<<S>>: E_TYPE selection<<S>>
                   groupby<<S>>
                   orderby<<S>>
                   limit_offset<<S>>
                   where<<S>>
                   having<<S>>
                   with_<<S>>
                   dgroupby<<S>>
                   dorderby<<S>>
                   dlimit_offset<<S>>    {{ S.set_statement_type(E_TYPE); return S }}

rule selection<<S>>: expr_add<<S>>        {{ S.append_selected(expr_add) }}
                     (  ',' expr_add<<S>> {{ S.append_selected(expr_add) }}
                     )*



#// other clauses (groupby, orderby, with, having) ##############################

#// to remove in rql 1.0
rule dorderby<<S>>: orderby<<S>> {{ if orderby: warn('ORDERBY is now before WHERE clause') }}
rule dgroupby<<S>>: groupby<<S>> {{ if groupby: warn('GROUPBY is now before WHERE clause') }}
rule dlimit_offset<<S>>: limit_offset<<S>> {{ if limit_offset: warn('LIMIT/OFFSET are now before WHERE clause') }}

rule groupby<<S>>: GROUPBY variables<<S>> {{ S.set_groupby(variables); return True }}
                 |

rule having<<S>>: HAVING               {{ nodes = [] }}
                   expr_cmp<<S>>       {{ nodes.append(expr_cmp) }}
                   ( ',' expr_cmp<<S>> {{ nodes.append(expr_cmp) }}
                   )*                  {{ S.set_having(nodes) }}
                |

rule orderby<<S>>: ORDERBY              {{ nodes = [] }}
                   sort_term<<S>>       {{ nodes.append(sort_term) }}
                   ( ',' sort_term<<S>> {{ nodes.append(sort_term) }}
                   )*                   {{ S.set_orderby(nodes); return True }}
                 |

rule with_<<S>>: WITH                {{ nodes = [] }}
                 subquery<<S>>       {{ nodes.append(subquery) }}
                 ( ',' subquery<<S>> {{ nodes.append(subquery) }}
                 )*                  {{ S.set_with(nodes) }}
               |

rule subquery<<S>>: variables<<S>>                     {{ node = SubQuery() ; node.set_aliases(variables) }}
                    BEING r"\(" union<<Union()>> r"\)" {{ node.set_query(union); return node }}


rule expr_cmp<<S>>: expr_add<<S>>  {{ c1 = expr_add }}
                    CMP_OP         {{ cmp = Comparison(CMP_OP.upper(), c1) }}
                    expr_add<<S>>  {{ cmp.append(expr_add); return cmp }}


rule sort_term<<S>>: expr_add<<S>> sort_meth {{ return SortTerm(expr_add, sort_meth) }}


rule sort_meth: SORT_DESC {{ return 0 }}

              | SORT_ASC  {{ return 1 }}

              |           {{ return 1 # default to SORT_ASC }}


#// Limit and offset ############################################################

rule limit_offset<<R>> :  limit<<R>> offset<<R>> {{ return limit or offset }}

rule limit<<R>> : LIMIT INT {{ R.set_limit(int(INT)); return True }}
                |

rule offset<<R>> : OFFSET INT {{ R.set_offset(int(INT)); return True }}
  		         |


#// Restriction statements ######################################################

rule where<<S>>: WHERE restriction<<S>> {{ S.set_where(restriction) }}
               |

rule restriction<<S>>: rels_or<<S>>       {{ node = rels_or }}
                       ( ',' rels_or<<S>> {{ node = And(node, rels_or) }}
                       )*                 {{ return node }}

rule rels_or<<S>>: rels_and<<S>>      {{ node = rels_and }}
                   ( OR rels_and<<S>> {{ node = Or(node, rels_and) }}
                   )*                 {{ return node }}

rule rels_and<<S>>: rels_not<<S>>        {{ node = rels_not }}
                    (  AND rels_not<<S>> {{ node = And(node, rels_not) }}
                    )*                   {{ return node }}

rule rels_not<<S>>: NOT rel<<S>> {{ node = Not(); node.append(rel); return node }}
                  | rel<<S>>     {{ return rel }}

rule rel<<S>>: rel_base<<S>>                {{ return rel_base }}
             | r"\(" restriction<<S>> r"\)" {{ return restriction }}


rule rel_base<<S>>: var<<S>> opt_left<<S>> rtype        {{ rtype.append(var) ; rtype.set_optional(opt_left) }}
                    expr<<S>> opt_right<<S>>            {{ rtype.append(expr) ; rtype.set_optional(opt_right) ; return rtype }}
                  | EXISTS r"\(" restriction<<S>> r"\)" {{ return Exists(restriction) }}

rule rtype: R_TYPE {{ return Relation(R_TYPE) }}

rule opt_left<<S>>: QMARK  {{ return 'left' }}
                  |
rule opt_right<<S>>: QMARK  {{ return 'right' }}
                   |

#// common statements ###########################################################

rule variables<<S>>:                   {{ vars = [] }}
                       var<<S>>        {{ vars.append(var) }}
                       (  ',' var<<S>> {{ vars.append(var) }}
                       )*              {{ return vars }}

rule decl_vars<<R>>: E_TYPE var<<R>> (     {{ R.add_main_variable(E_TYPE, var) }}
                     ',' E_TYPE var<<R>>)* {{ R.add_main_variable(E_TYPE, var) }}


rule decl_rels<<R>>: simple_rel<<R>> (     {{ R.add_main_relation(simple_rel) }}
                     ',' simple_rel<<R>>)* {{ R.add_main_relation(simple_rel) }}


rule simple_rel<<R>>: var<<R>> R_TYPE  {{ e = Relation(R_TYPE) ; e.append(var) }}
                      expr_add<<R>>    {{ e.append(Comparison('=', expr_add)) ; return e }}


rule expr<<S>>: CMP_OP expr_add<<S>> {{ return Comparison(CMP_OP.upper(), expr_add) }}

                | expr_add<<S>>      {{ return Comparison('=', expr_add) }}


rule expr_add<<S>>: expr_mul<<S>>          {{ node = expr_mul }}
                    ( ADD_OP expr_mul<<S>> {{ node = MathExpression( ADD_OP, node, expr_mul ) }}
                    )*                     {{ return node }}


rule expr_mul<<S>>: expr_base<<S>>          {{ node = expr_base }}
                    ( MUL_OP expr_base<<S>> {{ node = MathExpression( MUL_OP, node, expr_base) }}
                    )*                      {{ return node }}


rule expr_base<<S>>: const                     {{ return const }}
                   | var<<S>>                  {{ return var }}
                   | etype<<S>>                {{ return etype }}
                   | func<<S>>                 {{ return func }}
                   | r"\(" expr_add<<S>> r"\)" {{ return expr_add }}


rule func<<S>>: FUNCTION r"\("        {{ F = Function(FUNCTION) }}
                   ( expr_add<<S>> (     {{ F.append(expr_add) }}
                      ',' expr_add<<S>>
                     )*                  {{ F.append(expr_add) }}
                   )?
                r"\)"                 {{ return F }}


rule var<<S>>: VARIABLE {{ return VariableRef(S.get_variable(VARIABLE)) }}

rule etype<<S>>: E_TYPE {{ return S.get_etype(E_TYPE) }}


rule const: NULL       {{ return Constant(None, None) }}
          | DATE       {{ return Constant(DATE.upper(), 'Date') }}
          | DATETIME   {{ return Constant(DATETIME.upper(), 'Datetime') }}
          | TRUE       {{ return Constant(True, 'Boolean') }}
          | FALSE      {{ return Constant(False, 'Boolean') }}
          | FLOAT      {{ return Constant(float(FLOAT), 'Float') }}
          | INT        {{ return Constant(int(INT), 'Int') }}
          | STRING     {{ return Constant(unquote(STRING), 'String') }}
          | SUBSTITUTE {{ return Constant(SUBSTITUTE[2:-2], 'Substitute') }}

