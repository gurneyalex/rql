"""yapps input grammar for RQL.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""


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
%%

parser Hercule:

    ignore:            r'\s+'
    # C-like comments
    ignore:            r'/\*(?:[^*]|\*(?!/))*\*/'

    token DELETE:      r'(?i)DELETE'
    token SET:         r'(?i)SET'
    token INSERT:      r'(?i)INSERT'
    token DISTINCT:    r'(?i)DISTINCT'
    token WHERE:       r'(?i)WHERE'
    token OR:          r'(?i)OR'
    token AND:         r'(?i)AND'
    token NOT:         r'(?i)NOT'
    token GROUPBY:     r'(?i)GROUPBY'
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
    token CMP_OP:      r'(?i)<=|<|>=|>|~=|=|LIKE|ILIKE'
    token ADD_OP:      r'\+|-'
    token MUL_OP:      r'\*|/'
    token FUNCTION:    r'[A-Za-z_]+\s*(?=\()'
    token R_TYPE:      r'[a-z][a-z0-9_]*'
    token E_TYPE:      r'[A-Z][a-z]+[a-z0-9]*'
    token VARIABLE:    r'[A-Z][A-Z0-9_]*'
    token QMARK:       r'\?'

    token STRING:      r"'([^\'\\]|\\.)*'|\"([^\\\"\\]|\\.)*\""
    token FLOAT:       r'\d+\.\d*'
    token INT:         r'-?\d+'
    token SUBSTITUTE:  r'%\([A-Za-z_0-9]+\)s'


# Grammar entry ###############################################################
#
# abbreviations :
#
#  rel -> relation
#  decl -> declaration
#  expr -> expression
#  restr -> restriction
#  var -> variable
#  func -> function
#  const -> constant
#  cmp -> comparison

rule goal<<T>>: DELETE _delete<<Delete(T)>> ';' {{ return _delete }}

              | INSERT _insert<<Insert(T)>> ';' {{ return _insert }}
 
              | SET update<<Update(T)>> ';'     {{ return update }}

              | select<<Select(T)>> ';'         {{ return select }}


# Deletion  ###################################################################

rule _delete<<V>>: rels_decl<<V>> restr<<V>> {{ return V }}

                 | vars_decl<<V>> restr<<V>>    {{ return V }}


# Insertion  ##################################################################

rule _insert<<V>>: vars_decl<<V>> insert_rels<<V>> {{ return V }}
                    

rule insert_rels<<V>>: ":" rels_decl<<V>> restr<<V>> {{ return V }}

                     |


# Update  #####################################################################

rule update<<V>>: rels_decl<<V>> restr<<V>> {{ return V }}


# Selection  ##################################################################

rule select<<V>>: DISTINCT select_base<<V>> {{ V.distinct = True ; return V }}

                | select_base<<V>>          {{ return V }}


rule select_base<<V>>: E_TYPE selected_terms<<V>> restr<<V>> 
                       group<<V>> sort<<V>> 
                       limit_offset<<V>>  {{ V.set_statement_type(E_TYPE) ; return V }}


rule selected_terms<<V>>: added_expr<<V>> (   {{ V.append_selected(added_expr) }}
                            ',' added_expr<<V>>
                            )*                    {{ V.append_selected(added_expr) }}



# Groups and sorts ############################################################

rule group<<V>>: GROUPBY        {{ G = Group() }}
                   var<<V>> (   {{ G.append(var) }}
                   ',' var<<V>>
                   )*           {{ G.append(var) ; V.append(G) }}

                 |


rule sort<<V>>: ORDERBY              {{ S = Sort() }}
                  sort_term<<V>> (   {{ S.append(sort_term) }}
                  ',' sort_term<<V>>
                  )*                 {{ S.append(sort_term) ; V.append(S) }}

                |


rule sort_term<<V>>: added_expr<<V>> sort_meth {{ return SortTerm(added_expr, sort_meth) }}


rule sort_meth: SORT_DESC {{ return 0 }}

              | SORT_ASC  {{ return 1 }}

              |           {{ return 1 # default to SORT_ASC }}


# Limit and offset ############################################################

rule limit_offset<<V>> :  limit<<V>> offset<<V>>
		  
rule limit<<V>> : LIMIT INT {{ V.set_limit(int(INT)) }} 
                |


rule offset<<V>> : OFFSET INT {{ V.set_offset(int(INT)) }}
  		         | 


# Restriction statements ######################################################

rule restr<<V>>: WHERE rels<<V>> {{ V.append(rels) }}

               | 

rule rels<<V>>: ored_rels<<V>>       {{ lhs = ored_rels }}
                ( ',' ored_rels<<V>> {{ lhs = AND(lhs, ored_rels) }}
                )*                   {{ return lhs }}


rule ored_rels<<V>>: anded_rels<<V>>  {{ lhs = anded_rels }}
                     ( OR anded_rels<<V>> {{ lhs = _OR(lhs,anded_rels) }}
                     )*                 {{ return lhs }}


rule anded_rels<<V>>: rel<<V>>        {{ lhs = rel }}
                      (  AND rel<<V>> {{ lhs = _AND(lhs,rel) }}
                      )*              {{ return lhs }}


rule rel<<V>>: NOT base_rel<<V>>       {{ base_rel._not = 1; return base_rel }} 

               | base_rel<<V>>         {{ return base_rel }}

               | r"\(" rels<<V>> r"\)" {{ return rels }}


rule base_rel<<V>>: var<<V>> opt_left<<V>> rtype<<V>> {{ rtype.append(var) ; rtype.set_optional(opt_left) }} 
                    expr<<V>> opt_right<<V>>          {{ rtype.append(expr) ; rtype.set_optional(opt_right) ; return rtype }}
                   | EXISTS r"\(" rels<<V>> r"\)"     {{ return Exists(rels) }}
               
                  
rule rtype<<V>>: R_TYPE {{ return Relation(R_TYPE) }}

rule opt_left<<V>>: QMARK  {{ return 'left' }}
                   | 
rule opt_right<<V>>: QMARK  {{ return 'right' }}
                   | 
                    
# common statements ###########################################################

rule vars_decl<<V>>: E_TYPE var<<V>> (     {{ V.add_main_variable(E_TYPE, var) }}
                     ',' E_TYPE var<<V>>)* {{ V.add_main_variable(E_TYPE, var) }}


rule rels_decl<<V>>: simple_rel<<V>> (     {{ V.add_main_relation(simple_rel) }}
                     ',' simple_rel<<V>>)* {{ V.add_main_relation(simple_rel) }}


rule simple_rel<<V>>: var<<V>> R_TYPE    {{ e = Relation(R_TYPE) ; e.append(var) }} 
                      added_expr<<V>>    {{ e.append(Comparison('=', added_expr)) ; return e }}


rule expr<<V>>: CMP_OP added_expr<<V>> {{ return Comparison(CMP_OP.upper(), added_expr) }}

                | added_expr<<V>>      {{ return Comparison('=', added_expr) }}


rule added_expr<<V>>: muled_expr<<V>>          {{ lhs = muled_expr }}
                      ( ADD_OP muled_expr<<V>> {{ lhs = MathExpression( ADD_OP, lhs, muled_expr ) }}
                      )*                       {{ return lhs }}


rule muled_expr<<V>>: base_expr<<V>>          {{ lhs = base_expr }}
                      ( MUL_OP base_expr<<V>> {{ lhs = MathExpression( MUL_OP, lhs, base_expr) }}
                      )*                      {{ return lhs }}


rule base_expr<<V>>: const                         {{ return const }}

                     | var<<V>>                    {{ return var }} 

                     | etype<<V>>                  {{ return etype }} 

                     | func<<V>>                   {{ return func }}

                     | r"\(" added_expr<<V>> r"\)" {{ return added_expr }}


rule func<<V>>: FUNCTION r"\("              {{ F = Function(FUNCTION) }}
                  added_expr<<V>> (         {{ F.append(added_expr) }}
                  ',' added_expr<<V>>             
                  )*                          {{ F.append(added_expr) }}
                  r"\)"                       {{ return F }} 


rule var<<V>>: VARIABLE {{ return VariableRef(V.get_variable(VARIABLE)) }} 

rule etype<<V>>: E_TYPE {{ return V.get_etype(E_TYPE) }} 


rule const: NULL       {{ return Constant('NULL', None) }}
          | DATE       {{ return Constant(DATE.upper(), 'Date') }}
          | DATETIME   {{ return Constant(DATETIME.upper(), 'Datetime') }}
          | TRUE       {{ return Constant(True, 'Boolean') }}
          | FALSE      {{ return Constant(False, 'Boolean') }}
          | FLOAT      {{ return Constant(float(FLOAT), 'Float') }}
          | INT        {{ return Constant(int(INT), 'Int') }}
          | STRING     {{ return Constant(unquote(STRING), 'String') }}
          | SUBSTITUTE {{ return Constant(SUBSTITUTE[2:-2], 'Substitute') }}
                       
