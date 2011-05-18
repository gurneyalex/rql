YAPPS=yapps

parser.py: parser.g parser_main.py
	${YAPPS} parser.g
	#sed -i "s/__main__/old__main__/" parser.py
	#cat parser_main.py >> parser.py