"""Main parser command.

:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

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
    except SyntaxError, ex:
        # try to get error message from yapps
        from yapps.runtime import print_error
        print_error(ex, parser._scanner)
