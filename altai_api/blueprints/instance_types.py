
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

import uuid

from flask import Blueprint, abort, url_for, g

from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.utils.misc import from_mb, from_gb, to_mb, to_gb
from altai_api.utils import *

from altai_api.utils.decorators import root_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st


instance_types = Blueprint('instance_types', __name__)


def _instance_type_from_nova(flavor):
    return {
        u'id': flavor.id,
        u'href': url_for('instance_types.get_instance_type',
                         instance_type_id=flavor.id),
        u'name': flavor.name,
        u'cpus': flavor.vcpus,
        u'ram': from_mb(flavor.ram),
        u'root-size': from_gb(flavor.disk),
        u'ephemeral-size': from_gb(flavor.ephemeral)
    }


def _instance_type_for_nova(data):
    return  {
        u'name': data['name'],
        u'ram': to_mb(data['ram']),
        u'vcpus': data['cpus'],
        u'disk': to_gb(data['root-size']),
        u'ephemeral': to_gb(data['ephemeral-size'])
    }


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.Int('cpus'),
    st.Int('ram'),
    st.Int('root-size'),
    st.Int('ephemeral-size')),

    required=('name', 'cpus', 'ram', 'root-size', 'ephemeral-size')
)


@instance_types.route('/', methods=('GET',))
@root_endpoint('instance-types')
def list_instance_types():
    parse_collection_request(_SCHEMA)
    all_flavors = g.client_set.compute.flavors.list()
    result = [_instance_type_from_nova(flavor)
              for flavor in all_flavors]
    return make_collection_response(u'instance-types', result)


@instance_types.route('/<instance_type_id>', methods=('GET',))
def get_instance_type(instance_type_id):
    # the following great code returns deleted flavors...
    #try:
    #    flavor = g.client_set.compute.flavors.get(instance_type_id)
    #except osc_exc.NotFound:
    #    abort(404)

    all_flavors = g.client_set.compute.flavors.list()
    for flavor in all_flavors:
        if flavor.id == instance_type_id:
            return make_json_response(_instance_type_from_nova(flavor))
    abort(404)


@instance_types.route('/', methods=('POST',))
def create_instance_type():
    data = parse_request_data(required=_SCHEMA.required)
    args = _instance_type_for_nova(data)
    args['flavorid'] = uuid.uuid4().int
    try:
        flavor = g.client_set.compute.flavors.create(**args)
    except osc_exc.HttpException, e:
        raise exc.InvalidRequest(str(e))
    return make_json_response(_instance_type_from_nova(flavor))


@instance_types.route('/<instance_type_id>', methods=('DELETE',))
def delete_instance_type(instance_type_id):
    try:
        g.client_set.compute.flavors.delete(instance_type_id)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(None, 204)

