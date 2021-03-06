Name: python-maps
Version: 4.2.0
Release: 2%{?dist}
BuildArch: noarch
Summary: Python's missing mappings
Source0: %{name}-%{version}.tar.gz
License: MIT
URL: https://github.com/pcattori/maps

BuildRequires: python-urllib3
BuildRequires: python2-devel
BuildRequires: python-setuptools

Requires: python-six

%description
Python dictionaries with items also accessible via dot-notation

%prep
%setup

# Remove bundled egg-info
rm -rf %{name}.egg-info

%build
%{__python} setup.py build

%install
%{__python} setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%files -f INSTALLED_FILES

%changelog


