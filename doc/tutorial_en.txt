.. -*- coding: utf-8 -*-

.. _tutorielRQL:

==================================
"Relation Query Language" tutorial
==================================


Let's discover RQL with examples.


Schema
------

We will assume the following data model.

:Person:

::

	name      varchar(64) NOT NULL
	firstname varchar(64)
	sex       char(1) DEFAULT 'M' 
	title     varchar(128)
	email     varchar(128)
	web       varchar(128)
	tel       integer
	birthdate date


:Company:

::

	name  varchar(64)
	web   varchar(128)
	tel   varchar(15)
	adr   varchar(128)
	cp    varchar(12)
	city  varchar(32)


:Workcase:

::

	title varchar(128)
	ref   varchar(12) 


:Comment:

::

	diem date
	type char(1)
	para varchar(512)


with relationships:

::

	Person works_for Company
	Person commented_by Comment
	Company commented_by Comment
	Person concerned_by Workcase
	Company concerned_by Workcase


Toutes les entités ont un attribut supplémentaire 'eid', permettant
d'identifier chaque instance de manière unique.

De plus si les métadonnées sont utilisées, vous disposez pour chaque
type d'entité des relations "creation_date", "modification_date" dont
l'objet est une entité de type Dates (il y a un "s" pour ne pas avoir
de conflit avec le type de base "date"), ainsi que de la relation
"owned_by" dont l'objet est une entité de type Euser. Les schemas
standards de ces types d'entités sont les suivants :

:Dates:

::

	day date


:Euser:

::

	login  	  varchar(64) not null
	firstname varchar(64)
	surname   varchar(64)
	password  password
	role      choice('admin','user','anonymous') default 'user'
	email  	  varchar(128)
	web    	  varchar(128)
	birthday  date

Enfin, il existe la relation spéciale "is" permettant de spécifier le
type d'une variable. 


Essentials
----------

1. *Alls persons*

   ::
      
      Person X ;
      or
      Any X WHERE X is Person ;


2. *The company namend Logilab*

   ::

      Company S WHERE S name 'Logilab' ;


3. *All entities with a name starting with 'Log'*

   ::

      Any S WHERE S name LIKE 'Log%' ;
      or 
      Any S WHERE S name ~= 'Log%' ;

   This query can return entities of type Person and Company.


4. *All persons working for a company named Logilab*
   
   ::

      Person P WHERE P works_for S, S name "Logilab" ;
      or
      Person P WHERE P works_for S AND S name "Logilab" ;
      or
      Person P WHERE P works_for "Logilab" ;

   La dernière forme fonctionne car "nom" est le premier attribut des
   entités de type "Société" XXX nico: toujours vrai ?


5. *Companies named Caesium or Logilab*

   ::

      Company S WHERE S name IN ('Logilab','Caesium') ;
      or
      Company S WHERE S name 'Logilab' OR S name 'Caesium' ;


6. *All companies that are not named Caesium or Logilab*

   ::

      Company S WHERE NOT S name IN ('Logilab','Caesium') ;
      or
      Company S WHERE NOT S name 'Logilab' AND NOT S name 'Caesium' ;


7. *All entities commented by the entity number 43*

   ::

      Any X WHERE X commented_by N, N eid 43 ;


8. *All persons sorted by birth date in descending order*

   ::
      
      Any X WHERE X is Person, X birthdate D ORDERBY D DESC ;


9. *All persons grouped by company*

   ::
      
      Person X WHERE X works_for S GROUPBY S,X ;

   On note qu'il faut définir une variable pour s'en servir pour le
   groupage. De plus les variables séléctionnées doivent être groupées
   (mais les variables groupées ne doivent pas forcément être sélectionnées).

XXX nico: c'est peu utile comme requête
   
Exemples avancés
----------------
1. *All persons that have an empty name (i.e NULL)*

   ::

      Person P WHERE P name NULL ;


2. *All persons that do not work for a company*

   ::

      Person P WHERE NOT P works_for S ;


3. *All the companies that the person named 'toto' does not work for*

   ::

      Company S WHERE NOT P works_for S , P name 'toto' ;
      or
      Company S WHERE NOT 'toto' works_for S ;


4. *All the entities modified yesterday and today*

   ::

      Any X WHERE X modification_date <= today, X modification_date >= today - 1


5. *All the comments without type that required action within 7 days, sorted by date*


   ::

      Any N, D where N is Comment, N type NULL, N diem D, N diem >= today,
      N diem < today + 7 ORDERBY D


6. *All persons that have homonyms (each name listed only once)*

   ::

      Person X,Y where X name NX, Y name NX, X eid XE, Y eid > XE
