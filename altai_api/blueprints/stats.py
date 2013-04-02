
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

from flask import Blueprint, g, url_for

from altai_api import auth
from altai_api.utils import make_json_response
from altai_api.utils import parse_collection_request, make_collection_response
from altai_api.utils.decorators import root_endpoint
from altai_api.utils.decorators import user_endpoint
from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.images import list_all_images
from altai_api.blueprints.projects import link_for_tenant, get_tenant

BP = Blueprint('stats', __name__)


@BP.route('', methods=('GET',))
@root_endpoint('stats')
@user_endpoint
def altai_stats():
    cs = auth.admin_client_set()
    tenants = cs.identity_admin.tenants.list()
    users = cs.identity_admin.users.list()

    # TODO(imelnikov): should we ignore servers in systenant?
    servers = cs.compute.servers.list(search_opts={'all_tenants': 1})
    images = list_all_images(cs.image.images)
    global_images = [image for image in images if image.is_public]

    return make_json_response({
        'projects': len(tenants) - 1,  # not counting systenant
        'instances': len(servers),
        'users': len(users),
        'total-images': len(images),
        'global-images': len(global_images),
        'by-project-stats-href': url_for('stats.list_stats_by_project')
    })


_SCHEMA = Schema((
    st.LinkObject('project'),
    st.Int('members'),
    st.Int('instances'),
    st.Int('local-images'),
    st.Int('total-images')
))


@BP.route('/by-project/', methods=('GET',))
@user_endpoint
def list_stats_by_project():
    parse_collection_request(_SCHEMA)
    cs = auth.admin_client_set()

    if g.my_projects:
        tenants = g.client_set.identity_public.tenants.list()
    else:
        tenants = cs.identity_admin.tenants.list()

    result = {}
    for tenant in tenants:
        if tenant.id != auth.default_tenant_id():
            users = cs.identity_admin.tenants.list_users(tenant.id)
            result[tenant.id] = {
                'project': link_for_tenant(tenant),
                'members': len(users),
                'instances': 0,
                'local-images': 0,
                'total-images': 0,
                'href': url_for('stats.get_project_stats',
                                project_id=tenant.id)
            }

    for server in cs.compute.servers.list(search_opts={'all_tenants': 1}):
        try:
            result[server.tenant_id]['instances'] += 1
        except KeyError:
            pass

    global_images = 0
    for image in list_all_images(cs.image.images):
        if image.is_public:
            global_images += 1
        if image.owner in result:
            result[image.owner]['local-images'] += 1
            if not image.is_public:
                result[image.owner]['total-images'] += 1

    for value in result.itervalues():
        value['total-images'] += global_images
    data = sorted(result.itervalues(), key=lambda s: s['href'])
    return make_collection_response(u'stats', data,
                                    parent_href=url_for('stats.altai_stats'))


@BP.route('/by-project/<project_id>', methods=('GET',))
@user_endpoint
def get_project_stats(project_id):
    tenant = get_tenant(project_id)
    acs = auth.admin_client_set()
    users = acs.identity_admin.tenants.list_users(tenant.id)

    tcs = auth.client_set_for_tenant(project_id, fallback_to_api=g.is_admin)
    servers = tcs.compute.servers.list()
    images = tcs.image.images.list()
    local_images = [image for image in images
                    if image.owner == tenant.id]

    return make_json_response({
        u'project': link_for_tenant(tenant),
        u'instances': len(servers),
        u'members': len(users),
        u'local-images': len(local_images),
        u'total-images': len(images),
        'href': url_for('stats.get_project_stats',
                        project_id=tenant.id)
    })

