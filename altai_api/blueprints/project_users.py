
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

from flask import url_for, g, Blueprint, abort, request

from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response
from altai_api.utils import parse_collection_request

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.projects import get_tenant
from altai_api.blueprints.users import link_for_user, fetch_user


project_users = Blueprint('project_users', __name__)


_SCHEMA = Schema((
    st.String('id'),
    st.String('name')
))


@project_users.route('/', methods=('GET',))
def list_project_users(project_id):
    parse_collection_request(_SCHEMA)
    tenant = get_tenant(project_id)
    result = [link_for_user(user) for user in tenant.list_users()]
    parent_href = url_for('projects.get_project', project_id=project_id)
    return make_collection_response(u'users', result, parent_href=parent_href)


@project_users.route('/<user_id>', methods=('GET',))
def get_project_user(project_id, user_id):
    tenant = get_tenant(project_id)
    for user in tenant.list_users():
        if user.id == user_id:
            return make_json_response(link_for_user(user))
    abort(404)


@project_users.route('/', methods=('POST',))
def add_project_user(project_id):
    user_id = request.json['id']
    tenant = get_tenant(project_id)
    user = fetch_user(user_id)
    roles = g.client_set.identity_admin.roles.list()

    try:
        member_role_id = (role.id
                          for role in roles
                          if role.name.lower() == 'member').next()
    except StopIteration:
        raise RuntimeError('Server misconfiguration: role not found')

    tenant.add_user(user_id, member_role_id)
    return make_json_response(link_for_user(user))


@project_users.route('/<user_id>', methods=('DELETE',))
def remove_project_user(project_id, user_id):
    tenant = get_tenant(project_id)
    user = fetch_user(user_id)

    for role in user.list_roles(tenant):
        tenant.remove_user(user.id, role.id)
    return make_json_response(None, status_code=204)

