
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

"""Default settings for service"""

# watch sources and reload service on update
USE_RELOADER = False

# host to listen on
HOST = '0.0.0.0'

# port to listen on
PORT = 5039

# used for test
TEST_STRING = 'Test'

# enable this to make responses readable
PRETTY_PRINT_JSON = False

# keystone administrator credentials, for internal administrative jobs
KEYSTONE_ADMIN = 'admin'
KEYSTONE_ADMIN_PASSWORD = 'admin'
KEYSTONE_URI = 'localhost:5000/v2.0'

# system tenant to use by default
DEFAULT_TENANT = 'systenant'

# audit verbosity -- possible values
# 0: don't write anything to audit log
# 1: write only certain request to audit log
# 2: write everything to audit log
AUDIT_VERBOSITY = 1

# name of Altai installation
DEFAULT_INSTALLATION_NAME = 'Altai Private Cloud for Developers'

# mail configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'guess-who@griddynamics.com'
MAIL_PASSWORD = ''
MAIL_USE_TLS = True
DEFAULT_MAIL_SENDER = ('Altai MailBot', MAIL_USERNAME)
DEFAULT_MAIL_FOOTER = """--
With best regards,
Altai MailBot
"""


# periodic job intervals, in seconds, may be floating point number
RIP_EXPIRED_VMS_TASK_INTERVAL = 10.0
VMS_REMINDER_TASK_INTERVAL = 60.0
VM_DATA_GC_TASK_INTERVAL = 40 * 60.0

