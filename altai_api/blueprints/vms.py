
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
from flask.exceptions import HTTPException

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import *
from altai_api.utils.decorators import root_endpoint, user_endpoint
from altai_api.utils.collection import get_matcher_argument

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils.parsers import timestamp_from_openstack, int_from_string

from altai_api.auth import (client_set_for_tenant, admin_client_set,
                            current_user_project_ids,
                            assert_admin_or_project_user)

from altai_api.blueprints.users import link_for_user_id
from altai_api.blueprints.projects import link_for_project
from altai_api.blueprints.images import link_for_image

from altai_api.db.vm_data import VmDataDAO

from novaclient.v1_1.servers import REBOOT_SOFT, REBOOT_HARD


vms = Blueprint('vms', __name__)


def link_for_server(server):
    return {
        u'id': server.id,
        u'href': url_for('vms.get_vm', vm_id=server.id),
        u'name': server.name
    }


def _vm_from_nova(server):
    client = admin_client_set()
    project_link = link_for_project(server.tenant_id)
    flavor = client.compute.flavors.get(server.flavor['id'])
    user_link = link_for_user_id(server.user_id)
    image_link = link_for_image(server.image['id'])
    vmdata = VmDataDAO.get(server.id)

    result = {
        u'id': server.id,
        u'href': url_for('vms.get_vm', vm_id=server.id),
        u'name': server.name,
        u'project': project_link,
        u'created-by': user_link,
        u'image': image_link,
        u'instance-type': {
            u'id': flavor.id,
            u'name': flavor.name,
            u'href': url_for('instance_types.get_instance_type',
                             instance_type_id=flavor.id)
        },
        u'created': timestamp_from_openstack(server.created),
        u'state': server.status,
        u'ipv4': [elem['addr']
                  for val in server.addresses.itervalues()
                  for elem in val if elem['version'] == 4],
        u'actions': {
            u'reboot': url_for('vms.reboot_vm', vm_id=server.id),
            u'reset': url_for('vms.reset_vm', vm_id=server.id),
            u'remove': url_for('vms.remove_vm', vm_id=server.id),
            u'vnc': url_for('vms.vm_vnc_console', vm_id=server.id),
            u'console-output': url_for('vms.vm_console_output',
                                       vm_id=server.id),
        }
    }
    if vmdata:
        if vmdata.expires_at is not None:
            result[u'expires-at'] = vmdata.expires_at
        if vmdata.remind_at is not None:
            result[u'remind-at'] = vmdata.remind_at
    return result


def fetch_vm(vm_id):
    try:
        vm = admin_client_set().compute.servers.get(vm_id)
    except osc_exc.NotFound:
        abort(404)
    assert_admin_or_project_user(vm.tenant_id, eperm_status=404)
    return vm


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('state'),
    st.Timestamp('created'),
    st.Timestamp('expires-at', is_nullable=True),
    st.Timestamp('remind-at', is_nullable=True),
    st.Ipv4('ipv4'),
    st.LinkObject('created-by'),
    st.LinkObject('project'),
    st.LinkObject('instance-type'),
    st.LinkObject('image'),
    st.List(st.LinkObject('fw-rule-sets')),
    st.String('admin-pass'),
    st.String('ssh-key-pair')),

    create_required=('name', 'project', 'image', 'instance-type'),
    create_allowed=('fw-rule-sets', 'admin-pass', 'ssh-key-pair',
                    'expires-at', 'remind-at'),
    sortby=('id', 'name', 'state', 'created', 'ipv4',
            'created-by', 'project', 'instance-type', 'image'),
    updatable=('name', 'expires-at', 'remind-at')
)


def _servers_for_user():
    project_id = get_matcher_argument('project', 'eq')
    if project_id is not None:
        projects = (project_id,)
    else:
        projects = get_matcher_argument('project', 'in')

    result = []
    for project_id in current_user_project_ids():
        if projects is None or project_id in projects:
            cs = client_set_for_tenant(project_id)
            result.extend(cs.compute.servers.list())
    return result


@vms.route('/', methods=('GET',))
@root_endpoint('vms')
@user_endpoint
def list_vms():
    parse_collection_request(_SCHEMA.sortby)
    if g.my_projects:
        servers = _servers_for_user()
    else:
        servers = g.client_set.compute.servers.list(
                search_opts={'all_tenants': 1})
    return make_collection_response( u'vms', [_vm_from_nova(vm)
                                              for vm in servers])


@vms.route('/<vm_id>', methods=('GET',))
@user_endpoint
def get_vm(vm_id):
    return make_json_response(_vm_from_nova(fetch_vm(vm_id)))


def _security_group_ids_to_names(security_groups_ids, sg_manager):
    """Get security group IDs list and return list of their names

    Returns None if argument evaluates to false (e.g. is None or
    empty list).

    """
    if not security_groups_ids:
        return None
    names = []
    for sgid in security_groups_ids:
        try:
            sg = sg_manager.get(sgid)
        except osc_exc.NotFound:
            raise exc.IllegalValue('fw-rule-sets', 'list', sgid)
        names.append(sg.name)
    return names


