
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

from flask import g, request, after_this_request, current_app

from altai_api.db.audit import AuditDAO


def setup_audit():
    g.audit_data = {
        'resource': request.path,
        'method': request.method,
        'remote_address': request.remote_addr,

        # The following MUST be there, but may be updated later
        'user_id': None,
        'project_id': None,
        'message': None,
        'extra': {}
    }
    if current_app.config['AUDIT_VERBOSITY'] > 0:
        after_this_request(save_audit_data)


def set_audit_resource_id(obj):
    if isinstance(obj, basestring):
        g.audit_data['resource_id'] = obj
    elif hasattr(obj, 'id'):
        g.audit_data['resource_id'] = str(obj.id)
    else:
        g.audit_data['resource_id'] = str(obj)


_INTERESTING_STATUSES = set([200, 201, 202, 204, 403])


def save_audit_data(response):
    data = g.audit_data
    status = response.status_code

    if current_app.config['AUDIT_VERBOSITY'] < 2:
        # don't save certain data
        if data['method'] == 'GET':
            return response
        if status not in _INTERESTING_STATUSES:
            return response

    if data.get('response_status') is None:
        data['response_status'] = status
    if data['message'] is None and status in (200, 201, 202, 204):
        data['message'] = 'OK'

    AuditDAO.create_record(data)

    return response

