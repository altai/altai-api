
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

from flask import Blueprint, abort
from openstackclient_base import exceptions as osc_exc

from altai_api.blueprints.users import (user_from_nova, InvitesDAO,
                                        update_user_data)

from altai_api import auth
from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils import make_json_response, parse_request_data
from altai_api.utils.decorators import no_auth_endpoint, root_endpoint


BP = Blueprint('invites', __name__)


def _invite_and_user(code):
    user_mgr = auth.admin_client_set().identity_admin.users
    invite = InvitesDAO.get(code)
    try:
        assert not invite.complete
        user = user_mgr.get(invite.user_id)
        assert not user.enabled
    except (osc_exc.NotFound, AssertionError):
        abort(404)
    return invite, user


@BP.route('/')
@root_endpoint('invites')
def list_invites():
    # just a stub to mark with root_endpoint
    abort(404)


@BP.route('/<code>', methods=('GET',))
@no_auth_endpoint
def get_user_by_code(code):
    invite, user = _invite_and_user(code)
    return make_json_response(user_from_nova(user, invite))


_ACCEPT_SCHEMA = Schema((
    st.String('name'),
    st.String('fullname', allow_empty=True),
    st.String('email'),
))

_ACCEPT_REQUIRES = Schema((
    st.String('password'),
))


@BP.route('/<code>', methods=('PUT',))
@no_auth_endpoint
def accept_invite(code):
    data = parse_request_data(_ACCEPT_SCHEMA, _ACCEPT_REQUIRES)
    invite, user = _invite_and_user(code)

    data['enabled'] = True
    try:
        update_user_data(user, data)
        user = auth.admin_client_set().identity_admin.users.get(user.id)
    except osc_exc.NotFound:
        abort(404)

    InvitesDAO.complete_for_user(user.id)
    return make_json_response(user_from_nova(user, invite), 200)

