#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Altai API Service
# Copyright (C) 2012 Grid Dynamics Consulting Services, Inc
# All Rights Reserved
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program. If not, see
# <http://www.gnu.org/licenses/>.


from setuptools import setup, find_packages

setup(name='altai-api',
      version=__import__('altai_api').__version__,
      license='GNU LGPL 2.1',
      description='Altai Private Cloud for Developers management API implementation',
      author='GridDynamics Openstack Core Team, (c) GridDynamics',
      author_email='openstack@griddynamics.com',
      url='http://www.griddynamics.com/openstack',

      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      include_package_data=True,

      entry_points={
          'console_scrpits': [
              'altai-apid = altai_api.main:main'
          ]
      },

      install_requires=['Flask >= 0.9', 'python-openstackclient-base'],
      tests_require=['mox'],
      dependency_links=['http://github.com/altai/python-openstackclient-base/zipball/master#egg=python-openstackclient-base'], 

      test_suite='tests',
)

