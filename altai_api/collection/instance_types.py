
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

from flask import Blueprint, abort, url_for, request, g

from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response, setup_sorting


instance_types = Blueprint('instance_types', __name__)

_MB = 1024 * 1024
_GB = 1024 * 1024 * 1024

def _div(a, b):
    """Divide a to b with rounding up"""
    return int((a + b - 1) / b)


def _instance_type_from_nova(flavor):
    return {
        u'id' : flavor.id,
        u'href': url_for('instance_types.get_instance_type',
                         instance_type_id=flavor.id),
        u'name': flavor.name,
        u'cpus': flavor.vcpus,
        u'ram': flavor.ram * _MB,
        u'root-size': flavor.disk * _GB,
        u'ephemeral-size': flavor.ephemeral * _GB
    }

def _instance_type_for_nova(data):
    if u'id' in data:
        raise exc.UnknownElement(u'id')
    return  {
        u'name': data['name'],
        u'ram': _div(data['ram'], _MB),
        u'vcpus': data['cpus'],
        u'disk': _div(data['root-size'], _GB),
        u'ephemeral': _div(data['ephemeral-size'], _GB)
    }


@instance_types.route('/', methods=('GET',))
def list_instance_types():
    setup_sorting(('id', 'name', 'cpus', 'ram',
                   'root-size', 'ephemeral-size'))

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
    args = _instance_type_for_nova(request.json)
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

