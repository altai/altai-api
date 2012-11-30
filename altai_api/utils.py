
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

"""Miscellanious utility functions
"""

import json
import altai_api

from altai_api.main import app
from altai_api.authentication import is_authenticated


# Content type for JSON
_JSON = 'application/json'
_IMPELEMENTATION = 'Altai API service v%s' % altai_api.__version__


def make_json_response(data, status_code=200, location=None):
    """Make json response from response data.
    """
    if data is not None:
        if app.config.get('PRETTY_PRINT_JSON'):
            data = json.dumps(data, indent=4, sort_keys=True)
        else:
            data = json.dumps(data, separators=(',',':'))
    else:
        data = ""
    response = app.make_response((data, status_code))
    response.headers['Content-Type'] = _JSON
    if location is not None:
        response.headers['Location'] = location
    if is_authenticated():
        response.headers['X-GD-Altai-Implementation'] = _IMPELEMENTATION
    return response

