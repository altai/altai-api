
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

from flask import url_for, g, Blueprint, abort
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import *
from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.my_ssh_keys import keypair_from_nova
from altai_api.blueprints.users import fetch_user

users_ssh_keys = Blueprint('users_ssh_keys', __name__)


_SCHEMA = Schema((
    st.String('name'),
    st.String('public-key'),
    st.String('fingerprint')),

    required=('name', 'public-key'),
)


@users_ssh_keys.route('/', methods=('GET',))
def list_users_ssh_keys(user_id):
    parse_collection_request(_SCHEMA)
    mgr = g.client_set.compute_ext.user_keypairs

    result = [keypair_from_nova(keypair) for keypair in mgr.list(user_id)]
    if not result:
        # abort(404) when user not exists or not visible:
        fetch_user(user_id, g.is_admin)

    parent_href = url_for('users.get_user', user_id=user_id)
    return make_collection_response('ssh-keys', result,
                                    parent_href=parent_href)


@users_ssh_keys.route('/<key_name>', methods=('GET',))
def get_users_ssh_key(user_id, key_name):
    mgr = g.client_set.compute_ext.user_keypairs
    try:
        keypair = mgr.get(user_id, key_name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(keypair_from_nova(keypair))


@users_ssh_keys.route('/', methods=('POST',))
def create_users_ssh_key(user_id):
    data = parse_request_data(required=_SCHEMA.required)
    mgr = g.client_set.compute_ext.user_keypairs
    # abort(404) when user not exists or not visible:
    user = fetch_user(user_id, g.is_admin)

    kp = mgr.create(user, data['name'], data['public-key'])
    set_audit_resource_id(kp.name)
    return make_json_response(keypair_from_nova(kp))


@users_ssh_keys.route('/<key_name>', methods=('DELETE',))
def delete_users_ssh_key(user_id, key_name):
    mgr = g.client_set.compute_ext.user_keypairs
    try:
        mgr.delete(user_id, key_name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, 204)

