
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

from altai_api.utils import make_json_response
from altai_api.utils import timestamp_from_openstack
from altai_api.utils import make_collection_response, setup_sorting

from altai_api.authentication import client_set_for_tenant
from altai_api.collection.users import link_for_user, fetch_user
from altai_api.collection.projects import link_for_tenant

from novaclient.v1_1.servers import REBOOT_SOFT, REBOOT_HARD


vms = Blueprint('vms', __name__)

def _vm_from_nova(server):
    client = g.client_set
    tenant = client.identity_admin.tenants.get(server.tenant_id)
    flavor = client.compute.flavors.get(server.flavor['id'])
    user = fetch_user(server.user_id)

    result = {
        u'id': server.id,
        u'href': url_for('vms.get_vm', vm_id=server.id),
        u'name': server.name,
        u'project': link_for_tenant(tenant),
        u'created-by': link_for_user(user),
        # TODO(imelnikov): make this link object when images are implemented
        u'image': server.image['id'],
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
            u'add-tags': url_for('vms.add_vm_tags', vm_id=server.id),
            u'remove-tags': url_for('vms.remove_vm_tags', vm_id=server.id),
        },
        u'tags': [
            # TODO(imelnikov): implement it
        ]
    }
    return result


def fetch_vm(vm_id):
    try:
        return g.client_set.compute.servers.get(vm_id)
    except osc_exc.NotFound:
        abort(404)


@vms.route('/', methods=('GET',))
def list_vms():
    setup_sorting(('id', 'name', 'state', 'created',
                   'project.name', 'project.id', 'image.name', 'image.id'))
    l = g.client_set.compute.servers.list
    return make_collection_response(
        u'vms', [_vm_from_nova(vm) for vm in l(search_opts={'all_tenants': 1})])


@vms.route('/<vm_id>', methods=('GET',))
def get_vm(vm_id):
    return make_json_response(_vm_from_nova(fetch_vm(vm_id)))


def _security_group_ids_to_names(security_groups_ids, sg_manager):
    """Get security group IDs list and return list of their names

    Returns None if argument evaluates to false (e.g. is None or
    empty list.

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
def create_vm():
    data = request.json
    name, project_id, image_id, instance_type_id = [
        data[param] for param in ('name', 'project', 'image', 'instance-type')]

    tcs = client_set_for_tenant(project_id)
    security_groups = _security_group_ids_to_names(data.get('fw-rule-sets'),
                                                   tcs.compute.security_groups)

    # TODO(imelnikov): implement metatada (meta= arg) and tags
    server = tcs.compute.servers.create(
        name=name,
        image=image_id,
        flavor=instance_type_id,
        security_groups=security_groups,
        key_name=data.get('ssh-key-pair'),
        admin_pass=data.get('admin-pass')
    )
    return make_json_response(_vm_from_nova(server))


def _do_remove_vm(vm_id):
    """The real VM removal implementation"""
    server = fetch_vm(vm_id)
    server.delete()
    try:
        return fetch_vm(vm_id)
    except HTTPException:
        return None

@vms.route('/<vm_id>/remove', methods=('POST',))
def remove_vm(vm_id):
    if request.json:
        # it's dict -- checked in check_request_headers
        raise exc.UnknownElement(name=request.json.keys()[0])
    server = _do_remove_vm(vm_id)
    if server is not None:
        return make_json_response(_vm_from_nova(server))
    else:
        return make_json_response(None, status_code=204)

@vms.route('/<vm_id>', methods=('DELETE',))
def delete_vm(vm_id):
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
    if request.json != {}:
        # it must be dict, anyway
        raise exc.UnknownElement(name=request.json.keys()[0])
    server = fetch_vm(vm_id)
    server.reboot(method)
    # TODO(imelnikov): error handling
    # and fetch it again, with new status
    return make_json_response(_vm_from_nova(fetch_vm(vm_id)))

@vms.route('/<vm_id>/reboot', methods=('POST',))
def reboot_vm(vm_id):
    return _do_reboot_vm(vm_id, REBOOT_SOFT)

@vms.route('/<vm_id>/reset', methods=('POST',))
def reset_vm(vm_id):
    return _do_reboot_vm(vm_id, REBOOT_HARD)


@vms.route('/<vm_id>/add-tags')
def add_vm_tags(vm_id):
    raise NotImplemented('VM tags are not implemented yet')


@vms.route('/<vm_id>/remove-tags')
def remove_vm_tags(vm_id):
    raise NotImplemented('VM tags are not implemented yet')

