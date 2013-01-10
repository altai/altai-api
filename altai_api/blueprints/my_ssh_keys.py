
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

from flask import url_for, g, Blueprint, abort, request

from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response
from altai_api.utils import parse_collection_request

from altai_api.schema import Schema
from altai_api.schema import types as st

from openstackclient_base import exceptions as osc_exc

my_ssh_keys = Blueprint('my_ssh_keys', __name__)


def _keypair_from_nova(keypair):
    return {
        'href': url_for('my_ssh_keys.get_my_ssh_key',
                        key_name=keypair.name),
        'name': keypair.name,
        'public-key': keypair.public_key,
        'fingerprint': keypair.fingerprint
    }


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('public-key'),
    st.String('fingerprint')
))


@my_ssh_keys.route('/', methods=('GET',))
def list_my_ssh_keys():
    parse_collection_request(_SCHEMA)

    result = [_keypair_from_nova(keypair)
              for keypair in g.client_set.compute.keypairs.list()]

    return make_collection_response('ssh-keys', result,
                                    parent_href=url_for('get_current_user'))


@my_ssh_keys.route('/<key_name>', methods=('GET',))
def get_my_ssh_key(key_name):
    try:
        keypair = g.client_set.compute.keypairs.find(name=key_name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(_keypair_from_nova(keypair))


@my_ssh_keys.route('/', methods=('POST',))
def create_my_ssh_key():
    data = request.json
    kp = g.client_set.compute.keypairs.create(data['name'],
                                              data.get('public-key'))
    result = _keypair_from_nova(kp)
    if hasattr(kp, 'private_key'):
        result['private-key'] = kp.private_key
    return make_json_response(result)


@my_ssh_keys.route('/<key_name>', methods=('DELETE',))
def delete_my_ssh_key(key_name):
    try:
        g.client_set.compute.keypairs.delete(key_name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, 204)

