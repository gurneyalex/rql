# pylint: disable-msg=W0622
# copyright 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of rql.
#
# rql is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# rql is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with rql. If not, see <http://www.gnu.org/licenses/>.
"""RQL packaging information."""
__docformat__ = "restructuredtext en"

modname = "rql"
numversion = (0, 26, 1)
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


import os, subprocess, sys
from distutils.core import Extension

include_dirs = []

def gecode_version():
    import os, subprocess
    version = [3,3,1]
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
                              libraries=['GecodeInt-3-3-1-r-x86', 
                                         'GecodeKernel-3-3-1-r-x86', 
                                         'GecodeSearch-3-3-1-r-x86',
                                         'GecodeSupport-3-3-1-r-x86',
                                         ],
                              extra_compile_args=['/DGE_VERSION=%s' % GECODE_VERSION, '/EHsc'],
                              #extra_link_args=['-static-libgcc'],
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
