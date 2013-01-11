
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

from flask import url_for

from altai_api.main import app
from altai_api.utils import make_json_response


def _make_v1_info():
    'Make new dictionary with info on version 1'
    return {
        "major": 1,
        "minor": 0,
        "href": url_for('get_v1_endpoint')
    }


@app.route('/', methods=('GET',))
def get_versions():
    """REST API entry point."""
    return make_json_response({
        'versions': [ _make_v1_info() ]
    })


def _root_endpoints():
    for endpoint, function in app.view_functions.iteritems():
        name = getattr(function, 'altai_api_root_endpoint', None)
        if name:
            yield name + '-href', url_for(endpoint)


@app.route('/v1/', methods=('GET',))
def get_v1_endpoint():
    """Entry point for API v1"""
    response = _make_v1_info()
    response['links'] = dict(_root_endpoints())
    return make_json_response(response)

