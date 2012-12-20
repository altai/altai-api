
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

from flask import request, g, abort
from flask import current_app as app
from openstackclient_base.client_set import ClientSet


def require_auth():
    """Handle request authentication
    """
    if not keystone_auth(request.authorization):
        abort(401)
    return None


def keystone_auth(auth):
    """Authorize in keystone and save authorized client set to flask.g."""
    if auth is None:
        return False
    cs = ClientSet(username=auth.username,
                   password=auth.password,
                   tenant_name=app.config['DEFAULT_TENANT'],
                   auth_uri=app.config['KEYSTONE_URI'])
    try:
        cs.http_client.authenticate() # raises exception on failure
    except IOError, error:
        raise RuntimeError(
            'Failed to connect to authentication service (%s)' % error)
    g.client_set = cs
    return True


def is_authenticated():
    """Returns True if client was authenticated."""
    return hasattr(g, 'client_set')


def client_set_for_tenant(tenant_id=None, tenant_name=None):
    """Returns client set scoped to given tenant"""
    if tenant_name is None and tenant_id is None:
        raise ValueError('Either tenant_name or tenant_id mist be specified')
    return ClientSet(token=g.client_set.http_client.access['token']['id'],
                     tenant_name=tenant_name,
                     tenant_id=tenant_id,
                     auth_uri=app.config['KEYSTONE_URI'])

def default_tenant_id():
    """Returns ID of tenant named app.config['DEFAULT_TENANT']

    Works only for authorized users

    """
    return g.client_set.http_client.access['token']['tenant']['id']

def admin_role_id():
    """Get ID of 'admin' role -- role of administrator of default tenant.

    If client is not Altai administrator, she doesn't have this role and don't
    need it's ID, so this function raises 403 HTTP error in this case.

    """
    access = g.client_set.http_client.access
    admin_role_ids = [role['id']
                      for role in access['user']['roles']
                      if role['name'] == 'admin']
    try:
        return admin_role_ids[0]
    except IndexError:
        abort(403)

