YAPPS=yapps
#python thirdparty/yapps2.py

parser.py: parser.g parser_main.py
	${YAPPS} parser.g
	#sed "s/from yappsrt import/from thirdparty.yappsrt import/" parser.py > tmp.py
	sed -i "s/__main__/old__main__/" parser.py
	cat parser_main.py >> parser.py