@vms.route('/', methods=('POST',))
@user_endpoint
def create_vm():
    data = parse_request_data(_SCHEMA.create_allowed, _SCHEMA.create_required)

    tcs = client_set_for_tenant(data['project'])
    security_groups = _security_group_ids_to_names(data.get('fw-rule-sets'),
                                                   tcs.compute.security_groups)

    try:
        server = tcs.compute.servers.create(
            name=data['name'],
            image=data['image'],
            flavor=data['instance-type'],
            security_groups=security_groups,
            key_name=data.get('ssh-key-pair'),
            admin_pass=data.get('admin-pass'))
        if 'expires-at' in data or 'remind-at' in data:
            VmDataDAO.create(server.id,
                             expires_at=data.get('expires-at'),
                             remind_at=data.get('remind-at'))
    except osc_exc.OverLimit, e:
        return make_json_response(status_code=403, data={
            'path': request.path,
            'method': request.method,
            'message': 'Limits exceeded (%s)' % str(e)
        })
    set_audit_resource_id(server)
    return make_json_response(_vm_from_nova(server))


@vms.route('/<vm_id>', methods=('PUT',))
@user_endpoint
def update_vm(vm_id):
    data = parse_request_data(_SCHEMA.updatable)
    if 'name' in data:
        try:
            fetch_vm(vm_id).update(name=data['name'])
        except osc_exc.NotFound:
            abort(404)
    vm = fetch_vm(vm_id)

    for_vm_data = {}
    if 'expires-at' in data:
        for_vm_data['expires_at'] = data['expires-at']
    if 'remind-at' in data:
        for_vm_data['remind_at'] = data['remind-at']
    if for_vm_data:
        VmDataDAO.update(vm.id, **for_vm_data)

    set_audit_resource_id(vm)
    return make_json_response(_vm_from_nova(vm))


def _do_remove_vm(vm_id):
    """The real VM removal implementation"""
    try:
        fetch_vm(vm_id).delete()
    except osc_exc.NotFound:
        abort(404)

    VmDataDAO.delete(vm_id)
    try:
        return fetch_vm(vm_id)
    except HTTPException:
        return None


@vms.route('/<vm_id>/remove', methods=('POST',))
@user_endpoint
def remove_vm(vm_id):
    parse_request_data()
    server = _do_remove_vm(vm_id)
    set_audit_resource_id(vm_id)
    if server is not None:
        return make_json_response(_vm_from_nova(server))
    else:
        return make_json_response(None, status_code=204)


@vms.route('/<vm_id>', methods=('DELETE',))
@user_endpoint
def delete_vm(vm_id):
    set_audit_resource_id(vm_id)
    server = _do_remove_vm(vm_id)
    if server is not None:
        # TODO(imelnikov): wait for server to be gone if Expect: 202-Accepted
        #                  is not in request headers
        return make_json_response(None, status_code=202)
    else:
        return make_json_response(None, status_code=204)


def _do_reboot_vm(vm_id, method):
    """Rebooting implementation.

    Reboot and reset actions differ only by one parameter. Their
    common code lives here.

    """
    set_audit_resource_id(vm_id)
    parse_request_data()
    try:
        fetch_vm(vm_id).reboot(method)
    except osc_exc.NotFound:
        abort(404)
    # Fetch it again, with new status:
    return make_json_response(_vm_from_nova(fetch_vm(vm_id)))


@vms.route('/<vm_id>/reboot', methods=('POST',))
@user_endpoint
def reboot_vm(vm_id):
    return _do_reboot_vm(vm_id, REBOOT_SOFT)


@vms.route('/<vm_id>/reset', methods=('POST',))
@user_endpoint
def reset_vm(vm_id):
    return _do_reboot_vm(vm_id, REBOOT_HARD)


@vms.route('/<vm_id>/console-output', methods=('POST',))
@user_endpoint
def vm_console_output(vm_id):
    set_audit_resource_id(vm_id)
    length = int_from_string(request.args.get('length'), allow_none=True)
    g.unused_args.discard('length')

    try:
        server = fetch_vm(vm_id)
        data = server.get_console_output(length=length)
    except osc_exc.NotFound:
        abort(404)

    return make_json_response({
        'vm': link_for_server(server),
        'console-output': data
    })


@vms.route('/<vm_id>/vnc', methods=('POST',))
@user_endpoint
def vm_vnc_console(vm_id):
    set_audit_resource_id(vm_id)

    try:
        server = fetch_vm(vm_id)
        vnc = server.get_vnc_console(console_type='novnc')['console']
    except osc_exc.NotFound:
        abort(404)

    return make_json_response({
        'vm': link_for_server(server),
        'url': vnc['url'],
        'console-type': vnc['type']
    })

