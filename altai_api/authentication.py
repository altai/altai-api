
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

from altai_api.main import app
from flask import request, url_for, g
from openstackclient_base.client import HttpClient
from altai_api.default_settings import AUTHORIZATION_MODE


@app.before_request
def require_auth():
    """Handle request authentication
    """
    if not authorize(request.authorization):
        response = app.make_response((
            'You have to login with proper credentials', 401))

        entry_point = url_for('get_versions', _external=True)
        response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % (
            entry_point.split('//', 1)[1].strip('/')
        )
        return response
    return None

def authorize(auth):
    """Authorize and save authorized http client to flask.g.
    """
    auth_mode = app.config['AUTHORIZATION_MODE']
    if auth_mode == 'keystone':
        if auth is None:
            return False
        return keystone_authorize(auth.username,
                                  auth.password)
    elif auth_mode == 'noneatall':
        g.http_client = None
        return True
    else:
        raise RuntimeError('Invalud AUTHORIZATION_MODE value')


def keystone_authorize(username, password):
    """Authorize in keystone and save authorized http client to flask.g.
    """
    client = HttpClient(username=username,
                        password=password,
                        auth_uri=app.config['KEYSTONE_URI'])
    client.authenticate()
    g.http_client = client
    return True

