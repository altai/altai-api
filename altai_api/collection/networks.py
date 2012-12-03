
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
from altai_api.exceptions import UnknownElement, InvalidRequest
from openstackclient_base import exceptions as osc_exc

networks = flask.Blueprint('networks', __name__)


def net_to_dict(net):
    """Convert novaclient.v1_1.Network resource to dict"""
    d = {}
    d["id"] = net.id
    d["href"] = flask.url_for('networks.get_network', net_id=net.id)
    d["name"] = net.label
    d["vlan"] = int(net.vlan)
    d["cidr"] = net.cidr

    if net.project_id:
        d["used"] = True
        # TODO(ipersky): implement this as <link> after Projects blueprint is ready
        d["project"] = net.project_id
    else:
        d["used"] = False

    return d


def _response_template():
    return {
        'collection': {
            'name': 'networks',
            'size': 0
        },
        'networks': []
    }


@networks.route('/', methods=('GET',))
def list_networks():
    client = flask.g.client_set
    nets = client.compute.networks.list()

    response = _response_template()
    response['networks'] = [ net_to_dict(net) for net in nets ]
    response['collection']['size'] = len(nets)

    return make_json_response(response)


@networks.route('/<net_id>', methods=('GET',))
def get_network(net_id):
    client = flask.g.client_set
    try:
        net = client.compute.networks.get(net_id)
    except osc_exc.NotFound:
        flask.abort(404)

    return make_json_response(net_to_dict(net))


@networks.route('/', methods=('POST',))
def create_network():
    client = flask.g.client_set
    # validate input
    param = flask.request.json
    try:
        (name, vlan, cidr) = param["name"], int(param["vlan"]), param["cidr"]
    except:
        raise InvalidRequest("One of <name>, <vlan> or <cidr> params is missing \
                             or ivalid")
    # create network
    try:
        new_net = client.compute.networks.create(label=name, vlan=vlan, cidr=cidr)
    except osc_exc.BadRequest, e:
        raise InvalidRequest(str(e))


    return make_json_response(net_to_dict(new_net))


@networks.route('/<net_id>', methods=('DELETE',))
def delete_network(net_id):
    client = flask.g.client_set
    try:
        client.compute.networks.delete(net_id)
    except osc_exc.NotFound:
        flask.abort(404)
    return make_json_response(None, status_code=204)

