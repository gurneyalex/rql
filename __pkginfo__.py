# pylint: disable-msg=W0622
# Copyright (c) 2003-2006 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
rql packaging information
"""

__revision__ = "$Id: __pkginfo__.py,v 1.20 2006-03-28 10:11:17 syt Exp $"

modname = "rql"
numversion = [0, 4, 2]
version = '.'.join([str(num) for num in numversion])

license = 'LCL'
copyright = '''Copyright (c) 2003-2006 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr'''

author = "Sylvain Thenault"
author_email = "devel@logilab.fr"

short_desc = "relationship query language (RQL) utilities"
long_desc = """A library providing the base utilities to handle RQL queries,
such as a parser, a type inferencer.
"""
web = "" #"http://www.logilab.org/projects/rql"
#ftp = "ftp://ftp.logilab.org/pub/rql"


# debianize info
debian_maintainer = 'Sylvain Thenault'
debian_maintainer_email = 'sylvain.thenault@logilab.fr'
pyversions = ['2.3', '2.4']


include_dirs = []

from distutils.core import Extension
ext_modules = [Extension('rql.rqlparse',
                         ['rqlmodule/rqlmodule.cc',
                          'rqlmodule/nodes.cc',
                          'rqlmodule/rql_parser.cc',
                          'rqlmodule/rql_scanner.cc',
                          'rqlmodule/rql_token.cc',
                          ],
#                         extra_compile_args = ["-O0"],
                         ),
               ]
