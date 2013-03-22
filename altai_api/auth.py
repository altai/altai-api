
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

from flask import request, g, abort
from flask import current_app as app

from openstackclient_base.client_set import ClientSet
from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc


ATTRIBUTE_NAME = 'altai_api_endpoint_auth_type'


def require_auth():
    """Handle request authentication"""
    if request.url_rule is None:
        return user_auth()  # need user auth for 404

    check_auth = getattr(app.view_functions[request.url_rule.endpoint],
                         ATTRIBUTE_NAME, admin_auth)
    return check_auth()


def _keystone_auth(require_admin):
    auth = request.authorization
    if auth is None:
        abort(401)

    try:
        cs = _client_set(auth.username, auth.password,
                         tenant_name=app.config['SYSTENANT'])
    except (osc_exc.Unauthorized, osc_exc.Forbidden):
        if require_admin:
            abort(403)
        try:
            # as a user, try again without tenant
            cs = _client_set(auth.username, auth.password)
        except (osc_exc.Unauthorized, osc_exc.Forbidden):
            abort(403)

    if admin_role_id(cs) is None:
        if require_admin:
            abort(403)
        g.is_admin = False
    else:
        g.admin_client_set = cs
        g.is_admin = True

    g.client_set = cs
    g.audit_data['user_id'] = current_user_id()
    return None


def admin_auth():
    """Authorize for administrative endpoint"""
    return _keystone_auth(require_admin=True)


def user_auth():
    """Authorize for users endpoint"""
    return _keystone_auth(require_admin=False)


def no_auth():
    """Authorize for noauth endpoint"""
    g.client_set = None
    g.is_admin = False
    return None


def _client_set(username=None, password=None, token=None,
                tenant_name=None, tenant_id=None):
    """Authorize in keystone and return client set"""
    cs = ClientSet(username=username,
                   password=password,
                   token=token,
                   tenant_name=tenant_name,
                   tenant_id=tenant_id,
                   auth_uri=app.config['KEYSTONE_URI'])
    try:
        cs.http_client.authenticate()
    except IOError, error:
        raise RuntimeError(
            'Failed to connect to authentication service (%s)' % error)
    return cs


def is_authenticated():
    """Returns True if client was authenticated."""
    return getattr(g, 'client_set', None) is not None


def client_set_for_tenant(tenant_id, eperm_status=403, fallback_to_api=False):
    """Returns client set scoped to given tenant"""
    try:
        cs = _client_set(token=g.client_set.http_client.access['token']['id'],
                         tenant_id=tenant_id)
    except (osc_exc.Unauthorized, osc_exc.Forbidden):
        if g.is_admin:
            if fallback_to_api:
                return api_client_set(tenant_id)
            else:
                raise exc.AltaiApiException(
                        'You are not member of project %r' % tenant_id,
                        status_code=eperm_status,
                        exc_type='AdministratorIsNotMemberOfTenant')
        abort(eperm_status)
    return cs


def default_tenant_id():
    """Returns ID of tenant named app.config['SYSTENANT']
    """
    return admin_client_set().http_client.access['token']['tenant']['id']


def admin_role_id(client_set=None):
    """Get ID of 'admin' role -- role of administrator of default tenant.

    If client is not Altai administrator, she does not need it, so
    we can safely return None in this case.

    """
    if client_set is None:
        # TODO(imelnikov): should we use admin_client_set()?
        client_set = g.client_set
    for role in client_set.http_client.access['user']['roles']:
        if role['name'].lower() == 'admin':
            return role['id']
    return None


def assert_admin():
    """Abort with 403 if current user is not Altai administrator"""
    if not g.is_admin:
        abort(403)


def assert_admin_or_project_user(project_id, eperm_status=403):
    """Abort with given value if current user has no access to project

    User has access to project if he is member of the project or Altai
    administrator.

    """
    if not g.is_admin:
        if project_id not in current_user_project_ids():
            abort(eperm_status)


def current_user_id():
    """Return ID of current user"""
    if not is_authenticated():
        # NOTE(imelnikov): calling this function inside no_auth_endpoint
        # is an application programmer's error
        raise RuntimeError('No current user for this request')
    try:
        return g.client_set.http_client.access['user']['id']
    except KeyError:
        abort(403)


def add_api_superuser_to_project(project_id):
    """Gives API superuser administrative permissions for given projects

    API superuser should be granted all possible permissions.
    """
    try:
        cs = api_client_set()
        user_id = cs.http_client.access['user']['id']
        cs.identity_admin.roles.add_user_role(
            user_id, admin_role_id(cs), project_id)
    except Exception, e:
        app.logger.exception("Failed to add API superuser to "
                             "project %r (%s)", project_id, e)


def _api_client_set_impl(project_id=None):
    user = app.config['ALTAI_API_SUPERUSER']
    password = app.config['ALTAI_API_SUPERUSER_PASSWORD']
    try:
        if project_id is None:
            cs = _client_set(user, password,
                             tenant_name=app.config['SYSTENANT'])
        else:
            cs = _client_set(user, password, tenant_id=project_id)
        if admin_role_id(cs) is not None:
            return cs
    except (osc_exc.Unauthorized, osc_exc.Forbidden):
        pass
    return None


def api_client_set(project_id=None):
    """Return client set with API superuser credentials

    Useful when user is administrator, but not member of
    project project_id.

    """
    cs = _api_client_set_impl(project_id)
    if not cs and project_id is not None:
        add_api_superuser_to_project(project_id)
        cs = _api_client_set_impl(project_id)
    if cs:
        return cs
    else:
        raise RuntimeError('Service misconfiguration: '
                           'invalid API superuser credentials')


def admin_client_set():
    """Get client set with administrative credentials.

    If current user is Altai administrator, his client set bound to
    systenant is returned. If not, api_client_set is returned.

    """
    try:
        return g.admin_client_set
    except AttributeError:
        g.admin_client_set = api_client_set()
        return g.admin_client_set


def bound_client_set():
    """Get client set bound to any tenant user is member of

    Sometimes we don't care what tenant client is bound to, we just want
    to speak to compute, but unbound client set we use by default for users
    are very restricted.

    """
    roles = g.client_set.http_client.access['user'].get('roles')
    if roles:
        return g.client_set
    tenants = g.client_set.identity_public.tenants.list()
    if not tenants:
        abort(403)
    return client_set_for_tenant(tenants[0].id)


def current_user_project_ids():
    """Get set of project ids current user is member of"""
    try:
        return g.current_user_project_ids
    except AttributeError:
        tenants = (g.client_set.identity_public.tenants.list()
                   if is_authenticated() else [])
        g.current_user_project_ids = set((tenant.id for tenant in tenants))
        return g.current_user_project_ids
