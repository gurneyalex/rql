%if 0%{?el5}
%define python python26
%define __python /usr/bin/python2.6
%{!?python_scriptarch: %define python_scriptarch %(%{__python} -c "from distutils.sysconfig import get_python_lib; from os.path import join; print join(get_python_lib(1, 1), 'scripts')")}
%else
%define python python
%define __python /usr/bin/python
%endif

Name:           %{python}-rql
Version:        0.33.2
Release:        logilab.1%{?dist}
Summary:        relationship query language (RQL) utilities

Group:          Development/Languages/Python
License:        LGPLv2+
URL:            http://www.logilab.org/project/rql
Source0:        http://download.logilab.org/pub/rql/rql-%{version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

BuildRequires:  %{python}-devel
BuildRequires:  %{python}-setuptools
BuildRequires:  gecode-devel
Requires:       %{python}
Requires:       %{python}-logilab-common >= 0.47.0
Requires:       %{python}-logilab-database >= 1.6.0
Requires:       %{python}-yapps2 >= 2.1.1
Requires:       %{python}-logilab-constraint >= 0.5.0
Requires:       %{python}-six >= 1.4.0
Requires:       %{python}-setuptools


%description
relationship query language (RQL) utilities

%prep
%setup -q -n rql-%{version}

%build
%{__python} setup.py build
%if 0%{?el5}
# change the python version in shebangs
find . -name '*.py' -type f -print0 |  xargs -0 sed -i '1,3s;^#!.*python.*$;#! /usr/bin/python2.6;'
%endif

%install
NO_SETUPTOOLS=1 %{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT %{?python_scriptarch: --install-scripts=%{python_scriptarch}}

%clean
rm -rf $RPM_BUILD_ROOT

%files 
%defattr(-, root, root)
/*

