
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
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import *

from altai_api.utils.decorators import root_endpoint, user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.auth import (client_set_for_tenant, admin_client_set,
                            assert_admin_or_project_user)
from altai_api.blueprints.projects import link_for_project


BP = Blueprint('fw_rule_sets', __name__)


def link_for_security_group(secgroup):
    """Make link object for given security group"""
    sgid = unicode(secgroup.id)
    return {
        u'id': sgid,
        u'href': url_for('fw_rule_sets.get_fw_rule_set', fw_rule_set_id=sgid),
        u'name': secgroup.name
    }


def _sg_from_nova(secgroup, project_name=None):
    result = link_for_security_group(secgroup)
    result.update((
        (u'description', secgroup.description),
        (u'project', link_for_project(secgroup.tenant_id, project_name))
    ))
    return result


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('description'),
    st.LinkObject('project')),

    required=('name', 'project'),
    allowed=('description',)
)


@BP.route('/', methods=('GET',))
@root_endpoint('fw-rule-sets')
@user_endpoint
def list_fw_rule_sets():
    parse_collection_request(_SCHEMA)
    if g.my_projects:
        tenants = g.client_set.identity_public.tenants.list()
    else:
        tenants = admin_client_set().identity_admin.tenants.list()

    result = []
    for tenant in tenants:
        if tenant.name != app.config['SYSTENANT']:
            tcs = client_set_for_tenant(tenant.id, fallback_to_api=g.is_admin)
            for sg in tcs.compute.security_groups.list():
                result.append(_sg_from_nova(sg, tenant.name))
    return make_collection_response(u'fw-rule-sets', result)


@BP.route('/<fw_rule_set_id>', methods=('GET',))
@user_endpoint
def get_fw_rule_set(fw_rule_set_id):
    try:
        sg = g.client_set.compute.security_groups.get(fw_rule_set_id)
    except osc_exc.NotFound:
        abort(404)
    assert_admin_or_project_user(sg.tenant_id, eperm_status=404)
    return make_json_response(_sg_from_nova(sg))


@BP.route('/', methods=('POST',))
@user_endpoint
def create_fw_rule_set():
    data = parse_request_data(_SCHEMA.allowed, _SCHEMA.required)
    tcs = client_set_for_tenant(data['project'], eperm_status=404,
                                fallback_to_api=g.is_admin)
    sg = tcs.compute.security_groups.create(
        name=data['name'], description=data.get('description', ''))
    set_audit_resource_id(sg)
    return make_json_response(_sg_from_nova(sg))


@BP.route('/<fw_rule_set_id>', methods=('DELETE',))
@user_endpoint
def delete_fw_rule_set(fw_rule_set_id):
    try:
        sg = admin_client_set().compute.security_groups.get(fw_rule_set_id)
        assert_admin_or_project_user(sg.tenant_id, eperm_status=404)
        sg.delete()
    except osc_exc.NotFound:
        abort(404)

    set_audit_resource_id(sg)
    return make_json_response(None, status_code=204)

