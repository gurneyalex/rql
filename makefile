YAPPS=yapps

rql/parser.py: rql/parser.g rql/parser_main.py
	${YAPPS} rql/parser.g
	#sed -i "s/__main__/old__main__/" rql/parser.py
	#cat rql/parser_main.py >> rql/parser.py
