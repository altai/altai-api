
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

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import *
from altai_api.main import app
from altai_api.utils.decorators import root_endpoint, user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils.misc import from_mb, from_gb, to_mb, to_gb
from altai_api.auth import admin_client_set, client_set_for_tenant


projects = Blueprint('projects', __name__)


def link_for_project(project_id, project_name=None):
    """Make a link object for a project

    If project_name is not provided, it is looked up in the identity_admin
    and passes any exception it raises in case of error.

    """
    if project_name is None:
        try:
            tenant = admin_client_set().identity_admin.tenants.get(project_id)
            project_name = tenant.name
        except osc_exc.NotFound:
            project_name = None
    return {
        u'id': project_id,
        u'name': project_name,
        u'href': url_for('projects.get_project', project_id=project_id)
    }


def link_for_tenant(tenant):
    """Make link object for project identified by tenant"""
    return link_for_project(tenant.id, tenant.name)


def _project_from_nova(tenant, net, quotaset):
    network = None if net is None else {
        u'id': net.id,
        u'name': net.label,
        u'href': url_for('networks.get_network', net_id=net.id)
    }

    result = {
        u'id': tenant.id,
        u'name': tenant.name,
        u'href': url_for('projects.get_project', project_id=tenant.id),
        u'description': tenant.description,
        u'network': network,
        u'stats-href': url_for('projects.get_project_stats',
                               project_id=tenant.id)
    }

    if quotaset is not None:
        result[u'cpus-limit'] = quotaset.cores
        result[u'ram-limit'] = from_mb(quotaset.ram)
        result[u'storage-limit'] = from_gb(quotaset.gigabytes)
        result[u'vms-limit'] = quotaset.instances
    return result


def _network_for_project(project_id):
    for net in admin_client_set().compute.networks.list():
        if net.project_id == project_id:
            return net
    return None


def _quotaset_for_project(project_id):
    return admin_client_set().compute.quotas.get(project_id)


def get_tenant(project_id):
    try:
        if g.is_admin:
            tenant = admin_client_set().identity_admin.tenants.get(project_id)
        else:
            # NOTE(imelnikov): get does not work for public API
            tenant = g.client_set.identity_public.tenants.find(id=project_id)
    except osc_exc.NotFound:
        abort(404)

    # systenant is special entity, not a 'project' in Altai sense
    if tenant.name == app.config['DEFAULT_TENANT']:
        abort(404)
    return tenant


@projects.route('/<project_id>', methods=('GET',))
@user_endpoint
def get_project(project_id):
    tenant = get_tenant(project_id)  # checks permissions
    net = _network_for_project(project_id)
    quotaset = _quotaset_for_project(project_id)

    result = _project_from_nova(tenant, net, quotaset)
    return make_json_response(result)


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('description'),
    st.LinkObject('network'),
    st.Int('cpus-limit'),
    st.Int('ram-limit'),
    st.Int('storage-limit'),
    st.Int('vms-limit')),

    create_required=('name', 'network'),
    allowed=(  # both on creation and update
        'description', 'cpus-limit', 'ram-limit',
        'storage-limit', 'vms-limit')
)


@projects.route('/', methods=('GET',))
@root_endpoint('projects')
@user_endpoint
def list_projects():
    parse_collection_request(_SCHEMA)
    if g.my_projects:
        client = g.client_set.identity_public
    else:
        client = admin_client_set().identity_admin

    tenants = client.tenants.list()
    networks = dict(((net.project_id, net)
                     for net in admin_client_set().compute.networks.list()
                     if net.project_id))
    systenant = app.config['DEFAULT_TENANT']
    # systenant is special entity, not a 'project' in Altai sense
    result = [_project_from_nova(t, networks.get(t.id),
                                 _quotaset_for_project(t.id))
              for t in tenants if t.name != systenant]
    return make_collection_response(u'projects', result)


@projects.route('/<project_id>/stats', methods=('GET',))
@user_endpoint
def get_project_stats(project_id):
    tenant = get_tenant(project_id)
    users = admin_client_set().identity_admin.tenants.list_users(tenant.id)

    tcs = client_set_for_tenant(project_id, fallback_to_api=g.is_admin)
    servers = tcs.compute.servers.list()
    images = tcs.image.images.list()
    local_images = [image for image in images
                    if image.owner == tenant.id]

    return make_json_response({
        u'project': link_for_tenant(tenant),
        u'vms': len(servers),
        u'members': len(users),
        u'local-images': len(local_images),
        u'total-images': len(images)
    })


def _set_quota(tenant_id, data):
    """Set project limits from project dict"""
    kwargs = {}

    if 'cpus-limit' in data:
        kwargs['cores'] = data.get('cpus-limit')
    if 'ram-limit' in data:
        kwargs['ram'] = to_mb(data.get('ram-limit'))
    if 'storage-limit' in data:
        kwargs['gigabytes'] = to_gb(data.get('storage-limit'))
    if 'vms-limit' in data:
        kwargs['instances'] = data.get('vms-limit')

    if kwargs:
        g.client_set.compute.quotas.update(tenant_id, **kwargs)


@projects.route('/', methods=('POST',))
def create_project():
    data = parse_request_data(_SCHEMA.allowed, _SCHEMA.create_required)

    # first, check network
    networks = g.client_set.compute.networks
    try:
        net = networks.get(data['network'])
        assert net.project_id is None
        # TODO(imelnikov): special exception for used networks
    except (KeyError, AssertionError, osc_exc.NotFound):
        raise exc.IllegalValue(name='network',
                               typename='link object',
                               value=data.get('network'))
    tenant = g.client_set.identity_admin.tenants.create(
        data['name'], data.get('description', ''))
    set_audit_resource_id(tenant)

    try:
        networks.associate(net.id, tenant.id)
    except osc_exc.BadRequest:
        tenant.delete()
        raise exc.InvalidRequest('Failed to associate network %r '
                                 'with created project' % data['network'])
    _set_quota(tenant.id, data)
    result = _project_from_nova(tenant, networks.get(net.id),
                                _quotaset_for_project(tenant.id))
    return make_json_response(result)


def _project_has_servers(project_id):
    s = admin_client_set().compute.servers.list(
        detailed=False,
        search_opts=dict(all_tenants=1,
                         tenant_id=project_id,
                         limit=1))
    return len(s) > 0


@projects.route('/<project_id>', methods=('DELETE',))
def delete_project(project_id):
    set_audit_resource_id(project_id)
    tenant = get_tenant(project_id)

    # NOTE(imelnikov): server deletion in OpenStack is asynchronous and
    #   takes a lot of time, so to avoid races we don't delete them here
    if _project_has_servers(project_id):
        raise exc.InvalidRequest("Can't delete project "
                                 "while there are VMs")

    # detach all networks
    net_client = admin_client_set().compute.networks
    for net in net_client.list():
        if net.project_id == tenant.id:
            net_client.disassociate(net)

    try:
        tenant.delete()
    except osc_exc.NotFound:
        pass  # already deleted by someone else
    return make_json_response(None, 204)


@projects.route('/<project_id>', methods=('PUT',))
def update_project(project_id):
    data = parse_request_data(_SCHEMA.allowed)
    set_audit_resource_id(project_id)
    tenant = get_tenant(project_id)

    try:
        if 'description' in data:
            tenant = tenant.update(description=data['description'])
        _set_quota(project_id, data)
    except osc_exc.NotFound:
        abort(404)

    net = _network_for_project(project_id)
    quotaset = _quotaset_for_project(project_id)
    result = _project_from_nova(tenant, net, quotaset)
    return make_json_response(result)

