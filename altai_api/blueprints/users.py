
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

from flask import Blueprint, g, url_for, abort
from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.main import app

from altai_api import auth
from altai_api.utils import *
from altai_api.utils.decorators import root_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.projects import link_for_project

from altai_api.db.tokens import TokensDAO
from altai_api.utils.mail import send_invitation


users = Blueprint('users', __name__)

# NOTE(imelnikov): we put it here instead of invites.py in hope
# to avoid circular dependencies
InvitesDAO = TokensDAO('invite')


def link_for_user(user):
    return {
        u'id': user.id,
        u'name': user.name,
        u'href': url_for('users.get_user', user_id=user.id)
    }


def fetch_user(user_id):
    """Get user from keystone or abort with 404 if user is not found"""
    try:
        return g.client_set.identity_admin.users.get(user_id)
    except osc_exc.NotFound:
        abort(404)


def member_role_id():
    """Get ID of member role that is used to add member to project"""
    for role in g.client_set.identity_admin.roles.list():
        if role.name.lower() == 'member':
            return role.id
    raise RuntimeError('Server misconfiguration: role not found')


def user_from_nova(user, invite=None, send_code=False):
    systenant = app.config['DEFAULT_TENANT']
    roles = user.list_roles()

    projects = [link_for_project(r.tenant['id'], r.tenant['name'])
                for r in roles
                if r.tenant['name'] != systenant]

    is_admin = any((r.role["name"].lower() == 'admin'
                    for r in roles
                    if r.tenant['name'] == systenant))
    result = {
        u'id': user.id,
        u'href': url_for('users.get_user', user_id=user.id),
        u'name': user.name,
        u'email': user.email,
        u'fullname': getattr(user, 'fullname', ''),
        u'admin': is_admin,
        u'projects': projects,
        u'completed-registration': user.enabled,
    }

    if not user.enabled and invite is None:
        invite = InvitesDAO.get_for_user(user.id)

    if invite is not None and not invite.complete:
        result['invited-at'] = invite.created_at
        if send_code:
            result['invitation-code'] = invite.code
    return result


def _grant_admin(user_id):
    """Grant admin permission.

    Add admin role with in admin tenant (aka systenant).

    """
    g.client_set.identity_admin.roles.add_user_role(
        user_id, auth.admin_role_id(), auth.default_tenant_id())


def _revoke_admin(user_id):
    """Revoke admin permission.

    Remove admin role in admin tenant (aka systenant).

    """
    try:
        g.client_set.identity_admin.roles.remove_user_role(
            user_id, auth.admin_role_id(), auth.default_tenant_id())
    except osc_exc.NotFound:
        pass  # user was not admin


def _add_user_to_projects(user, projects):
    auth.assert_admin()
    role_id = member_role_id()
    for project in projects:
        try:
            g.client_set.identity_admin.roles.add_user_role(
                user=user, role=role_id, tenant=project)
        except osc_exc.NotFound:
            raise exc.IllegalValue('projects', 'link object', project)


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('fullname'),
    st.String('email'),
    st.Boolean('admin'),
    st.Boolean('completed-registration'),
    st.Timestamp('invited-at'),
    st.List(st.LinkObject('projects')),
    st.Boolean('invite'),
    st.String('password'),
    st.Boolean('send-invite-mail'),
    st.String('link-template')),

    create_required=('email',),
    create_allowed=('name', 'fullname', 'admin', 'projects',
                    'invite', 'link-template', 'send-invite-mail',
                    'password'),
    updatable=('name', 'email', 'fullname', 'admin', 'password'),
    list_args=('id', 'name', 'fullname', 'email', 'projects',
               'admin', 'completed-registration', 'invited-at')
)


@users.route('/', methods=('GET',))
@root_endpoint('users')
def list_users():
    parse_collection_request(_SCHEMA.list_args)
    user_mgr = g.client_set.identity_admin.users
    return make_collection_response(u'users', [user_from_nova(user)
                                               for user in user_mgr.list()])


@users.route('/<user_id>', methods=('GET',))
def get_user(user_id):
    user = fetch_user(user_id)
    return make_json_response(user_from_nova(user))


@users.route('/', methods=('POST',))
def create_user():
    data = parse_request_data(_SCHEMA.create_allowed, _SCHEMA.create_required)

    name = data.get('name')
    if name is None:
        name = data.get('email').split('@', 1)[0]

    invite = data.get('invite')
    if not invite:
        if 'password' not in data:
            raise exc.MissingElement('password')
        if 'send-invite-mail' in data:
            raise exc.UnknownElement('send-invite-mail')
        if 'link-template' in data:
            raise exc.UnknownElement('link-template')

    try:
        user_mgr = g.client_set.identity_admin.users

        # NOTE(imelnikov): we disable user until she accepts invite
        new_user = user_mgr.create(name=name,
                                   password=data.get('password'),
                                   email=data['email'],
                                   enabled=not invite)
        set_audit_resource_id(new_user)
        if 'fullname' in data:
            user_mgr.update(new_user, fullname=data['fullname'])
        if data.get('admin'):
            _grant_admin(new_user.id)
        if 'projects' in data:
            _add_user_to_projects(new_user, data['projects'])
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))

    if invite:
        inv = InvitesDAO.create(new_user.id, new_user.email)
        send_mail = data.get('send-invite-mail', True)
        if send_mail:
            send_invitation(new_user.email, inv.code,
                            data.get('link-template'),
                            greeting=data.get('fullname'))
        result = user_from_nova(new_user, inv, send_code=not send_mail)
    else:
        result = user_from_nova(new_user)
    return make_json_response(result)


def update_user_data(user, data):
    user_mgr = g.client_set.identity_admin.users

    fields_to_update = {}
    for key in ('name', 'email', 'fullname', 'enabled'):
        if key in data:
            fields_to_update[key] = data[key]

    try:
        if fields_to_update:
            user_mgr.update(user, **fields_to_update)
        if 'password' in data:
            user_mgr.update_password(user, data['password'])
    except osc_exc.NotFound:
        abort(404)


@users.route('/<user_id>', methods=('PUT',))
def update_user(user_id):
    user = fetch_user(user_id)
    param = parse_request_data(_SCHEMA.updatable)
    set_audit_resource_id(user_id)

    update_user_data(user, param)

    admin = param.get('admin')
    if admin == True:
        _grant_admin(user_id)
    elif admin == False:
        _revoke_admin(user_id)

    # get updated user
    user = fetch_user(user_id)
    return make_json_response(user_from_nova(user))


@users.route('/<user_id>', methods=('DELETE',))
def delete_user(user_id):
    set_audit_resource_id(user_id)
    try:
        g.client_set.identity_admin.users.delete(user_id)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, status_code=204)


_SEND_INVITE_SCHEMA = Schema((
    st.String('link-template'),
    st.Boolean('send-invite-mail'),
    st.Boolean('disable-user')
))


@users.route('/<user_id>/send-invite', methods=('POST',))
def send_invite_for_user(user_id):
    data = parse_request_data(_SEND_INVITE_SCHEMA)
    user = fetch_user(user_id)

    send_mail = data.get('send-invite-mail', True)
    disable_user = data.get('disable-user', False)
    if not send_mail or disable_user:
        auth.assert_admin()

    inv = InvitesDAO.create(user.id, user.email)
    if disable_user:
        update_user_data(user, {'enabled': False, 'password': None})
    if send_mail:
        send_invitation(user.email, inv.code,
                        data.get('link-template'),
                        greeting=getattr(user, 'fullname', ''))
    return make_json_response(user_from_nova(user, inv,
                                             send_code=not send_mail))

