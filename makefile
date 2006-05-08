YAPPS=python thirdparty/yapps2.py

parser.py: parser.g parser_main.py
	${YAPPS} parser.g
	sed "s/from yappsrt import/from thirdparty.yappsrt import/" parser.py > tmp.py
	sed "s/__main__/old__main__/" tmp.py > parser.py
	rm tmp.py
	cat parser_main.py >> parser.py