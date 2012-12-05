
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
from altai_api.utils import make_json_response
from altai_api.exceptions import InvalidRequest
from altai_api.main import app

users = Blueprint('users', __name__)

def is_admin(user):
    return any(x.role["name"].lower() == 'admin'
               and x.tenant["name"] == app.config['DEFAULT_TENANT']
               for x in user.list_roles())

def _projects_for_user(user):
    # TODO(ipersky): implement
    return []

def user_to_dict(user):
    return {
        u'id': user.id,
        u'href': url_for('users.get_user', user_id=user.id),
        u'name': user.name,
        u'email': user.email,
        u'fullname': user.fullname if hasattr(user, 'fullname') else '',
        u'admin': is_admin(user),
        # TODO(ipersky): implement
        u'projects': _projects_for_user(user),
        u'completed-registration': user.enabled,
    }

@users.route('/', methods=('GET',))
def list_users():
    users = g.client_set.identity_admin.users.list()
    return make_json_response({
        'collection': {
            'name': 'users',
            'size': len(users)
        },
        'users': [user_to_dict(user) for user in users]
    })

@users.route('/<user_id>', methods=('GET',))
def get_user(user_id):
    try:
        user = g.client_set.identity_admin.users.get(user_id)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(user_to_dict(user))

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
        new_user = g.client_set.identity_admin.users.create(
            name=name, password=password, email=email)
        if fullname:
            g.client_set.identity_admin.users.update(new_user, fullname=fullname)
        # TODO(ipersky): add admin role to systenant if 'admin' is set
    except osc_exc.BadRequest, e:
        raise InvalidRequest(str(e))

    return make_json_response(user_to_dict(new_user))

@users.route('/<user_id>', methods=('PUT',))
def update_user(user_id):
    try:
        user = g.client_set.identity_admin.users.get(user_id)
    except osc_exc.NotFound:
        abort(404)

    param = request.json
    fields_to_update = {}
    # update name, email, fullname
    for key in ('name', 'email', 'fullname'):
        if key in param:
            fields_to_update[key] = param[key]
    if len(fields_to_update):
        g.client_set.identity_admin.users.update(user, **fields_to_update)
    # update password
    if 'password' in param:
        g.client_set.identity_admin.users.update_password(user,
                                                          param['password'])
    # update admin flag
    # TODO(ipersky): correctly set 'admin' param

    # get updated user
    user = g.client_set.identity_admin.users.get(user_id)
    return make_json_response(user_to_dict(user))

@users.route('/<user_id>', methods=('DELETE',))
def delete_user(user_id):
    try:
        g.client_set.identity_admin.users.delete(user_id)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, status_code=204)

