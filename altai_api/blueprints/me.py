
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

from flask import Blueprint, g, abort

from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.auth import current_user_id
from altai_api.utils import make_json_response, parse_request_data
from altai_api.utils.decorators import (no_auth_endpoint, user_endpoint,
                                        root_endpoint)

from altai_api.utils.mail import send_reset_password
from altai_api.blueprints.users import get_user, fetch_user, update_user_data
from altai_api.db.tokens import TokensDAO


BP = Blueprint('me', __name__)
ResetTokensDAO = TokensDAO('password-reset')


@BP.route('')
@user_endpoint
@root_endpoint('me')
def get_current_user():
    """Current user resource shortcut"""
    return get_user(current_user_id())


def _find_user(data):
    if 1 != sum((1 if 'id' in data else 0,
                 1 if 'name' in data else 0,
                 1 if 'email' in data else 0)):
        raise exc.InvalidRequest('Exactly one element of id, name or email'
                                 ' must be present')
    user_mgr = g.client_set.identity_admin.users
    try:
        if 'id' in data:
            return user_mgr.get(data['id'])
        elif 'email' in data:
            return user_mgr.find(email=data['email'])
        elif 'name' in data:
            return user_mgr.find(name=data['name'])
    except osc_exc.NotFound:
        return None


_RESET_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('email'),
    st.String('link-template')
))


@BP.route('/reset-password', methods=('POST',))
@no_auth_endpoint
@root_endpoint('reset-password')
def reset_password():
    if not g.config('password-reset', 'enabled'):
        abort(404)
    data = parse_request_data(allowed=_RESET_SCHEMA)
    user = _find_user(data)
    if user is None:
        return make_json_response(None, status_code=204)
    token = ResetTokensDAO.create(user.id, user.email)
    send_reset_password(user.email, token.code, user.name,
                        link_template=data.get('link-template'),
                        greeting=getattr(user, 'fullname', ''))
    return make_json_response(None, status_code=204)


_APPLY_SCHEMA = Schema((
    st.String('password'),
))


@BP.route('/reset-password/<code>', methods=('POST',))
@no_auth_endpoint
def apply_password_reset(code):
    if not g.config('password-reset', 'enabled'):
        abort(404)
    data = parse_request_data(required=_APPLY_SCHEMA)
    token = ResetTokensDAO.get(code)
    if not token or token.complete:
        abort(404)
    user = fetch_user(token.user_id, admin_mode=True)
    update_user_data(user, data)
    ResetTokensDAO.complete_for_user(token.user_id)
    return make_json_response(None, status_code=204)

