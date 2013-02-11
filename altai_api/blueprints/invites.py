
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

from flask import Blueprint, abort
from openstackclient_base import exceptions as osc_exc

from altai_api.blueprints.users import (user_from_nova, InvitesDAO)

from altai_api.auth import admin_client_set
from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils import make_json_response, parse_request_data
from altai_api.utils.decorators import no_auth_endpoint


invites = Blueprint('invites', __name__)


def _invite_and_user(code, user_mgr):
    invite = InvitesDAO.get(code)
    try:
        assert not invite.complete
        user = user_mgr.get(invite.user_id)
        assert not user.enabled
    except (osc_exc.NotFound, AssertionError):
        abort(404)
    return invite, user


@invites.route('/<code>', methods=('GET',))
@no_auth_endpoint
def get_user_by_code(code):
    user_mgr = admin_client_set().identity_admin.users
    invite, user = _invite_and_user(code, user_mgr)
    return make_json_response(user_from_nova(user, invite))


_ACCEPT_SCHEMA = Schema((
    st.String('name'),
    st.String('fullname'),
    st.String('email'),
))

_ACCEPT_REQUIRES = Schema((
    st.String('password'),
))


@invites.route('/<code>', methods=('PUT',))
@no_auth_endpoint
def accept_invite(code):
    data = parse_request_data(_ACCEPT_SCHEMA, _ACCEPT_REQUIRES)
    user_mgr = admin_client_set().identity_admin.users
    invite, user = _invite_and_user(code, user_mgr)

    try:
        user_mgr.update(user.id, enabled=True)
        user_mgr.update_password(user.id, data['password'])
        user = user_mgr.get(user.id)
    except osc_exc.NotFound:
        abort(404)

    InvitesDAO.complete_for_user(user.id)
    return make_json_response(user_from_nova(user, invite), 200)

