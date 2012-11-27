
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

"""Default settings for service
"""

# debug: disabled by default
DEBUG = False

# host to listen on
HOST = '0.0.0.0'

# port to listen on
PORT = 5039

# used for test
TEST_STRING = 'Test'

# enable this to make responses readable
PRETTY_PRINT_JSON = False

# the way we authorize users; possible values:
# 'keystone': use keystone for authorization
# 'noneatall': does not work, used to run some simple unit tests
AUTHORIZATION_MODE = 'keystone'

# keystone administrator credentials, for internal administrative tasks
KEYSTONE_ADMIN = 'admin'
KEYSTONE_ADMIN_PASSWORD = 'admin'
KEYSTONE_URI = 'localhost:5000/v2.0'

# system tenant to use by default
DEFAULT_TENANT = 'systenant'

