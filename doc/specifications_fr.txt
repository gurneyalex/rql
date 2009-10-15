.. -*- coding: utf-8 -*-

=================================================
Spécification "Relation Query Language" (Hercule)
=================================================

:Author: Sylvain Thénault
:Organization: Logilab
:Version: $Revision: 1.10 $
:Date: $Date: 2004-05-18 15:04:13 $

Introduction
============

Objectifs de RQL
----------------

L'objectif est d'avoir un langage mettant l'accent sur le parcours de
relations. A ce titre les attributs seront donc considérés comme des cas
particuliers de relations (au niveau de l'implémentation, l'utilisateur du
langage ne devant quasiment pas voir de différence entre un attribut et une
relation).

RQL s'inspire de SQL mais se veut plus haut niveau. Une connaissance du schéma
Cubicweb définissant l'application est nécessaire.


Comparaison avec des langages existants
---------------------------------------

SQL
```
RQL s'inspire des fonctionnalités de SQL mais se veut à un plus haut niveau
(l'implémentation actuelle de RQL génère du SQL). Pour cela il se limite au
parcours de relations et introduit des variables. L'utilisateur n'a pas besoin
de connaitre le modèle SQL sous-jacent, mais uniquement le schéma Erudi
définissant l'application.

Versa
`````
Faudrait que je regarde plus en détail, mais voilâ déja quelques idées pour
l'instant...  Versa_ est le langage ressemblant le plus à ce que nous voulions
faire, mais le modèle de donnée sous-jacent étant du RDF, il y a un certain
nombre de choses tels que les namespaces ou la manipulation des types RDF qui
ne nous intéressent pas. Niveau fonctionnalité, Versa_ est très complet
notamment grâce à de nombreuses fonctions de conversion et de manipulations
des types de base, dont il faudra peut-être s'inspirer à un moment ou à
l'autre.  Enfin, La syntaxe est un peu ésotérique.

Voir aussi
``````````
RDFQL_


Les différents types de requêtes
--------------------------------

Recherche (`Any`)
  Ce type de requête permet d'extraire des entités ou des attributs d'entités.

Insertion d'entités (`INSERT`)
  Ce type de requête permet d'insérer de nouvelles entités dans la base. On
  permettra également la création directe de relations sur les entités
  nouvellement créées.

Mise à jour d'entités, création de relations (`SET`)
  Ce type de requête permet de mettre à jours des entités existantes dans la base,
  ou de créer des relations entres des entités existantes.

Suppression d'entités ou de relation (`DELETE`)
  Ce type de requête permet de supprimer des entités et relations existantes dans
  la base.



Exemples
========

(voir le tutoriel :ref:`tutorielRQL` pour plus d'exemples)

Requête de recherche
--------------------

  [`DISTINCT`] <type d'entité> V1(, V2)\*
  [`GROUPBY` V1(, V2)\*]  [`ORDERBY` <orderterms>]
  [`WHERE` <restriction>] 
  [`LIMIT` <value>] [`OFFSET` <value>]

:type d'entité:
  Type de la ou des variables séléctionnées. 
  Le type spécial `Any`, revient à ne pas spécifier de type.
:restriction:
  liste des relations à parcourir sous la forme 
    `V1 relation V2|<valeur constante>`
:orderterms:
  Définition de l'ordre de selection : variable ou n° de colonne suivie de la
  méthode de tri (`ASC`, `DESC`), ASC étant la valeur par défaut.
:note pour les requêtes groupées:
  Pour les requêtes groupées (i.e. avec une clause `GROUPBY`), toutes les
  variables sélectionnée doivent être soit groupée soit aggrégée.



- *recherche de l'objet ayant l'identifiant 53*
  ::

       Any X WHERE 
       X eid 53 

- *recherche des documents de type bande dessinée, appartenant à syt et disponible*
  ::

       Document X WHERE 
       X occurence_of F, F class C, C name 'Bande dessinée',
       X owned_by U, U login 'syt',
       X available true

- *recherche des personnes travaillant pour eurocopter intéressé par la formation*
  ::

       Personne P WHERE
       P travaille_pour S, S nom 'Eurocopter',
       P interesse_par T, T nom 'formation'

- *recherche des notes de moins de 10 jours écrites par jphc ou ocy*
  ::

       Note N WHERE
       N ecrit_le D, D day > (today -10), 
       N ecrit_par P, P nom 'jphc' or P nom 'ocy'

- *recherche des personnes intéressées par la formation ou habitant à Paris*
  ::

       Personne P WHERE
       (P interesse_par T, T nom 'formation') or
       (P ville 'Paris')

- *Le nom et le prénom de toutes les personnes*
  ::

       Any N, P WHERE
       X is Personne, X nom N, X prenom P

  On remarquera que la selection de plusieurs entités force généralement
  l'utilisation de "Any", car la spécification de type s'applique sinon
  à toutes les variables séléctionnées. On aurait pu écrire ici 
  ::

       String N, P WHERE
       X is Personne, X nom N, X prenom P


Requête d'insertion
-------------------
   `INSERT` <type d'entité> V1(, <type d'entité> V2)\* `:` <assignements>
   [`WHERE` <restriction>] 

