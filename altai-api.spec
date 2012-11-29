
Name:           altai-api
Version:        0.0.1
Release:        0.1
Summary:        Altai API Implementation
License:        GNU LGPL 2.1
URL:            http://www.griddynamics.com/openstack
Group:          Development

Source:         %{name}-%{version}.tar.gz

Requires:       python-flask >= 0.9
Requires:       python-openstackclient-base
Requires:       python-glanceclient
Requires:       python-keystoneclient
Requires:       python-nova

# for running tests
BuildRequires:  python-mox

%description
Altai REST API is programming interface to Altai Private Cloud for
Developers.  The goal of Altai REST API is to provide clean, reliable
and small but complete interface for private cloud management that will
be easy to learn, use and implement on wide range of backends.

This package provides service implementing the API.


%prep
%setup -q -n %{name}-%{version}

%build
echo 'This is early development version, no package should be build.'
exit 1

%changelog
* Thu Nov 29 2012 Ivan A. Melnikov <imelnikov@griddynamics.com> - 0.0.1-1
- Initial deliberately unbuildable spec.

