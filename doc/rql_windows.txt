Compiling rql for Windows
=========================


:author: Alexandre Fayolle
:date: 2009/09/09

RQL can use either logilab.constraint or gecode to perform type
inference. This document explains how the gecode support can be added
for the Windows platform. 

The short way
-------------

Download and install http://ftp.logilab.org/pub/rql/rql-0.23.0.win32-py2.5.exe

The long way
------------

Problem statement: we want to use python2.5 on windows. Compiling C
extensions requires Visual Studio 2003, but Gecode requires Visual
Studio 2008. So we are stuck with using MinGW, and then again Gecode
requires gcc 4.2 or later and cygwin to support building. 
But cygwin doesn't come with a mingw enabled gcc 4.x (only 3.x
available), so some stiching is required. 

Dependencies installation
~~~~~~~~~~~~~~~~~~~~~~~~~

* cygwin_: download http://www.cygwin.com/setup.exe, run it and select the following
  packages:

  - diffutils
  - perl
  - g++-mingw
  - some text editor of your choice (nano, vim...)

* mingw_: download the following files:

  - `gcc-g++-4.4.0-bin <http://sourceforge.net/projects/mingw/files/GCC%20Version%204/Current%20Release_%20gcc-4.4.0/gcc-c%2B%2B-4.4.0-mingw32-bin.tar.gz/download>`_

  - `gcc-g++-4.4.0-dll <http://sourceforge.net/projects/mingw/files/GCC%20Version%204/Current%20Release_%20gcc-4.4.0/gcc-c%2B%2B-4.4.0-mingw32-dll.tar.gz/download>`_

  - `gcc-core-4.4.0-bin <http://sourceforge.net/projects/mingw/files/GCC%20Version%204/Current%20Release_%20gcc-4.4.0/gcc-core-4.4.0-mingw32-bin.tar.gz/download>`_

  - `gcc-core-4.4.0-dll <http://sourceforge.net/projects/mingw/files/GCC%20Version%204/Current%20Release_%20gcc-4.4.0/gcc-core-4.4.0-mingw32-dll.tar.gz/download>`_

 - `gmp-4.2.4-dll <http://sourceforge.net/projects/mingw/files/GCC%20Version%204/Current%20Release_%20gcc-4.4.0/gmp-4.2.4-mingw32-dll.tar.gz/download>`_

 - `mpfr-2.4.1-dll <http://sourceforge.net/projects/mingw/files/GCC%20Version%204/Current%20Release_%20gcc-4.4.0/mpfr-2.4.1-mingw32-dll.tar.gz/download>`_

 - `binutils-2.19.1-bin <http://sourceforge.net/projects/mingw/files/GNU%20Binutils/Current%20Release_%20GNU%20binutils-2.19.1/binutils-2.19.1-mingw32-bin.tar.gz/download>`_

 - `w32api-3.13-dev <http://sourceforge.net/projects/mingw/files/MinGW%20API%20for%20MS-Windows/Current%20Release_%20w32api-3.13/w32api-3.13-mingw32-dev.tar.gz/download>`_

  - `mingwrt-3.15.2-dev <http://sourceforge.net/projects/mingw/files/MinGW%20Runtime/mingwrt-3.15.2/mingwrt-3.15.2-mingw32-dev.tar.gz/download>`_


Create ``c:\MinGW``. Launch a cygwin shell, go to ``/cygdrive/c/MinGW`` and
untar all the mingw tarballs

Edit ``/etc/profile`` and go to the place where the ``PATH`` environment
variable is set. Change the line to *prepend*
``/cygdrive/c/MinGW/bin:/cygdrive/c/MinGW/libexec/mingw32/4.4.0`` to the ``PATH``

* download and untar `Gecode 3.1.0 source distribution <http://www.gecode.org/download/gecode-3.1.0.tar.gz>`_.


Compiling gecode
~~~~~~~~~~~~~~~~

In a cygwin shell, go the the untarred Gecode source directory and run::

  $ ./configure --enable-version-specific-runtime-libs \
                --disable-shared --disable-qt --disable-gist \
                --disable-examples --enable-static

Edit gecode/support/config.hpp, and change the line ::

  #define GECODE_USE_GETTIMEOFDAY 1

to::

  #define GECODE_USE_CLOCK 1

run::

  $ make CXXFLAGS="-I. -O1 -DNDEBUG -Wextra -Wall -pipe -ggdb \
  -fno-strict-aliasing -ffast-math -mthreads -DGECODE_BUILD_SUPPORT -static-libgcc"

While this runs, consider renting some Bollywood movie (I enjoyed `this one
<http://www.imdb.com/title/tt0172684/>`_) and watching it.


Compiling the C extension in rql
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

in a Windows shell (aka "DOS Console"), go the the rql directory and
run::

 $ set PATH=%PATH%;c:\MinGW\bin;c:\MinGW\libexec\mingw32\4.4.0
 $ python setup.py build_ext -c mingw32 \
                             -Ic:\temp\gecode-3.1.0 \
                             -Lc:\temp\gecode-3.1.0 
                             --in-place

Test
~~~~

Open a new console (to get the default ``PATH``). Go to the parent
directory of rql. Launch the Python interpreter, and type::

 >>> import rql.analyze

If this works, congratulation, you're done. 



.. _cygwin: http://www.cygwin.com
.. _mingw: http://www.mingw.org

