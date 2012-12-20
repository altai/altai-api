
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

import flask

from altai_api.utils import make_json_response
from altai_api.utils import parse_collection_request
from altai_api.utils import make_collection_response

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.collection.projects import link_for_project

networks = flask.Blueprint('networks', __name__)


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
    st.String('name'),
    st.String('id'),
    st.Int('vlan'),
    st.Cidr('cidr'),
    st.Boolean('used'),
    st.LinkObject('project')
))


@networks.route('/', methods=('GET',))
def list_networks():
    parse_collection_request(_SCHEMA)
    nets = flask.g.client_set.compute.networks.list()
    return make_collection_response(u'networks',
                                    [_net_to_dict(net) for net in nets])


@networks.route('/<net_id>', methods=('GET',))
def get_network(net_id):
    client = flask.g.client_set
    try:
        net = client.compute.networks.get(net_id)
    except osc_exc.NotFound:
        flask.abort(404)

    return make_json_response(_net_to_dict(net))


@networks.route('/', methods=('POST',))
def create_network():
    client = flask.g.client_set
    # TOOD(imelnikov) validate input
    param = flask.request.json
    (name, vlan, cidr) = param["name"], int(param["vlan"]), param["cidr"]

    # create network
    try:
        new_net = client.compute.networks.create(label=name,
                                                 vlan_start=vlan,
                                                 cidr=cidr)
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))

    if isinstance(new_net, list) and len(new_net) == 1:
        new_net = new_net[0]
    else:
        raise ValueError('Network created with strange result: %r' % new_net)

    return make_json_response(_net_to_dict(new_net))


@networks.route('/<net_id>', methods=('DELETE',))
def delete_network(net_id):
    client = flask.g.client_set
    try:
        client.compute.networks.delete(net_id)
    except osc_exc.NotFound:
        flask.abort(404)
    return make_json_response(None, status_code=204)

