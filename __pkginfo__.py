# pylint: disable-msg=W0622
# Copyright (c) 2003-2008 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
rql packaging information
"""

modname = "rql"
numversion = (0, 15, 3)
version = '.'.join([str(num) for num in numversion])

license = 'LCL'
copyright = '''Copyright (c) 2003-2008 LOGILAB S.A. (Paris, FRANCE).
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
pyversions = ['2.4']


include_dirs = []
