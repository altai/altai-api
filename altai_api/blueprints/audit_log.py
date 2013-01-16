
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

from flask import url_for, g, Blueprint
from openstackclient_base import exceptions as osc_exc

from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response
from altai_api.utils import parse_collection_request

from altai_api.utils.decorators import root_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.blueprints.projects import link_for_project

from altai_api.db.audit import AuditDAO


audit_log = Blueprint('audit_log', __name__)


def _record_to_dict(record, user_name, project_name):
    if record.user_id:
        user_ref = {
            u'id': record.user_id,
            u'name': user_name,
            u'href': url_for('users.get_user', user_id=record.user_id)
        }
    else:
        user_ref = None

    if record.project_id:
        project_ref = link_for_project(record.project_id, project_name)
    else:
        project_ref = None

    result = {
        'id': record.record_id,
        'href': url_for('audit_log.get_log_record',
                        record_id=record.record_id),
        'user': user_ref,
        'project': project_ref
    }
    for name in ('resource', 'method', 'response_status', 'message',
                 'remote_address', 'timestamp', 'extra'):
        result[name] = getattr(record, name)
    return result


def record_from_database(record, user_name=None, project_name=None):
    iadm = g.client_set.identity_admin
    if record.user_id is not None and user_name is None:
        try:
            user_name = iadm.users.get(record.user_id).name
        except osc_exc.NotFound:
            pass
    if record.project_id is not None and project_name is None:
        try:
            project_name = iadm.tenants.get(record.project_id).name
        except osc_exc.NotFound:
            pass
    return _record_to_dict(record, user_name, project_name)


_SCHEMA = Schema((
    st.String('id'),
    st.String('message'),
    st.String('method'),
    st.String('resource'),
    st.Ipv4('remote_address'),
    st.Int('response_status'),
    st.Timestamp('timestamp'),
    st.LinkObject('user'),
    st.LinkObject('project'),
))


@audit_log.route('/')
@root_endpoint('audit-log')
def list_all_records():
    parse_collection_request(_SCHEMA)
    # TODO(imelnikov): user and tenant names
    result = [record_from_database(record)
              for record in AuditDAO.list_all()]
    return make_collection_response(u'audit-log', result)


@audit_log.route('/<record_id>')
def get_log_record(record_id):
    result = record_from_database(AuditDAO.get(record_id))
    return make_json_response(result)

