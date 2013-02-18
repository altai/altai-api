
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

from flask import url_for, Blueprint, abort, g

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import *
from altai_api.utils.decorators import user_endpoint
from altai_api.auth import (admin_client_set, assert_admin_or_project_user,
                            assert_admin, current_user_id)

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.auth import default_tenant_id
from altai_api.blueprints.projects import get_tenant
from altai_api.blueprints.users import link_for_user, member_role_id


project_users = Blueprint('project_users', __name__)


_SCHEMA = Schema((
    st.String('id'),
    st.String('name')),

    required=('id',)
)


def _project_users_list(project_id):
    assert_admin_or_project_user(project_id, eperm_status=404)
    if project_id == default_tenant_id():
        abort(404)
    try:
        return admin_client_set().identity_admin.tenants.list_users(project_id)
    except osc_exc.NotFound:
        abort(404)


@project_users.route('/', methods=('GET',))
@user_endpoint
def list_project_users(project_id):
    parse_collection_request(_SCHEMA)
    result = [link_for_user(user) for user in _project_users_list(project_id)]
    parent_href = url_for('projects.get_project', project_id=project_id)
    return make_collection_response(u'users', result, parent_href=parent_href)


@project_users.route('/<user_id>', methods=('GET',))
@user_endpoint
def get_project_user(project_id, user_id):
    for user in _project_users_list(project_id):
        if user.id == user_id:
            return make_json_response(link_for_user(user))
    abort(404)


def _get_user(user_id):
    try:
        return g.client_set.identity_admin.users.get(user_id)
    except osc_exc.NotFound:
        raise exc.InvalidRequest('User with id %s does not exist' % user_id)


@project_users.route('/', methods=('POST',))
def add_project_user(project_id):
    user_id = parse_request_data(required=_SCHEMA.required)['id']
    tenant = get_tenant(project_id)
    user = _get_user(user_id)
    set_audit_resource_id(user_id)

    try:
        tenant.add_user(user.id, member_role_id())
    except osc_exc.NotFound:
        user = _get_user(user_id)  # check that user still exists
        abort(404)  # if user still exists, tenant was removed

    return make_json_response(link_for_user(user))


@project_users.route('/<user_id>', methods=('DELETE',))
@user_endpoint
def remove_project_user(project_id, user_id):
    tenant = get_tenant(project_id)
    if user_id != current_user_id():
        assert_admin()

    try:
        user_mgr = admin_client_set().identity_admin.users
        roles = user_mgr.list_roles(user_id, project_id)
    except osc_exc.NotFound:
        abort(404)
    if not roles:
        abort(404)  # user was not member of the project

    for role in roles:
        try:
            tenant.remove_user(user_id, role.id)
        except osc_exc.NotFound:
            pass  # already deleted by someone else
    return make_json_response(None, status_code=204)

