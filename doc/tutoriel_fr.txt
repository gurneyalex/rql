.. -*- coding: utf-8 -*-

.. _tutorielRQL:

============================================
Tutoriel "Relation Query Language" (Hercule)
============================================


Apprenons RQL par la pratique...



Schema
------
Nous supposerons dans la suite de ce document que le schéma de
l'application est le suivant. Les différentes entités
disponibles sont :

:Personne:

::

	nom    varchar(64) NOT NULL
	prenom varchar(64)
	sexe   char(1) DEFAULT 'M' 
	promo  choice('bon','pasbon')
	titre  varchar(128)
	adel   varchar(128)
	web    varchar(128)
	tel    integer
	datenaiss date


:Societe:

::

	nom  varchar(64)
	web varchar(128)
	tel  varchar(15)
	adr  varchar(128)
	cp   varchar(12)
	ville varchar(32)


:Affaire:

::

	sujet varchar(128)
	ref   varchar(12) 


:Note:

::

	diem date
	type char(1)
	para varchar(512)


Et les relations entre elles:

::

	Person travaille_pour Societe
	Person evaluee_par Note
	Societe evaluee_par Note
	Person concerne_par Note
	Person concerne_par Affaire
	Societe concerne_par Affaire


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


L'essentiel
-----------
1. *Toutes les personnes*

   ::
      
      Personne X ;
      ou
      Any X WHERE X is Personne ;


2. *La societé nommé Logilab*

   ::

      Societe S WHERE S nom 'Logilab' ;


3. *Tous les objets ayant un attribut nom commençant par 'Log'*

   ::

      Any S WHERE S nom LIKE 'Log%' ;
      ou 
      Any S WHERE S nom ~= 'Log%' ;

   Cette requête peut renvoyer des objets de type personne et de type
   société.


4. *Toutes les personnes travaillant pour la société nommé Logilab*
   
   ::

      Personne P WHERE P travaille_pour S, S nom "Logilab" ;
      ou
      Personne P WHERE P travaille_pour S AND S nom "Logilab" ;
      ou
      Personne P WHERE P travaille_pour "Logilab" ;

   La dernière forme fonctionne car "nom" est le premier attribut des
   entités de type "Société" XXX nico: toujours vrai ?


5. *Les societés nommées Caesium ou Logilab*

   ::

      Societe S WHERE S nom IN ('Logilab','Caesium') ;
      ou
      Societe S WHERE S nom 'Logilab' OR S nom 'Caesium' ;


6. *Toutes les societés sauf celles nommées Caesium ou Logilab*

   ::

      Societe S WHERE NOT S nom IN ('Logilab','Caesium') ;
      ou
      Societe S WHERE NOT S nom 'Logilab' AND NOT S nom 'Caesium' ;


7. *Les objets évalués par la note d'identifiant 43*

   ::

      Any X WHERE X evaluee_par N, N eid 43 ;


8. *Toutes les personnes triés par date de naissance dans l'ordre antechronologique*

   ::
      
      Any X WHERE X is Personne, X datenaiss D ORDERBY D DESC ;


9. *Toutes les personnes groupées par leur société*

   ::
      
      Personne X WHERE X travaille_pour S GROUPBY S,X ;

   On note qu'il faut définir une variable pour s'en servir pour le
   groupage. De plus les variables séléctionnées doivent être groupées
   (mais les variables groupées ne doivent pas forcément être sélectionnées).

XXX nico: c'est peu utile comme requête
   
Exemples avancés
----------------
1. *Toutes les personnes dont le champ nom n'est pas spécifié (i.e NULL)*

   ::

      Personne P WHERE P nom NULL ;


2. *Toutes les personnes qui ne travaillent pour aucune société*

   ::

      Personne P WHERE NOT P travaille_pour S ;


3. *Toutes les sociétés où la personne nommée toto ne travaille pas*

   ::

      Societe S WHERE NOT P travaille_pour S , P nom 'toto' ;
      ou
      Societe S WHERE NOT 'toto' travaille_pour S ;


4. *Toutes les entités ayant été modifiées entre aujourd'hui et hier*

   ::

      Any X WHERE X modification_date <= today, X modification_date >= today - 1


5. *Toutes les notes n'ayant pas de type et à effectuer dans les 7 jours, triées par date*

   ::

      Any N, D where N is Note, N type NULL, N diem D, N diem >= today,
      N diem < today + 7 ORDERBY D


6. *Les personnes ayant un homonyme (sans doublons)*

   ::

      Personne X,Y where X nom NX, Y nom NX, X eid XE, Y eid > XE
