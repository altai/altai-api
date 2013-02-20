
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
from altai_api.utils.parsers import int_from_string
from altai_api.utils.decorators import user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.auth import (client_set_for_tenant, admin_client_set,
                            assert_admin_or_project_user)
from altai_api.blueprints.vms import fetch_vm
from altai_api.blueprints.fw_rule_sets import link_for_security_group


vm_fw_rule_sets = Blueprint('vm_fw_rule_sets', __name__)


def _security_groups_for_server(vm_id):
    try:
        result = admin_client_set().compute.security_groups._list(
            '/servers/%s/os-security-groups' % vm_id,
            'security_groups')
    except osc_exc.HttpException:
        fetch_vm(vm_id)  # check that server exists; if not, abort(404)
        raise            # if server exists, re-raise: it was other error
    if not result:
        fetch_vm(vm_id)  # check that server exists and is visible
    else:
        assert_admin_or_project_user(result[0].tenant_id, eperm_status=404)
    return result


def _find_sg_on_server(vm_id, set_id):
    # ids are (sic!) ints
    sg_id = int_from_string(set_id, on_error=lambda value_: abort(404))
    for sg in _security_groups_for_server(vm_id):
        if sg.id == sg_id:
            return sg
    abort(404)


_SCHEMA = Schema((
    st.String('id'),
    st.String('name')),

    required=('id',)
)


@vm_fw_rule_sets.route('/', methods=('GET',))
@user_endpoint
def list_vm_fw_rule_sets(vm_id):
    parse_collection_request(_SCHEMA)
    result = [link_for_security_group(sg)
              for sg in _security_groups_for_server(vm_id)]
    parent_href = url_for('vms.get_vm', vm_id=vm_id)
    return make_collection_response(u'fw-rule-sets', result,
                                    parent_href=parent_href)


@vm_fw_rule_sets.route('/<set_id>', methods=('GET',))
@user_endpoint
def get_vm_fw_rule_set(vm_id, set_id):
    sg = _find_sg_on_server(vm_id, set_id)
    return make_json_response(link_for_security_group(sg))


@vm_fw_rule_sets.route('/', methods=('POST',))
@user_endpoint
def add_vm_fw_rule_set(vm_id):
    server = fetch_vm(vm_id)
    set_id = parse_request_data(required=_SCHEMA.required)['id']
    set_audit_resource_id(set_id)
    try:
        sg = admin_client_set().compute.security_groups.get(set_id)
    except osc_exc.NotFound:
        raise exc.IllegalValue(name='id', typename='string', value=set_id)

    tcs = client_set_for_tenant(server.tenant_id, fallback_to_api=g.is_admin)
    try:
        tcs.compute.servers.add_security_group(server, sg.name)
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))
    return make_json_response(link_for_security_group(sg))


@vm_fw_rule_sets.route('/<set_id>', methods=('DELETE',))
@user_endpoint
def remove_vm_fw_rule_set(vm_id, set_id):
    server = fetch_vm(vm_id)
    sg = _find_sg_on_server(vm_id, set_id)
    tcs = client_set_for_tenant(server.tenant_id, fallback_to_api=g.is_admin)

    try:
        tcs.compute.servers.remove_security_group(server, sg.name)
    except osc_exc.BadRequest, e:
        raise exc.InvalidRequest(str(e))
    except osc_exc.HttpException:
        _find_sg_on_server(vm_id, set_id)  # to abort(404) if vm or sg gone
        raise

    return make_json_response(None, status_code=204)

