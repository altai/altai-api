
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2012-2013 Grid Dynamics Consulting Services, Inc
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

# credentials for Altai API superuser
ALTAI_API_SUPERUSER = 'altai_api_superuser'
ALTAI_API_SUPERUSER_PASSWORD = '9b7ba716-e418-4123-857f-3a19aed44916'

# OpenStack endpoint
KEYSTONE_URI = 'localhost:5000/v2.0'

# system tenant name
SYSTENANT = 'systenant'

# audit verbosity -- possible values
# 0: don't write anything to audit log
# 1: write only certain request to audit log
# 2: write everything to audit log
AUDIT_VERBOSITY = 1

# put exception traceback into response in case of error; possible values:
# 'never': don't put traceback to any response
# 'auth_500': put traceback to 500 error response if user was authenticated
# 'always': put traceback to every error response caused by exception
TRACEBACK_IN_RESPONSE = 'auth_500'

# mail configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'altai-mailbot@example.com'
MAIL_PASSWORD = ''
MAIL_USE_TLS = True

# file to write logs to; None means write to stderr
LOG_FILE_NAME = None

# default log priority
# possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
LOG_LEVEL = 'INFO'

# log format; see python.logging docs for available formats
LOG_FORMAT = '%(asctime)s %(levelname)8s: %(message)s'

# format for date in logs
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# periodic job intervals, in seconds, may be floating point number
RIP_EXPIRED_INSTANCES_TASK_INTERVAL = 10.0
INSTANCES_REMINDER_TASK_INTERVAL = 60.0
INSTANCE_DATA_GC_TASK_INTERVAL = 40 * 60.0

# request sanity check parameters
MAX_ELEMENT_NAME_LENGTH = 64
MAX_PARAMETER_LENGTH = 4096

