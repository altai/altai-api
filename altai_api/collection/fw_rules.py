
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
from altai_api.utils import make_collection_response, setup_sorting

from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc


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
        u'port-range-firt': rule['from_port'],
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
        u'port-range-firt': rule.from_port,
        u'port-range-last': rule.to_port,
        u'source': rule.ip_range.get('cidr')
    }


def _get_security_group(sg_id):
    try:
        sg = g.client_set.compute.security_groups.get(sg_id)
    except osc_exc.NotFound:
        abort(404)
    # TODO(imelnikov): do we need to check if group belongs to systenant?
    return sg


@fw_rules.route('/', methods=('GET',))
def list_fw_rules(fw_rule_set_id):
    setup_sorting(('id', 'protocol', 'source',
                   'port-range-first', 'port-range-last'))

    result = [_fw_rule_dict_from_nova(rule)
              for rule in _get_security_group(fw_rule_set_id).rules]
    parent_href = url_for('fw_rule_sets.get_fw_rule_set',
                          fw_rule_set_id=fw_rule_set_id)
    return make_collection_response(u'rules', result,
                                    parent_href=parent_href)


def _find_rule(sg_id, rule_id):
    """Find rule record in given security group"""
    try:
        # rule ids are (sic!) ints
        # TODO(imelnikov): replace with parse_int
        rid = int(rule_id)
        assert str(rid) == rule_id
    except (ValueError, AssertionError):
        abort(404)

    for rule in _get_security_group(sg_id).rules:
        if rule['id'] == rid:
            return rule
    abort(404)


@fw_rules.route('/<rule_id>', methods=('GET',))
def get_fw_rule(fw_rule_set_id, rule_id):
    rule = _find_rule(fw_rule_set_id, rule_id)
    return make_json_response(_fw_rule_dict_from_nova(rule))


@fw_rules.route('/', methods=('POST',))
def create_fw_rule(fw_rule_set_id):
    data = request.json
    from_port = data.get('port-range-first', -1)
    to_port = data.get('port-range-last', from_port)
    rule = g.client_set.compute.security_group_rules.create(
        parent_group_id=fw_rule_set_id,
        ip_protocol=data['protocol'].lower(),
        from_port=from_port,
        to_port=to_port,
        cidr=data['source'])
    return make_json_response(_fw_rule_object_from_nova(rule))


@fw_rules.route('/<rule_id>', methods=('DELETE',))
def delete_fw_rule(fw_rule_set_id, rule_id):
    # we check that group exists and has given rule by looking for it there
    _find_rule(fw_rule_set_id, rule_id)
    g.client_set.compute.security_group_rules.delete(rule_id)
    return make_json_response(None, 204)
