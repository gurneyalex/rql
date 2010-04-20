# pylint: disable-msg=W0622
"""RQL packaging information.

:copyright: 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

modname = "rql"
numversion = (0, 26, 0)
version = '.'.join(str(num) for num in numversion)

license = 'LGPL'

author = "Logilab"
author_email = "contact@logilab.fr"

short_desc = "relationship query language (RQL) utilities"
long_desc = """A library providing the base utilities to handle RQL queries,
such as a parser, a type inferencer.
"""
web = "http://www.logilab.org/project/rql"
ftp = "ftp://ftp.logilab.org/pub/rql"

pyversions = ['2.4']


import os, subprocess, sys
from distutils.core import Extension

include_dirs = []

def gecode_version():
    import os, subprocess
    version = [1, 3, 1]
    if os.path.exists('data/gecode_version.cc'):
        try:
            res = os.system("g++ -o gecode_version data/gecode_version.cc")
            p = subprocess.Popen("./gecode_version", stdout=subprocess.PIPE)
            vers = p.stdout.read()
            version = [int(c) for c in vers.strip().split('.')]
        except OSError:
            pass
    return version

def encode_version(a,b,c):
    return ((a<<16)+(b<<8)+c)

GECODE_VERSION = encode_version(*gecode_version())

if sys.platform != 'win32':
    ext_modules = [Extension('rql_solve',
                             ['gecode_solver.cpp'],
                              libraries=['gecodeint', 'gecodekernel', 'gecodesearch',],
                             extra_compile_args=['-DGE_VERSION=%s' % GECODE_VERSION],
                         )
                   ]
else:
    ext_modules = [ Extension('rql_solve',
                              ['gecode_solver.cpp'],
                              libraries=['gecodeint', 'gecodekernel', 'gecodesearch',],
                              extra_compile_args=['-DGE_VERSION=%s' % GECODE_VERSION],
                              extra_link_args=['-static-libgcc'],
                              )
                    ]

install_requires = [
    'logilab-common >= 0.47.0',
    'logilab-database',
    'yapps2 >= 2.1.1',
    ]

# links to download yapps2 package that is not (yet) registered in pypi
dependency_links = [
    "http://ftp.logilab.org/pub/yapps/yapps2-2.1.1.zip#egg=yapps2-2.1.1",
    ]
