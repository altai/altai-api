
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

import flask

from altai_api.auth import admin_client_set
from altai_api.utils import *
from altai_api.utils.decorators import root_endpoint, user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.blueprints.projects import link_for_project

BP = flask.Blueprint('networks', __name__)


def _net_to_dict(net):
    """Convert novaclient.v1_1.Network resource to dict"""
    d = {}
    d["id"] = net.id
    d["href"] = flask.url_for('networks.get_network', net_id=net.id)
    d["name"] = net.label
    d["vlan"] = int(net.vlan)
    d["cidr"] = net.cidr

    if net.project_id:
        d["used"] = True
        d["project"] = link_for_project(net.project_id)
    else:
        d["used"] = False

    return d


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.Int('vlan'),
    st.Cidr('cidr'),
    st.Boolean('used'),
    st.LinkObject('project')),

    required=('name', 'vlan', 'cidr')
)


@BP.route('/', methods=('GET',))
@root_endpoint('networks')
@user_endpoint
def list_networks():
    parse_collection_request(_SCHEMA)
    nets = admin_client_set().compute.networks.list()
    return make_collection_response(u'networks',
                                    [_net_to_dict(net) for net in nets])


@BP.route('/<net_id>', methods=('GET',))
@user_endpoint
def get_network(net_id):
    try:
        net = admin_client_set().compute.networks.get(net_id)
    except osc_exc.NotFound:
        flask.abort(404)

    return make_json_response(_net_to_dict(net))


@BP.route('/', methods=('POST',))
def create_network():
    param = parse_request_data(_SCHEMA.required)
    client = flask.g.client_set

    # create network
    try:
        new_net = client.compute.networks.create(label=param['name'],
                                                 vlan_start=param['vlan'],
                                                 cidr=param['cidr'])
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))

    if isinstance(new_net, list) and len(new_net) == 1:
        new_net = new_net[0]
    else:
        raise ValueError('Network created with strange result: %r' % new_net)

    set_audit_resource_id(new_net)
    return make_json_response(_net_to_dict(new_net))


@BP.route('/<net_id>', methods=('DELETE',))
def delete_network(net_id):
    set_audit_resource_id(net_id)
    client = flask.g.client_set
    try:
        client.compute.networks.delete(net_id)
    except osc_exc.NotFound:
        flask.abort(404)
    return make_json_response(None, status_code=204)

