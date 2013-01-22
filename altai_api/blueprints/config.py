
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2013 Grid Dynamics Consulting Services, Inc
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

from flask import url_for, abort, Blueprint, g, current_app

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils import *
from altai_api.utils.decorators import root_endpoint, user_endpoint

from altai_api.db.config import ConfigDAO


config = Blueprint('config', __name__)

SCHEMAS = {
    'general': Schema((
        st.String('installation-name'),
    )),
    'mail': Schema((
        st.String('sender-name'),
        st.String('sender-mail'),
        st.String('footer'),
    )),
    'invitations': Schema((
        st.Boolean('enabled'),
        st.List(st.String('domains-allowed')),
    )),
    'password-reset': Schema((
        st.Boolean('enabled'),
    )),
}

_USER_VISIBLE_GROUPS = ('general',)

_SCHEMA = Schema((
    st.String('name'),
))


def _link_for_group(group):
    return {
        'name': group,
        'href': url_for('config.get_config', name=group)
    }


def _update_general(general):
    general['authorization-mode'] = 'NATIVE'
    general['openstack-endpoint'] = current_app.config['KEYSTONE_URI']


@config.route('/', methods=('GET',))
@root_endpoint('config')
@user_endpoint
def list_config():
    parse_collection_request(_SCHEMA)
    groups = SCHEMAS if g.is_admin else _USER_VISIBLE_GROUPS
    result = dict(((group, {}) for group in groups))
    for group, element, value in ConfigDAO.list_all():
        try:
            result[group][element] = value
        except KeyError:
            continue

    _update_general(result['general'])
    # NOTE(imelnikov): do it late to override values for
    #   'name' and 'href' if someone put them into database
    for group in groups:
        result[group].update(_link_for_group(group))
    return make_collection_response('config', result.values())


@config.route('/<name>', methods=('GET',))
@user_endpoint
def get_config(name):
    groups = SCHEMAS if g.is_admin else _USER_VISIBLE_GROUPS
    if name not in groups:
        abort(404)
    result = dict(((element, value)
                   for group, element, value in ConfigDAO.list_group(name)
                   if group == name))  # yup, imelnikov is paranoid
    if name == 'general':
        _update_general(result)

    # NOTE(imelnikov): do it late to override values for
    #   'name' and 'href' if someone put them into database
    result.update(_link_for_group(name))
    return make_json_response(result)


@config.route('/<name>', methods=('PUT',))
def update_config(name):
    if name not in SCHEMAS:
        abort(404)
    data = parse_request_data(allowed=SCHEMAS[name])
    set_audit_resource_id(name)
    for element, value in data.iteritems():
        ConfigDAO.set_to(name, element, value)
    return get_config(name)