:assignements:
  liste des relations à assigner sous la forme `V1 relation V2|<valeur constante>`

La restriction permet de définir des variables utilisées dans les assignements.

Attention, si une restriction est spécifiée, l'insertion est effectuée *pour
chaque ligne de résultat renvoyée par la restriction*.

- *insertion d'une nouvelle personne nommée 'bidule'*
  ::

       INSERT Personne X: X nom 'bidule'

- *insertion d'une nouvelle personne nommée 'bidule', d'une autre nommée 'chouette' et d'une relation 'ami' entre eux*
  ::

       INSERT Personne X, Personne Y: X nom 'bidule', Y nom 'chouette', X ami Y

- *insertion d'une nouvelle personne nommée 'bidule' et d'une relation 'ami' avec une personne existante nommée 'chouette'*
  ::

       INSERT Personne X: X nom 'bidule', X ami Y WHERE Y nom 'chouette'


Requête de mise à jour, création de relations
---------------------------------------------
   `SET` <assignements>
   [`WHERE` <restriction>] 

Attention, si une restriction est spécifiée, la mise à jour est effectuée *pour
chaque ligne de résultat renvoyée par la restriction*.

- *renommage de la personne nommée 'bidule' en 'toto', avec modification du prénom*
  ::

       SET X nom 'toto', X prenom 'original' WHERE X is Person, X nom 'bidule'

- *insertion d'une relation de type 'connait' entre les objets reliés par la relation de type 'ami'*
  ::

       SET X know Y WHERE X ami Y


Requête de suppression
----------------------
   `DELETE` (<type d''entité> V) | (V1 relation v2),...
   [`WHERE` <restriction>] 

Attention, si une restriction est spécifiée, la suppression est effectuée *pour
chaque ligne de résultat renvoyée par la restriction*.

- *supression de la personne nommé 'toto'*
  ::

       DELETE Person X WHERE X nom 'toto'

- *suppression de toutes les relations de type 'ami' partant de la personne nommée 'toto'*
  ::

       DELETE X ami Y WHERE X is Person, X nom 'toto'



Définition du langage
=====================

Mots clés réservés
------------------
Les mots clés ne sont pas sensibles à la casse.

::

    DISTINCT, INSERT, SET, DELETE,
    WHERE, AND, OR, NOT
    IN, LIKE, ILIKE,
    TRUE, FALSE, NULL, TODAY, NOW
    GROUPBY, ORDERBY, ASC, DESC


Variables et Typage
-------------------

Au niveau de RQL, on ne fait pas de distinction entre entités et attributs. La
valeur d'un attribut est considérée comme une entité d'un type particulier (voir
ci-dessous), lié à une (vraie) entité par une relation du nom de l'attribut.

Les entités et valeurs à parcourir et / ou séléctionner sont représentées dans
la requête par des *variables* qui doivent être écrites en majuscule.

Il existe un type spécial **Any**, revenant à ne pas spécifier de type.

On peut contraindre les types possibles pour une variable à l'aide de la
relation spéciale **is**.

Le(s) type(s) possible(s) pour chaque variable est déduit du schema en
fonction des contraintes exprimées ci-dessus et à l'aide des relations entre
chaque variable.

Types de bases
``````````````

Les types de bases supportés sont les chaines (entre doubles ou simples quotes),
les nombres entiers ou flottant (le séparateur étant le '.'), les dates et les
booléens. On s'attend donc à recevoir un schéma dans lequel les types String,
Int, Float, Date et Boolean sont définis.

* `String` (litéral: entre doubles ou simples quotes).
* `Int`, `Float` (le séparateur étant le '.').
* `Date`, `Datetime`, `Time` (litéral: chaîne YYYY/MM/DD[ hh:mm] ou mots-clés
  `TODAY` et `NOW`).
* `Boolean` (mots-clés `TRUE` et `FALSE`).
* mot-clé `NULL`.


Opérateurs
----------

