
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

from altai_api.main import app
from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response
from altai_api.utils import parse_collection_request

from altai_api.utils.decorators import root_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.authentication import client_set_for_tenant
from altai_api.blueprints.projects import link_for_tenant

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc


fw_rule_sets = Blueprint('fw_rule_sets', __name__)


def link_for_security_group(secgroup):
    """Make link object for given security group"""
    sgid = unicode(secgroup.id)
    return {
        u'id': sgid,
        u'href': url_for('fw_rule_sets.get_fw_rule_set', fw_rule_set_id=sgid),
        u'name': secgroup.name
    }


def _sg_from_nova(secgroup, tenant):
    if secgroup.tenant_id != tenant.id:
        # this is a bit of well tested paranoia
        raise ValueError('Firewall rule set %s is from tenant %s, not %s'
                         % (secgroup.name, secgroup.tenant_id, tenant.id))
    result = link_for_security_group(secgroup)
    result.update((
        (u'description', secgroup.description),
        (u'project', link_for_tenant(tenant))
    ))
    return result


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('description'),
    st.LinkObject('project')
))


@fw_rule_sets.route('/', methods=('GET',))
@root_endpoint('fw-rule-sets')
def list_fw_rule_sets():
    parse_collection_request(_SCHEMA)
    tenants = g.client_set.identity_admin.tenants.list()
    systenant = app.config['DEFAULT_TENANT']

    result = []
    for tenant in tenants:
        if tenant.name != systenant:
            tcs = client_set_for_tenant(tenant.id)
            for sg in tcs.compute.security_groups.list():
                result.append(_sg_from_nova(sg, tenant))
    return make_collection_response(u'fw-rule-sets', result)


@fw_rule_sets.route('/<fw_rule_set_id>', methods=('GET',))
def get_fw_rule_set(fw_rule_set_id):
    try:
        sg = g.client_set.compute.security_groups.get(fw_rule_set_id)
    except osc_exc.NotFound:
        abort(404)
    tenant = g.client_set.identity_admin.tenants.get(sg.tenant_id)
    # if tenant is not found, something is wrong, so 500 is right response
    return make_json_response(_sg_from_nova(sg, tenant))


@fw_rule_sets.route('/', methods=('POST',))
def create_fw_rule_set():
    data = request.json
    try:
        tenant = g.client_set.identity_admin.tenants.get(data['project'])
    except osc_exc.NotFound:
        raise exc.IllegalValue(name=u'project',
                               typename=u'link object',
                               value=data['project'])

    tcs = client_set_for_tenant(tenant.id)
    sg = tcs.compute.security_groups.create(name=data[u'name'],
                                            description=data[u'description'])
    return make_json_response(_sg_from_nova(sg, tenant))


@fw_rule_sets.route('/<fw_rule_set_id>', methods=('DELETE',))
def delete_fw_rule_set(fw_rule_set_id):
    try:
        sg = g.client_set.compute.security_groups.get(fw_rule_set_id)
        # if sg is deleted between this two lines, next call raises NotFound
        sg.delete()
    except osc_exc.NotFound:
        abort(404)

    return make_json_response(None, status_code=204)

