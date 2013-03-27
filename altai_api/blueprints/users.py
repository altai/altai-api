
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

from flask import Blueprint, g, url_for, abort
from flask import current_app as app
from flask.exceptions import HTTPException
from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc


from altai_api import auth
from altai_api.utils import *
from altai_api.utils.decorators import root_endpoint, user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.projects import link_for_project

from altai_api.db.tokens import TokensDAO
from altai_api.utils.mail import send_invitation


BP = Blueprint('users', __name__)

# NOTE(imelnikov): we put it here instead of invites.py in hope
# to avoid circular dependencies
InvitesDAO = TokensDAO('invite')


def link_for_user(user):
    return link_for_user_id(user.id, user.name)


def link_for_user_id(user_id, user_name=None):
    if user_name is None:
        try:
            user_name = fetch_user(user_id, g.is_admin).name
        except HTTPException:
            user_name = None
    return {
        u'id': user_id,
        u'name': user_name,
        u'href': url_for('users.get_user', user_id=user_id)
    }


def _user_is_visible(user, admin_mode):
    if admin_mode or user.id == auth.current_user_id():
        return True
    try:
        user_projects = set((role.tenant.get('id')
                             for role in user.list_roles()))
        user_projects.intersection_update(auth.current_user_project_ids())
        return len(user_projects) > 0
    except osc_exc.HttpException:
        return False


def _role_is_visible(role):
    if role.tenant['name'] == app.config['SYSTENANT']:
        return False
    if not g.my_projects:
        return True
    return role.tenant['id'] in auth.current_user_project_ids()


def fetch_user(user_id, admin_mode):
    """Get user from keystone or abort with 404 if user is not found"""
    try:
        user = auth.admin_client_set().identity_admin.users.get(user_id)
    except osc_exc.NotFound:
        abort(404)
    if not _user_is_visible(user, admin_mode):
        abort(404)
    return user


def member_role_id():
    """Get ID of member role that is used to add member to project"""
    for role in g.client_set.identity_admin.roles.list():
        if role.name.lower() == 'member':
            return role.id
    raise RuntimeError('Server misconfiguration: role not found')


def user_from_nova(user, invite=None, send_code=False):
    roles = user.list_roles()
    projects = [link_for_project(r.tenant['id'], r.tenant['name'])
                for r in roles if _role_is_visible(r)]
    is_admin = any((r.role["name"].lower() == 'admin'
                    for r in roles
                    if r.tenant['name'] == app.config['SYSTENANT']))
    href = lambda endpoint: url_for(endpoint, user_id=user.id)
    result = {
        u'id': user.id,
        u'href': href('users.get_user'),
        u'name': user.name,
        u'email': user.email,
        u'fullname': getattr(user, 'fullname', ''),
        u'admin': is_admin,
        u'projects': projects,
        u'completed-registration': user.enabled,
        u'links': {
            u'ssh-keys': href('users_ssh_keys.list_users_ssh_keys'),
            u'send-invite': href('users.send_invite_for_user')
        }
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
    auth.assert_admin()
    g.client_set.identity_admin.roles.add_user_role(
        user_id, auth.admin_role_id(), auth.default_tenant_id())


def _revoke_admin(user_id):
    """Revoke admin permission.

    Remove admin role in admin tenant (aka systenant).

    """
    auth.assert_admin()
    try:
        g.client_set.identity_admin.roles.remove_user_role(
            user_id, auth.admin_role_id(), auth.default_tenant_id())
    except osc_exc.NotFound:
        pass  # user was not admin


def _add_user_to_projects(user, projects):
    if not projects:
        return
    auth.assert_admin()
    role_id = member_role_id()
    for project in projects:
        try:
            g.client_set.identity_admin.roles.add_user_role(
                user=user, role=role_id, tenant=project)
        except osc_exc.NotFound:
            raise exc.InvalidElementValue('projects', 'link object', project,
                                          'Project does not exist')


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('fullname', allow_empty=True),
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


@BP.route('/', methods=('GET',))
@root_endpoint('users')
@user_endpoint
def list_users():
    parse_collection_request(_SCHEMA.list_args)
    user_mgr = auth.admin_client_set().identity_admin.users
    return make_collection_response(
        u'users', [user_from_nova(user)
                   for user in user_mgr.list()
                   if _user_is_visible(user, not g.my_projects)])


@BP.route('/<user_id>', methods=('GET',))
@user_endpoint
def get_user(user_id):
    user = fetch_user(user_id, not g.my_projects)
    return make_json_response(user_from_nova(user))


@BP.route('/', methods=('POST',))
def create_user():
    data = parse_request_data(_SCHEMA.create_allowed, _SCHEMA.create_required)

    email_name, email_domain = data['email'].rsplit('@', 1)
    name = data.get('name', email_name)

    invite = data.get('invite')
    if invite:
        if not g.config('invitations', 'enabled'):
            # TODO(imelnikov): consider if this is error 403, not 400
            raise exc.InvalidRequest('Invitations disabled')
        domains_allowed = g.config('invitations', 'domains-allowed')
        if domains_allowed and email_domain not in domains_allowed:
            abort(403)
    else:
        if 'password' not in data:
            raise exc.MissingElement('password')
        for e in ('send-invite-mail', 'link-template'):
            if e in data:
                reason = '%s element is allowed only when inviting user' % e
                raise exc.UnknownElement(e, reason)

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
        _add_user_to_projects(new_user, data.get('projects'))
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))

    if invite:
        result = _invite_user(new_user, data)
    else:
        result = user_from_nova(new_user)
    return make_json_response(result)


