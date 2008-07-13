MKHTML=mkdoc
MKHTML_OPT=--doctype book --param division.toc.section.depth=1  --target html --stylesheet single-file

SRC=.

all: specifications_fr.html tutoriel_fr.html epydoc


specifications_fr.html: ${SRC}/specifications_fr.txt
	${MKHTML} ${MKHTML_OPT} ${SRC}/specifications_fr.txt

tutoriel_fr.html :${SRC}/tutoriel_fr.txt
	${MKHTML} ${MKHTML_OPT} ${SRC}/tutoriel_fr.txt


epydoc:
	epydoc --html -o apidoc -v --graph all --no-private --exclude="__pkginfo__" --exclude="setup" -n "RQL Module" ../

clean:
	rm -f *.html
	rm -rf apidoc