Opérateurs logiques
```````````````````
::

    AND, OR, ','

"," est équivalent à "AND" mais avec la plus petite priorité parmi les
opérateurs logiques (voir `Priorité des opérateurs`_).

Opérateurs mathématiques
````````````````````````
::

    +, -, *, /

Opérateurs de comparaison
`````````````````````````
::

    =, <, <=, >=, >, ~=, IN, LIKE, ILIKE

* L'opérateur `=` est l'opérateur par défaut.

* L'opérateur `LIKE` équivalent à `~=` permet d'utiliser le caractère `%` dans
  une chaine de caractère pour indiquer que la chaîne doit commencer ou terminer
  par un préfix/suffixe::

    Any X WHERE X nom ~= 'Th%'
    Any X WHERE X nom LIKE '%lt'

* L'opérateur `ILIKE` est une version de `LIKE` qui n'est pas sensible à la
  casse.

* L'opérateur `IN` permet de donner une liste de valeurs possibles::

    Any X WHERE X nom IN ('chauvat', 'fayolle', 'di mascio', 'thenault')


XXX nico: A truc <> 'titi' ne serait-il pas plus pratique que NOT A
truc 'titi' ?

Priorité des opérateurs
```````````````````````

1. '*', '/'

2. '+', '-'

3. 'and'

4. 'or'

5. ','


Fonctionnalités avancées
------------------------

Fonctions d'aggrégat
````````````````````
::

    COUNT, MIN, MAX, AVG, SUM

Fonctions sur les chaines
`````````````````````````
::

    UPPER, LOWER

Relations optionnelles
``````````````````````

* Elles permettent de sélectionner des entités liées ou non à une autre.

* Il faut utiliser le `?` derrière la variable pour spécifier que la relation
  vers celle-ci est optionnelle :

  - Anomalies d'un projet attachées ou non à une version ::

      Any X,V WHERE X concerns P, P eid 42, X corrected_in V?

  - Toutes les fiches et le projet qu'elles documentent le cas échéant ::

      Any C,P WHERE C is Card, P? documented_by C



Grammaire BNF
-------------
Les éléments terminaux sont en majuscules, les non-terminaux en minuscule. La
valeur des éléments terminaux (entre quotes) correspond à une expression
régulière Python.
:: 

    statement ::= (select | delete | insert | update) ';'


    # select specific rules
    select ::= 'DISTINCT'? E_TYPE selected_terms restriction? group? sort?

    selected_terms ::= expression (',' expression)*

    group       ::= 'GROUPBY' VARIABLE (',' VARIABLE)*

    sort        ::= 'ORDERBY' sort_term (',' sort_term)*

    sort_term   ::= VARIABLE sort_method? 

    sort_method ::= 'ASC' | 'DESC'


    # delete specific rules
    delete ::= 'DELETE' (variables_declaration | relations_declaration) restriction?


    # insert specific rules
    insert ::= 'INSERT' variables_declaration (':' relations_declaration)? restriction?


    # update specific rules
    update ::= 'SET' relations_declaration restriction


    # common rules
    variables_declaration ::= E_TYPE VARIABLE (',' E_TYPE VARIABLE)*

    relations_declaration ::= simple_relation (',' simple_relation)*

    simple_relation ::= VARIABLE R_TYPE expression

    restriction ::= 'WHERE' relations

    relations   ::= relation (LOGIC_OP relation)*
                  | '(' relations ')'

    relation ::= 'NOT'? VARIABLE R_TYPE COMP_OP? expression 
               | 'NOT'? VARIABLE R_TYPE 'IN' '(' expression (',' expression)* ')'
    
    expression ::= var_or_func_or_const (MATH_OP var_or_func_or_const)*
                 | '(' expression ')'

    var_or_func_or_const ::= VARIABLE | function | constant

    function ::= FUNCTION '(' expression (',' expression)* ')'

    constant ::= KEYWORD | STRING | FLOAT | INT

    # tokens
    LOGIC_OP ::= ',' | 'OR' | 'AND'
    MATH_OP  ::= '+' | '-' | '/' | '*'
    COMP_OP  ::= '>' | '>=' | '=' | '<=' | '<' | '~=' | 'LIKE' 

    FUNCTION ::= 'MIN' | 'MAX' | 'SUM' | 'AVG' | 'COUNT' | 'UPPER' | 'LOWER'

    VARIABLE ::= '[A-Z][A-Z0-9]*'
    E_TYPE   ::= '[A-Z]\w*'
    R_TYPE   ::= '[a-z_]+'

    KEYWORD  ::= 'TRUE' | 'FALSE' | 'NULL' | 'TODAY' | 'NOW'
    STRING   ::= "'([^'\]|\\.)*'" | '"([^\"]|\\.)*\"'
    FLOAT    ::= '\d+\.\d*'
    INT      ::= '\d+'


