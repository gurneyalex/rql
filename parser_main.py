""" Copyright (c) 2000-2003 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: parser_main.py,v 1.3 2005-06-09 00:02:37 ludal Exp $"


if __name__ == '__main__':
    from sys import argv
    
    parser = Hercule(HerculeScanner(argv[1]))
    e_types = {}
    # parse the RQL string
    try:
        tree = parser.goal(e_types)
        print '-'*80
        print tree
        print '-'*80
        print repr(tree)
        print e_types
    except SyntaxError, s:
        # try to get error message from yapps
        data = parser._scanner.input
        print_error(data, s, parser._scanner)
