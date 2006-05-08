from distutils.core import setup, Extension

ext = Extension('cscan',
                sources = ['scan.c'])

setup (name = 'cscan',
       version = '1.0',
       description = 'This is a demo package',
       ext_modules = [ext])
