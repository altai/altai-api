
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2013 Grid Dynamics Consulting Services, Inc
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

BP = Blueprint('nodes', __name__)

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils import make_json_response
from altai_api.utils import parse_collection_request, make_collection_response
from altai_api.utils.decorators import root_endpoint

from altai_api.utils.misc import from_mb


def link_for_node(name):
    return {
        'name': name,
        'href': url_for('nodes.get_node', name=name)
    }


def _node_to_view(name, hosts):
    result = link_for_node(name)
    for h in hosts:
        if h.project == '(total)':
            result['memory'] = from_mb(h.memory_mb)
            result['cpus'] = h.cpu
        elif h.project == '(used_now)':
            result['memory-used'] = from_mb(h.memory_mb)
            result['cpus-used'] = h.cpu
    return result


_SCHEMA = Schema((
    st.String('name'),
    st.Int('memory'),
    st.Int('cpus'),
    st.Int('memory-used'),
    st.Int('cpus-used'),
))


@BP.route('/', methods=('GET',))
@root_endpoint('nodes')
def list_nodes():
    parse_collection_request(_SCHEMA)
    host_mgr = g.client_set.compute.hosts

    names = [h._info['host_name']
             for h in host_mgr.list_all()
             if h._info['service'] == 'compute']

    result = []
    for name in names:
        try:
            result.append(_node_to_view(name, host_mgr.get(name)))
        except osc_exc.NotFound:
            pass
    return make_collection_response('nodes', result)


@BP.route('/<name>', methods=('GET',))
def get_node(name):
    try:
        hosts = g.client_set.compute.hosts.get(name)
    except osc_exc.NotFound:
        abort(404)
    return make_json_response(_node_to_view(name, hosts))

