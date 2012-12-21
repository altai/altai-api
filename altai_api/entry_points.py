
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

from flask import url_for, g

from altai_api.main import app
from altai_api.utils import make_json_response

from altai_api.collection.users import get_user


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


@app.route('/v1/', methods=('GET',))
def get_v1_endpoint():
    """Entry point for API v1"""
    response = _make_v1_info()
    response['links'] = {
        'instance-types-href': url_for('instance_types.list_instance_types')
    }
    return make_json_response(response)


@app.route('/v1/me')
def get_current_user():
    """Current user resource shortcut"""
    uid = g.client_set.http_client.access['user']['id']
    return get_user(uid)

