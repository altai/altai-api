
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

import openstackclient_base.exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.main import app
from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response, setup_sorting
from altai_api.utils.misc import from_mb, from_gb, to_mb, to_gb
from altai_api.authentication import client_set_for_tenant


projects = Blueprint('projects', __name__)


def link_for_project(project_id, project_name=None):
    """Make a link object for a project

    If project_name is not provided, it is looked up in the identity_admin
    and passes any exception it raises in case of error.

    """
    if project_name is None:
        tenant = g.client_set.identity_admin.tenants.get(project_id)
        project_name = tenant.name
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
    for net in g.client_set.compute.networks.list():
        if net.project_id == project_id:
            return net
    return None


def _quotaset_for_project(project_id):
    return g.client_set.compute.quotas.get(project_id)


def _servers_for_project(project_id):
    return g.client_set.compute.servers.list(search_opts={
        'project_id': project_id,
        'all_tenants': 1
    })


def get_tenant(project_id):
    try:
        tenant = g.client_set.identity_admin.tenants.get(project_id)
    except osc_exc.NotFound:
        abort(404)

    # systenant is special entity, not a 'project' in Altai sense
    if tenant.name == app.config['DEFAULT_TENANT']:
        abort(404)
    return tenant


@projects.route('/<project_id>', methods=('GET',))
def get_project(project_id):
    tenant = get_tenant(project_id)
    net = _network_for_project(project_id)
    quotaset = _quotaset_for_project(project_id)

    result = _project_from_nova(tenant, net, quotaset)
    return make_json_response(result)


@projects.route('/', methods=('GET',))
def list_projects():
    setup_sorting(('id', 'name', 'description', 'network.id', 'network.name'))
    cs = g.client_set
    tenants = cs.identity_admin.tenants.list()
    networks = dict(((net.project_id, net)
                     for net in cs.compute.networks.list()
                     if net.project_id))
    systenant = app.config['DEFAULT_TENANT']
    # systenant is special entity, not a 'project' in Altai sense
    result = [_project_from_nova(t, networks.get(t.id),
                                 _quotaset_for_project(t.id))
              for t in tenants if t.name != systenant]
    return make_collection_response(u'projects', result)


@projects.route('/<project_id>/stats', methods=('GET',))
def get_project_stats(project_id):
    tenant = get_tenant(project_id)

    users = tenant.list_users()
    servers = _servers_for_project(tenant.id)

    tcs = client_set_for_tenant(tenant_id=tenant.id)
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
    data = request.json

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


@projects.route('/<project_id>', methods=('DELETE',))
def delete_project(project_id):
    tenant = get_tenant(project_id)

    # kill all vms
    for server in _servers_for_project(tenant.id):
        server.delete()

    # detach all networks
    net_client = g.client_set.compute.networks
    for net in net_client.list():
        if net.project_id == tenant.id:
            net_client.disassociate(net)

    tenant.delete()
    return make_json_response(None, 204)


@projects.route('/<project_id>', methods=('PUT',))
def update_project(project_id):
    data = request.json
    tenant = get_tenant(project_id)

    if 'name' in data or 'description' in data:
        tenant = tenant.update(
            name=data.get('name', tenant.name),
            description=data.get('description', tenant.description))

    _set_quota(project_id, data)

    net = _network_for_project(project_id)
    quotaset = _quotaset_for_project(project_id)
    result = _project_from_nova(tenant, net, quotaset)
    return make_json_response(result)

