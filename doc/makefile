MKHTML=mkdoc
MKHTML_OPT=--doctype book --param division.toc.section.depth=1  --target html --stylesheet single-file

SRC=.


all: specifications_fr.html tutoriel_fr.html


specifications_fr.html: ${SRC}/specifications_fr.txt
	${MKHTML} ${MKHTML_OPT} ${SRC}/specifications_fr.txt

tutoriel_fr.html :${SRC}/tutoriel_fr.txt
	${MKHTML} ${MKHTML_OPT} ${SRC}/tutoriel_fr.txt


clean:
	rm -f *.html
