
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

from flask import current_app as app
from flask import url_for, g, Blueprint, abort

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import *
from altai_api.utils.decorators import root_endpoint, user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils.misc import from_mb, to_mb
from altai_api.auth import admin_client_set


BP = Blueprint('projects', __name__)


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


def _project_to_view(tenant, net, quotaset):
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
        u'links': {
            u'stats': url_for('stats.get_project_stats',
                              project_id=tenant.id),
            u'manage-users': url_for('project_users.list_project_users',
                                     project_id=tenant.id)
        }
    }

    if quotaset is not None:
        result[u'cpus-limit'] = quotaset.cores
        result[u'ram-limit'] = from_mb(quotaset.ram)
        result[u'instances-limit'] = quotaset.instances
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
    if tenant.name == app.config['SYSTENANT']:
        abort(404)
    return tenant


@BP.route('/<project_id>', methods=('GET',))
@user_endpoint
def get_project(project_id):
    tenant = get_tenant(project_id)  # checks permissions
    net = _network_for_project(project_id)
    quotaset = _quotaset_for_project(project_id)

    result = _project_to_view(tenant, net, quotaset)
    return make_json_response(result)


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('description', allow_empty=True),
    st.LinkObject('network'),
    st.Int('cpus-limit'),
    st.Int('ram-limit'),
    st.Int('instances-limit')),

    create_required=('name', 'network'),
    allowed=(  # both on creation and update
        'description', 'cpus-limit', 'ram-limit',
        'instances-limit')
)


@BP.route('/', methods=('GET',))
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
    systenant = app.config['SYSTENANT']
    # systenant is special entity, not a 'project' in Altai sense
    result = [_project_to_view(t, networks.get(t.id),
                                 _quotaset_for_project(t.id))
              for t in tenants if t.name != systenant]
    return make_collection_response(u'projects', result)


def _set_quota(tenant_id, data):
    """Set project limits from project dict"""
    kwargs = {}

    if 'cpus-limit' in data:
        kwargs['cores'] = data.get('cpus-limit')
    if 'ram-limit' in data:
        kwargs['ram'] = to_mb(data.get('ram-limit'))
    if 'instances-limit' in data:
        kwargs['instances'] = data.get('instances-limit')

    if kwargs:
        g.client_set.compute.quotas.update(tenant_id, **kwargs)


@BP.route('/', methods=('POST',))
def create_project():
    data = parse_request_data(_SCHEMA.allowed, _SCHEMA.create_required)

    # first, check network
    networks = g.client_set.compute.networks
    network_id = data['network']
    try:
        net = networks.get(data['network'])
    except osc_exc.NotFound:
        raise exc.InvalidElementValue('network', 'link object', network_id,
                                      'Network does not exist.')
    if net.project_id is not None:
        raise exc.InvalidElementValue('network', 'link object', network_id,
                                      'Network is already used.')
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
    result = _project_to_view(tenant, networks.get(net.id),
                                _quotaset_for_project(tenant.id))
    return make_json_response(result)


def _project_has_servers(project_id):
    s = admin_client_set().compute.servers.list(
        detailed=False,
        search_opts=dict(all_tenants=1,
                         tenant_id=project_id,
                         limit=1))
    return len(s) > 0


def _project_has_images(project_id):
    image_list = admin_client_set().image.images.list(
        filters=dict(is_public=False, tenant_id=project_id),
        limit=1)
    return len(image_list) > 0


@BP.route('/<project_id>', methods=('DELETE',))
def delete_project(project_id):
    set_audit_resource_id(project_id)
    tenant = get_tenant(project_id)

    # NOTE(imelnikov): server deletion in OpenStack is asynchronous and
    #   takes a lot of time, so to avoid races we don't delete them here
    if _project_has_servers(project_id):
        raise exc.InvalidRequest("Can't delete project "
                                 "while there are instances in it")

    # NOTE(imelnikov): image deletion would work OK here, but for consistency
    #   and safety we opt for check instead
    if _project_has_images(project_id):
        raise exc.InvalidRequest("Can't delete project "
                                 "while there are images in it")

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


@BP.route('/<project_id>', methods=('PUT',))
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
    result = _project_to_view(tenant, net, quotaset)
    return make_json_response(result)

