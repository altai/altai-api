
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

from altai_api.utils import *

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.authentication import client_set_for_tenant
from altai_api.blueprints.vms import fetch_vm
from altai_api.blueprints.fw_rule_sets import link_for_security_group


vm_fw_rule_sets = Blueprint('vm_fw_rule_sets', __name__)


# NOTE(imelnikov): Next function asks for server so client have to fetch
# server before calling it, because nova returns error 500 on invalid
# server id which is really hard to distinguish from real errors.
def _security_groups_for_server(server):
    return g.client_set.compute.security_groups._list(
        '/servers/%s/os-security-groups' % server.id, 'security_groups')


def _find_sg_on_server(server, set_id):
    try:
        sg_id = int(set_id)
    except ValueError:
        abort(404)

    secgroups = _security_groups_for_server(server)
    try:
        sg = (sg for sg in secgroups if sg.id == sg_id).next()
    except StopIteration:
        abort(404)
    return sg


_SCHEMA = Schema((
    st.String('id'),
    st.String('name')),

    required=('id',)
)


@vm_fw_rule_sets.route('/', methods=('GET',))
def list_vm_fw_rule_sets(vm_id):
    parse_collection_request(_SCHEMA)
    server = fetch_vm(vm_id)
    result = [link_for_security_group(sg)
              for sg in _security_groups_for_server(server)]
    parent_href = url_for('vms.get_vm', vm_id=vm_id)
    return make_collection_response(u'fw-rule-sets', result,
                                    parent_href=parent_href)


@vm_fw_rule_sets.route('/<set_id>', methods=('GET',))
def get_vm_fw_rule_set(vm_id, set_id):
    server = fetch_vm(vm_id)
    sg = _find_sg_on_server(server, set_id)
    return make_json_response(link_for_security_group(sg))


@vm_fw_rule_sets.route('/', methods=('POST',))
def add_vm_fw_rule_set(vm_id):
    server = fetch_vm(vm_id)
    set_id = parse_request_data(required=_SCHEMA.required)['id']
    try:
        sg = g.client_set.compute.security_groups.get(set_id)
    except osc_exc.NotFound:
        raise exc.IllegalValue(name='id', typename='string', value=set_id)

    try:
        tcs = client_set_for_tenant(server.tenant_id)
        tcs.compute.servers.add_security_group(server, sg.name)
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))
    return make_json_response(link_for_security_group(sg))


@vm_fw_rule_sets.route('/<set_id>', methods=('DELETE',))
def remove_vm_fw_rule_set(vm_id, set_id):
    server = fetch_vm(vm_id)
    sg = _find_sg_on_server(server, set_id)
    tcs = client_set_for_tenant(server.tenant_id)

    try:
        tcs.compute.servers.remove_security_group(server, sg.name)
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))
    return make_json_response(None, status_code=204)

