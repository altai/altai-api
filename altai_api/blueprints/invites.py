
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

from altai_api.blueprints.users import (user_from_nova, fetch_user,
                                        update_user_data, InvitesDAO)

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils import make_json_response, parse_request_data
from altai_api.utils.decorators import no_auth_endpoint


invites = Blueprint('invites', __name__)


def _invite_and_user(code):
    invite = InvitesDAO.get(code)
    if invite.complete:
        abort(404)
    user = fetch_user(invite.user_id)
    if user.enabled:
        abort(404)
    return invite, user


@invites.route('/<code>', methods=('GET',))
@no_auth_endpoint
def get_user_by_code(code):
    invite, user = _invite_and_user(code)
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

    invite, user = _invite_and_user(code)
    data['enabled'] = True
    update_user_data(user, data)
    InvitesDAO.complete_for_user(user.id)

    # fetch updated user:
    user = fetch_user(user.id)
    return make_json_response(user_from_nova(user, invite), 200)

