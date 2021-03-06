
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

from flask import url_for, g, Blueprint, abort
from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api import auth
from altai_api.utils import *
from altai_api.utils.decorators import user_endpoint
from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.my_ssh_keys import keypair_to_view
from altai_api.blueprints.users import fetch_user

BP = Blueprint('users_ssh_keys', __name__)


_SCHEMA = Schema((
    st.String('name'),
    st.String('public-key'),
    st.String('fingerprint')),

    required=('name', 'public-key'),
)


@BP.route('/', methods=('GET',))
@user_endpoint
def list_users_ssh_keys(user_id):
    parse_collection_request(_SCHEMA)
    fetch_user(user_id, g.is_admin)  # check that user exists and is visible

    mgr = auth.admin_client_set().compute_ext.user_keypairs
    result = [keypair_to_view(keypair) for keypair in mgr.list(user_id)]

    parent_href = url_for('users.get_user', user_id=user_id)
    return make_collection_response('ssh-keys', result,
                                    parent_href=parent_href)


@BP.route('/<key_name>', methods=('GET',))
@user_endpoint
def get_users_ssh_key(user_id, key_name):
    if not g.is_admin:
        fetch_user(user_id, False)  # check that user is visible
    try:
        mgr = auth.admin_client_set().compute_ext.user_keypairs
        keypair = mgr.get(user_id, key_name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(keypair_to_view(keypair))


@BP.route('/', methods=('POST',))
@user_endpoint
def create_users_ssh_key(user_id):
    data = parse_request_data(required=_SCHEMA.required)

    if user_id != auth.current_user_id():
        auth.assert_admin()
    fetch_user(user_id, g.is_admin)  # check that user exists and is visible

    mgr = auth.admin_client_set().compute_ext.user_keypairs
    try:
        kp = mgr.create(user_id, data['name'], data['public-key'])
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))
    set_audit_resource_id(kp.name)
    return make_json_response(keypair_to_view(kp))


@BP.route('/<key_name>', methods=('DELETE',))
def delete_users_ssh_key(user_id, key_name):
    if user_id != auth.current_user_id():
        auth.assert_admin()

    mgr = auth.admin_client_set().compute_ext.user_keypairs
    try:
        mgr.delete(user_id, key_name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, 204)