def _invite_user(user, data):
    inv = InvitesDAO.create(user.id, user.email)
    send_mail = data.get('send-invite-mail', True)
    if send_mail:
        send_invitation(user.email, inv.code,
                        data.get('link-template'),
                        greeting=getattr(user, 'fullname', ''))
    else:
        auth.assert_admin()
    return user_from_nova(user, inv, send_code=not send_mail)


def update_user_data(user, data):
    fields_to_update = {}
    for key in ('name', 'email', 'fullname', 'enabled'):
        if key in data:
            fields_to_update[key] = data[key]

    user_mgr = auth.admin_client_set().identity_admin.users
    try:
        if fields_to_update:
            user_mgr.update(user, **fields_to_update)
        if 'password' in data:
            user_mgr.update_password(user, data['password'])
    except osc_exc.NotFound:
        abort(404)


@BP.route('/<user_id>', methods=('PUT',))
@user_endpoint
def update_user(user_id):
    param = parse_request_data(_SCHEMA.updatable)
    user = fetch_user(user_id, g.is_admin)

    set_audit_resource_id(user_id)
    if 'admin' in param:
        auth.assert_admin()

    update_user_data(user, param)

    admin = param.get('admin')
    if admin == True:
        _grant_admin(user_id)
    elif admin == False:
        _revoke_admin(user_id)

    # get updated user
    user = fetch_user(user_id, g.is_admin)
    return make_json_response(user_from_nova(user))


@BP.route('/<user_id>', methods=('DELETE',))
def delete_user(user_id):
    set_audit_resource_id(user_id)

    # try to clean up user's SSH keys
    for key in g.client_set.compute_ext.user_keypairs.list(user_id):
        try:
            g.client_set.compute_ext.user_keypairs.delete(user_id, key.id)
        except osc_exc.HttpException:
            app.logger.exception('Failed to remove keypair %s for user %s',
                                 key.id, user_id)

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


@BP.route('/<user_id>/send-invite', methods=('POST',))
def send_invite_for_user(user_id):
    if not g.config('invitations', 'enabled'):
        # TODO(imelnikov): consider if this is error 403, not 400
        raise exc.InvalidRequest('Invitations disabled')

    data = parse_request_data(_SEND_INVITE_SCHEMA)
    user = fetch_user(user_id, g.is_admin)

    if data.get('disable-user', False):
        auth.assert_admin()
        update_user_data(user, {'enabled': False, 'password': None})

    result = _invite_user(user, data)
    return make_json_response(result)

