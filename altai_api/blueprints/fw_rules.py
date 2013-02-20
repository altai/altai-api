
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

from flask import url_for, g, Blueprint, abort
from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api import auth
from altai_api.utils import *
from altai_api.utils.parsers import int_from_string
from altai_api.utils.decorators import user_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st


fw_rules = Blueprint('fw_rules', __name__)


def _fw_rule_dict_from_nova(rule):
    """Convert dict from nova representation to ours.

    Such dicts can be found in secgroup.rules list.

    """
    rule_id = unicode(rule['id'])
    return {
        u'id': rule_id,
        u'href': url_for('fw_rules.get_fw_rule',
                         fw_rule_set_id=rule['parent_group_id'],
                         rule_id=rule_id),
        u'protocol': rule['ip_protocol'].upper(),
        u'port-range-first': rule['from_port'],
        u'port-range-last': rule['to_port'],
        u'source': rule['ip_range'].get('cidr')
    }


def _fw_rule_object_from_nova(rule):
    """Convert SecurityGroupRule to our representation"""
    rule_id = str(rule.id)
    return {
        u'id': rule_id,
        u'href': url_for('fw_rules.get_fw_rule',
                         fw_rule_set_id=rule.parent_group_id,
                         rule_id=rule_id),
        u'protocol': rule.ip_protocol.upper(),
        u'port-range-first': rule.from_port,
        u'port-range-last': rule.to_port,
        u'source': rule.ip_range.get('cidr')
    }


def _get_security_group(sg_id):
    try:
        sg = auth.admin_client_set().compute.security_groups.get(sg_id)
    except osc_exc.NotFound:
        abort(404)
    auth.assert_admin_or_project_user(sg.tenant_id, eperm_status=404)
    # TODO(imelnikov): do we need to check if group belongs to systenant?
    return sg


_SCHEMA = Schema((
    st.String('id'),
    st.String('protocol'),
    st.Cidr('source'),
    st.Int('port-range-first', min_val=-1, max_val=65535),
    st.Int('port-range-last', min_val=-1, max_val=65535)),

    required=('protocol', 'source'),
    allowed=('port-range-first', 'port-range-last')
)


@fw_rules.route('/', methods=('GET',))
@user_endpoint
def list_fw_rules(fw_rule_set_id):
    parse_collection_request(_SCHEMA)
    result = [_fw_rule_dict_from_nova(rule)
              for rule in _get_security_group(fw_rule_set_id).rules]
    parent_href = url_for('fw_rule_sets.get_fw_rule_set',
                          fw_rule_set_id=fw_rule_set_id)
    return make_collection_response(u'rules', result,
                                    parent_href=parent_href)


def _find_rule(sg_id, rule_id):
    """Find rule record in given security group"""
    # rule ids are (sic!) ints
    rid = int_from_string(rule_id, on_error=lambda value_: abort(404))
    for rule in _get_security_group(sg_id).rules:
        if rule['id'] == rid:
            return rule
    abort(404)


@fw_rules.route('/<rule_id>', methods=('GET',))
@user_endpoint
def get_fw_rule(fw_rule_set_id, rule_id):
    rule = _find_rule(fw_rule_set_id, rule_id)
    return make_json_response(_fw_rule_dict_from_nova(rule))


@fw_rules.route('/', methods=('POST',))
@user_endpoint
def create_fw_rule(fw_rule_set_id):
    data = parse_request_data(_SCHEMA.allowed, _SCHEMA.required)
    protocol = data['protocol']
    if protocol not in ('TCP', 'UDP', 'ICMP'):
        raise exc.IllegalValue('protocol', 'string', protocol)
    sg = _get_security_group(fw_rule_set_id)

    from_port = data.get('port-range-first', -1)
    to_port = data.get('port-range-last', from_port)
    client = auth.client_set_for_tenant(sg.tenant_id,
                                        fallback_to_api=g.is_admin,
                                        eperm_status=404)
    try:
        rule = client.compute.security_group_rules.create(
            parent_group_id=fw_rule_set_id,
            ip_protocol=protocol.lower(),
            from_port=from_port,
            to_port=to_port,
            cidr=data['source'])
    except osc_exc.NotFound:
        abort(404)
    set_audit_resource_id(rule)
    return make_json_response(_fw_rule_object_from_nova(rule))


@fw_rules.route('/<rule_id>', methods=('DELETE',))
@user_endpoint
def delete_fw_rule(fw_rule_set_id, rule_id):
    set_audit_resource_id(rule_id)
    # we check that group exists and has given rule by looking for it there
    _find_rule(fw_rule_set_id, rule_id)
    try:
        g.client_set.compute.security_group_rules.delete(rule_id)
    except osc_exc.NotFound:
        pass  # already deleted by someone else
    return make_json_response(None, 204)