Remarques
---------

Tri et groupes
``````````````

- pour les requêtes groupées (i.e. avec une clause GROUPBY), toutes les
  variables sélectionnées doivent être groupées

- pour grouper ou/et trier sur les attributs on peut faire : "X,L user U, U
  login L GROUPBY L,X ORDERBY L"

- si la méthode de tri (SORT_METHOD) n'est pas précisée, alors le tri est
  ascendant.

Négation
````````

* Une requête du type `Document X WHERE NOT X owned_by U` revient à dire "les
  documents n'ayant pas de relation `owned_by`". 
* En revanche la requête `Document X WHERE NOT X owned_by U, U login "syt"`
  revient à dire "les  documents n'ayant pas de relation `owned_by` avec
  l'utilisateur syt". Ils peuvent avoir une relation "owned_by" avec un autre
  utilisateur.

Identité
````````

On peut utiliser la relation spéciale `identity` dans une requête pour
rajouter une contrainte d'identité entre deux variables. C'est l'équivalent
du ``is`` en python::

  Any A WHERE A comments B, A identity B

retournerait l'ensemble des objets qui se commentent eux-mêmes. La relation
`identity` est surtout pratique lors de la définition des règles de sécurités
avec des `RQLExpressions`.

Implémentation
==============

Représentation interne (arbre syntaxique)
-----------------------------------------

L'arbre de recherche ne contient pas les variables sélectionnées (i.e. on n'y 
trouve que ce qui suit le "WHERE").

L'arbre d'insertion ne contient pas les variables insérées ni les relations 
définies sur ces variables (i.e. on n'y trouve que ce qui suit le
"WHERE").

L'arbre de suppression ne contient pas les variables ou relations supprimées 
(i.e. on n'y trouve que ce qui suit le "WHERE").

L'arbre de mise à jour ne contient pas les variables ou relations mises à jour
(i.e. on n'y trouve que ce qui suit le "WHERE").

::

    Select         ((Relation|And|Or)?, Group?, Sort?)
    Insert         (Relation|And|Or)?
    Delete         (Relation|And|Or)?
    Update         (Relation|And|Or)?

    And            ((Relation|And|Or), (Relation|And|Or))
    Or             ((Relation|And|Or), (Relation|And|Or))

    Relation       ((VariableRef, Comparison))

    Comparison     ((Function|MathExpression|Keyword|Constant|VariableRef)+)

    Function       (())
    MathExpression ((MathExpression|Keyword|Constant|VariableRef), (MathExpression|Keyword|Constant|VariableRef))

    Group          (VariableRef+)
    Sort           (SortTerm+)
    SortTerm       (VariableRef+)

    VariableRef ()
    Variable    ()
    Keyword     ()
    Constant    ()


Remarques
---------

- l'implémentation actuelle ne supporte pas de lier deux relations ayant comme
  type de relation 'is' avec un OR. Je ne pense pas que la négation ne
  soit supportée non plus sur ce type de relation (à confirmer).

- les relations définissant les variables doivent être à gauche de celles les
  utilisant. Par exemple ::

    Point P where P abs X, P ord Y, P value X+Y

  est valide, mais ::

    Point P where P abs X, P value X+Y, P ord Y

  ne l'est pas.



Conclusion
==========

Limitations
-----------

Il manque pour l'instant:

- COALESCE

- restriction sur les groupes (HAVING)

et certainement d'autres choses...

Un inconvénient est que pour utiliser ce langage il faut bien connaitre le
schéma utilisé (avec les vrais noms de relations et d'entités, pas ceux affichés
dans l'interface utilisateur). D'un autre coté, on peut pas vraiment contourner
cela, et c'est le boulot d'une interface utilisateur de cacher le RQL.


Sujets de réflexion
-------------------

Il serait pratique de pouvoir exprimer dans le schema des correspondances de
relations (règles non récursives)::

    Document class Type <-> Document occurence_of Fiche class Type
    Fiche class Type    <-> Fiche collection Collection class Type
    
Ainsi 1. devient::

    Document X where 
    X class C, C name 'Bande dessinée',
    X owned_by U, U login 'syt',
    X available true

Je ne suis cependant pas sûr qu'il faille gérer ça au niveau de RQL...

Il faudrait aussi une relation spéciale 'anonyme'.



.. _Versa: http://uche.ogbuji.net/tech/rdf/versa/
.. _RDFQL: http://www.w3.org/TandS/QL/QL98/pp/rdfquery.html
