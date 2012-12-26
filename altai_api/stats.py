
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

from flask import g

import openstackclient_base.exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.utils.decorators import root_endpoint

from altai_api.main import app
from altai_api.utils import make_json_response
from altai_api.collection.images import list_all_images


@app.route('/v1/stats', methods=('GET',))
@root_endpoint('stats')
def altai_stats():
    cs = g.client_set
    tenants = cs.identity_admin.tenants.list()
    users = cs.identity_admin.users.list()

    # TODO(imelnikov): should we ignore servers in systenant?
    servers = cs.compute.servers.list(search_opts={'all_tenants': 1})
    images = list_all_images()
    global_images = [image for image in images if image.is_public]

    return make_json_response({
        'projects': len(tenants) - 1,  # not counting systenant
        'vms': len(servers),
        'users': len(users),
        'total-images': len(images),
        'global-images': len(global_images)
    })

