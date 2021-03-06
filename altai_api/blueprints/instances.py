
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
from altai_api.blueprints.nodes import link_for_node

from altai_api.db.instance_data import InstanceDataDAO

from novaclient.v1_1.servers import REBOOT_SOFT, REBOOT_HARD


BP = Blueprint('instances', __name__)


def link_for_server(server):
    return {
        u'id': server.id,
        u'href': url_for('instances.get_instance', instance_id=server.id),
        u'name': server.name
    }


_HOST_ATTRIBUTE = 'OS-EXT-SRV-ATTR:host'


def _instance_to_view(server):
    client = admin_client_set()
    project_link = link_for_project(server.tenant_id)
    flavor = client.compute.flavors.get(server.flavor['id'])
    user_link = link_for_user_id(server.user_id)
    image_link = link_for_image(server.image['id'])
    instancedata = InstanceDataDAO.get(server.id)

    href_for = lambda endpoint: url_for(endpoint,
                                        instance_id=server.id)

    result = {
        u'id': server.id,
        u'href': href_for('instances.get_instance'),
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
        u'links': {
            u'reboot': href_for('instances.reboot_instance'),
            u'reset': href_for('instances.reset_instance'),
            u'remove': href_for('instances.remove_instance'),
            u'vnc': href_for('instances.instance_vnc_console'),
            u'console-output': href_for('instances.instance_console_output'),
            u'fw-rules': href_for('instance_fw_rule_sets'
                                  '.list_instance_fw_rule_sets')
        }
    }
    if instancedata:
        if instancedata.expires_at is not None:
            result[u'expires-at'] = instancedata.expires_at
        if instancedata.remind_at is not None:
            result[u'remind-at'] = instancedata.remind_at
    if g.is_admin and hasattr(server, _HOST_ATTRIBUTE):
        result['node'] = link_for_node(getattr(server, _HOST_ATTRIBUTE))
    return result


def fetch_instance(instance_id):
    try:
        instance = admin_client_set().compute.servers.get(instance_id)
    except osc_exc.NotFound:
        abort(404)
    assert_admin_or_project_user(instance.tenant_id, eperm_status=404)
    return instance


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


@BP.route('/', methods=('GET',))
@root_endpoint('instances')
@user_endpoint
def list_instances():
    parse_collection_request(_SCHEMA.sortby)
    if g.my_projects:
        servers = _servers_for_user()
    else:
        servers = g.client_set.compute.servers.list(
                search_opts={'all_tenants': 1})
    result = [_instance_to_view(instance) for instance in servers]
    return make_collection_response(u'instances', result)


@BP.route('/<instance_id>', methods=('GET',))
@user_endpoint
def get_instance(instance_id):
    return make_json_response(_instance_to_view(fetch_instance(instance_id)))


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
            raise exc.InvalidElementValue('fw-rule-sets', 'list', sgid,
                                          'Security group %r does not exist'
                                          % sgid)
        names.append(sg.name)
    return names


@BP.route('/', methods=('POST',))
@user_endpoint
def create_instance():
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
            InstanceDataDAO.create(server.id,
                             expires_at=data.get('expires-at'),
                             remind_at=data.get('remind-at'))
    except osc_exc.OverLimit, e:
        return make_json_response(status_code=403, data={
            'path': request.path,
            'method': request.method,
            'message': 'Limits exceeded (%s)' % str(e)
        })
    set_audit_resource_id(server)
    return make_json_response(_instance_to_view(server))


@BP.route('/<instance_id>', methods=('PUT',))
@user_endpoint
def update_instance(instance_id):
    data = parse_request_data(_SCHEMA.updatable)
    if 'name' in data:
        try:
            fetch_instance(instance_id).update(name=data['name'])
        except osc_exc.NotFound:
            abort(404)
    instance = fetch_instance(instance_id)

    for_instance_data = {}
    if 'expires-at' in data:
        for_instance_data['expires_at'] = data['expires-at']
    if 'remind-at' in data:
        for_instance_data['remind_at'] = data['remind-at']
    if for_instance_data:
        InstanceDataDAO.update(instance.id, **for_instance_data)

    set_audit_resource_id(instance)
    return make_json_response(_instance_to_view(instance))


def _do_remove_instance(instance_id):
    """The real instance removal implementation"""
    try:
        fetch_instance(instance_id).delete()
    except osc_exc.NotFound:
        abort(404)

    InstanceDataDAO.delete(instance_id)
    try:
        return fetch_instance(instance_id)
    except HTTPException:
        return None


@BP.route('/<instance_id>/remove', methods=('POST',))
@user_endpoint
def remove_instance(instance_id):
    parse_request_data()
    server = _do_remove_instance(instance_id)
    set_audit_resource_id(instance_id)
    if server is not None:
        return make_json_response(_instance_to_view(server))
    else:
        return make_json_response(None, status_code=204)


@BP.route('/<instance_id>', methods=('DELETE',))
@user_endpoint
def delete_instance(instance_id):
    set_audit_resource_id(instance_id)
    server = _do_remove_instance(instance_id)
    if server is not None:
        # TODO(imelnikov): wait for server to be gone if Expect: 202-Accepted
        #                  is not in request headers
        return make_json_response(None, status_code=202)
    else:
        return make_json_response(None, status_code=204)


def _do_reboot_instance(instance_id, method):
    """Rebooting implementation.

    Reboot and reset actions differ only by one parameter. Their
    common code lives here.

    """
    set_audit_resource_id(instance_id)
    parse_request_data()
    try:
        fetch_instance(instance_id).reboot(method)
    except osc_exc.NotFound:
        abort(404)
    # Fetch it again, with new status:
    return make_json_response(_instance_to_view(fetch_instance(instance_id)))


@BP.route('/<instance_id>/reboot', methods=('POST',))
@user_endpoint
def reboot_instance(instance_id):
    return _do_reboot_instance(instance_id, REBOOT_SOFT)


@BP.route('/<instance_id>/reset', methods=('POST',))
@user_endpoint
def reset_instance(instance_id):
    return _do_reboot_instance(instance_id, REBOOT_HARD)


@BP.route('/<instance_id>/console-output', methods=('POST',))
@user_endpoint
def instance_console_output(instance_id):
    set_audit_resource_id(instance_id)
    length = int_from_string(request.args.get('length'), allow_none=True)
    g.unused_args.discard('length')

    try:
        server = fetch_instance(instance_id)
        data = server.get_console_output(length=length)
    except osc_exc.NotFound:
        abort(404)

    return make_json_response({
        'instance': link_for_server(server),
        'console-output': data
    })


@BP.route('/<instance_id>/vnc', methods=('POST',))
@user_endpoint
def instance_vnc_console(instance_id):
    set_audit_resource_id(instance_id)

    try:
        server = fetch_instance(instance_id)
        vnc = server.get_vnc_console(console_type='novnc')['console']
    except osc_exc.NotFound:
        abort(404)

    return make_json_response({
        'instance': link_for_server(server),
        'url': vnc['url'],
        'console-type': vnc['type']
    })

