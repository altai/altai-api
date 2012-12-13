
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

from flask import Blueprint, g, url_for, abort, request
from openstackclient_base import exceptions as osc_exc

from altai_api.main import app
from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response, setup_sorting
from altai_api.exceptions import InvalidRequest
from altai_api.authentication import default_tenant_id, admin_role_id

from altai_api.collection.projects import link_for_project


users = Blueprint('users', __name__)

def link_for_user(user):
    return {
        u'id': user.id,
        u'name': user.name,
        u'href': url_for('users.get_user', user_id=user.id)
    }


def fetch_user(user_id):
    try:
        return g.client_set.identity_admin.users.get(user_id)
    except osc_exc.NotFound:
        abort(404)



def _user_from_nova(user):
    systenant = app.config['DEFAULT_TENANT']
    roles = user.list_roles()

    projects = [link_for_project(r.tenant['id'], r.tenant['name'])
                for r in roles
                if r.tenant['name'] != systenant]

    is_admin = any((r.role["name"].lower() == 'admin'
                    for r in roles
                    if r.tenant['name'] == systenant))
    return {
        u'id': user.id,
        u'href': url_for('users.get_user', user_id=user.id),
        u'name': user.name,
        u'email': user.email,
        u'fullname': getattr(user, 'fullname', ''),
        u'admin': is_admin,
        u'projects': projects,
        u'completed-registration': user.enabled,
    }


def _grant_admin(user_id):
    """Grant admin permission.

    Add admin role with in admin tenant (aka systenant).

    """
    g.client_set.identity_admin.roles.add_user_role(
        user_id, admin_role_id(), default_tenant_id())


def _revoke_admin(user_id):
    """Revoke admin permission.

    Remove admin role in admin tenant (aka systenant).

    """
    try:
        g.client_set.identity_admin.roles.remove_user_role(
            user_id, admin_role_id(), default_tenant_id())
    except osc_exc.NotFound:
        pass # user was not admin


@users.route('/', methods=('GET',))
def list_users():
    setup_sorting(('id', 'name', 'fullname', 'email',
                   'admin', 'completed-registration'))
    user_mgr = g.client_set.identity_admin.users
    return make_collection_response(u'users', [_user_from_nova(user)
                                               for user in user_mgr.list()])


@users.route('/<user_id>', methods=('GET',))
def get_user(user_id):
    user = fetch_user(user_id)
    return make_json_response(_user_from_nova(user))


@users.route('/', methods=('POST',))
def create_user():
    param = request.json
    try:
        email = param["email"]
        password = param["password"]
        name = param.get("name", email)
        fullname = param.get("fullname", '')
        admin = bool(param.get("admin", False))
    except:
        raise InvalidRequest("One of params is missing or invalid")
    # create user
    try:
        user_mgr = g.client_set.identity_admin.users
        new_user = user_mgr.create(
            name=name, password=password, email=email)
        if fullname:
            user_mgr.update(new_user, fullname=fullname)
        if admin:
            _grant_admin(new_user.id)
    except osc_exc.BadRequest, e:
        raise InvalidRequest(str(e))

    return make_json_response(_user_from_nova(new_user))


@users.route('/<user_id>', methods=('PUT',))
def update_user(user_id):
    user = fetch_user(user_id)
    param = request.json
    user_mgr = g.client_set.identity_admin.users


    fields_to_update = {}
    # update name, email, fullname
    for key in ('name', 'email', 'fullname'):
        if key in param:
            fields_to_update[key] = param[key]
    if fields_to_update:
        user_mgr.update(user, **fields_to_update)
    # update password
    if 'password' in param:
        user_mgr.update_password(user, param['password'])
    # update admin flag
    admin = param.get('admin')
    if admin == True:
        _grant_admin(user_id)
    elif admin == False:
        _revoke_admin(user_id)

    # get updated user
    user = user_mgr.get(user_id)
    return make_json_response(_user_from_nova(user))


@users.route('/<user_id>', methods=('DELETE',))
def delete_user(user_id):
    try:
        g.client_set.identity_admin.users.delete(user_id)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, status_code=204)


