
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

from altai_api.utils import make_json_response
from altai_api.utils.decorators import no_auth_endpoint


def register_entry_points(app):
    # NOTE(imelnikov): we can't url_for as there is no app context
    #   and we can't use app.create_url_adapter because it requires
    #   setting SERVER_NAME config parameter, which is not reliable
    url_adapter = app.url_map.bind(
        app.config['SERVER_NAME'] or 'localhost',
        script_name=app.config['APPLICATION_ROOT'] or '/',
        url_scheme=app.config['PREFERRED_URL_SCHEME'])

    def url_for(endpoint):
        return url_adapter.build(endpoint, {})

    root_endpoints = {}
    for endpoint, function in app.view_functions.iteritems():
        name = getattr(function, 'altai_api_root_endpoint', None)
        if name:
            root_endpoints[name + '-href'] = url_for(endpoint)

    v1_info = { 'major': 1, 'minor': 0 }
    versions = { 'versions': [ v1_info ] }
    v1_root = v1_info.copy()
    v1_root['links'] = root_endpoints

    @app.route('/', methods=('GET',))
    @no_auth_endpoint
    def get_versions():
        """REST API entry point."""
        return make_json_response(versions)

    @app.route('/v1/', methods=('GET',))
    @no_auth_endpoint
    def get_v1_endpoint():
        """Entry point for API v1"""
        return make_json_response(v1_root)

    v1_href = url_for('get_v1_endpoint')
    v1_info['href'] = v1_href
    v1_root['href'] = v1_href

