
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

from datetime import datetime
from openstackclient_base import exceptions as osc_exc

from tests import doubles
from tests import ContextWrappedTestCase
from tests.mocked import MockedTestCase
from altai_api.db.audit import AuditRecord

from altai_api.blueprints import audit_log


class RecordToDictTestCase(ContextWrappedTestCase):
    def test_record_to_dict_works(self):
        now = datetime.utcnow()
        data = {
            'extra': {'foo': 'bar'},
            'message': 'OK',
            'method': 'POST',
            'project_id': 'PID',
            'remote_address': '127.0.0.1',
            'resource': '/test',
            'response_status': 200,
            'user_id': 'UID'
        }
        record = AuditRecord(**data)
        record.record_id = 'ID'
        record.timestamp = now

        expected = {
            'id': 'ID',
            'href': '/v1/audit-log/ID',
            'message': 'OK',
            'method': 'POST',
            'project': {
                'href': '/v1/projects/PID',
                'id': 'PID',
                'name': 'PROJECT'
            },
            'user': {
                'href': '/v1/users/UID',
                'id': 'UID',
                'name': 'USER'
            },
            'remote_address': '127.0.0.1',
            'resource': '/test',
            'response_status': 200,
            'timestamp': now,
            'extra': {'foo': 'bar'},
        }

        result = audit_log._record_to_dict(record, 'USER', 'PROJECT')
        self.assertEquals(result, expected)

    def test_record_to_dict_nulls(self):
        now = datetime.utcnow()
        data = {
            'extra': {'foo': 'bar'},
            'message': None,
            'method': 'POST',
            'project_id': None,
            'remote_address': '127.0.0.1',
            'resource': '/test',
            'response_status': 200,
            'user_id': None
        }
        record = AuditRecord(**data)
        record.record_id = 'ID'
        record.timestamp = now

        expected = {
            'id': 'ID',
            'href': '/v1/audit-log/ID',
            'message': None,
            'method': 'POST',
            'project': None,
            'user': None,
            'remote_address': '127.0.0.1',
            'resource': '/test',
            'response_status': 200,
            'timestamp': now,
            'extra': {'foo': 'bar'},
        }

        result = audit_log._record_to_dict(record, 'USER', 'PROJECT')
        self.assertEquals(result, expected)


class RecordFromDatabaseTestCase(MockedTestCase, ContextWrappedTestCase):
    def setUp(self):
        super(RecordFromDatabaseTestCase, self).setUp()
        self.mox.StubOutWithMock(audit_log, '_record_to_dict')
        self.iadm = self.fake_client_set.identity_admin

    def test_all_nones(self):
        record = AuditRecord(user_id=None, project_id=None)
        audit_log._record_to_dict(record, None, None).AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record)
        self.assertEquals('REPLY', reply)

    def test_has_user_name(self):
        record = AuditRecord(user_id='UID', project_id=None)
        audit_log._record_to_dict(record, 'user', None)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record, 'user')
        self.assertEquals('REPLY', reply)

    def test_get_user_name(self):
        record = AuditRecord(user_id='UID', project_id=None)
        user = doubles.make(self.mox, doubles.User, name='USERNAME')
        self.iadm.users.get('UID').AndReturn(user)
        audit_log._record_to_dict(record, 'USERNAME', None)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record)
        self.assertEquals('REPLY', reply)

    def test_user_not_found(self):
        record = AuditRecord(user_id='UID', project_id=None)
        self.iadm.users.get('UID').AndRaise(osc_exc.NotFound('failure'))
        audit_log._record_to_dict(record, None, None)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record)
        self.assertEquals('REPLY', reply)

    def test_has_project_name(self):
        record = AuditRecord(project_id='PID', user_id=None)
        audit_log._record_to_dict(record, None, 'project')\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record, None, 'project')
        self.assertEquals('REPLY', reply)

    def test_get_project_name(self):
        record = AuditRecord(project_id='PID', user_id=None)
        project = doubles.make(self.mox, doubles.Tenant, name='PROJECT')
        self.iadm.tenants.get('PID').AndReturn(project)
        audit_log._record_to_dict(record, None, 'PROJECT')\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record)
        self.assertEquals('REPLY', reply)

    def test_project_not_found(self):
        record = AuditRecord(project_id='PID', user_id=None)
        self.iadm.tenants.get('PID').AndRaise(osc_exc.NotFound('failure'))
        audit_log._record_to_dict(record, None, None)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        reply = audit_log.record_to_view(record)
        self.assertEquals('REPLY', reply)


class AuditLogTestCase(MockedTestCase):
    def setUp(self):
        super(AuditLogTestCase, self).setUp()
        self.mox.StubOutWithMock(audit_log, 'AuditDAO')
        self.mox.StubOutWithMock(audit_log, 'record_to_view')

    def test_list_works(self):
        audit_log.AuditDAO.list_all().AndReturn(['A1', 'A2'])
        audit_log.record_to_view('A1').AndReturn('R1')
        audit_log.record_to_view('A2').AndReturn('R2')
        expected = {
            'collection': {
                'name': 'audit-log',
                'size': 2
            },
            'audit-log': [ 'R1', 'R2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/audit-log/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_works(self):
        record_id = 'RID'
        audit_log.AuditDAO.get(record_id).AndReturn('RECORD')
        audit_log.record_to_view('RECORD').AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/audit-log/%s' % record_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

