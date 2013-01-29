
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

from datetime import datetime, timedelta

from tests.db import ContextWrappedDBTestCase
from altai_api.db.audit import AuditDAO


class AuditDAOTestCase(ContextWrappedDBTestCase):

    def setUp(self):
        super(AuditDAOTestCase, self).setUp()
        data = {
            'extra': {},
            'message': 'OK',
            'method': 'POST',
            'project_id': 'PID',
            'remote_address': '127.0.0.1',
            'resource': '/test',
            'resource_id': 'test',
            'response_status': 200,
            'user_id': 'UID'
        }
        record = AuditDAO.create_record(data)
        self.record_id = record.record_id

    def test_get(self):
        record = AuditDAO.get(self.record_id)
        self.assertEquals(record.message, 'OK')
        self.assertEquals(record.resource_id, 'test')
        self.assertEquals(record.user_id, 'UID')
        self.assertEquals(record.response_status, 200)
        delta = datetime.utcnow() - record.timestamp

        # assume tests are rather fast
        self.assertTrue(delta <= timedelta(seconds=5))
        # but not faster then light
        self.assertTrue(delta >= timedelta(0))

    def test_list_all(self):
        l = list(AuditDAO.list_all())
        self.assertEquals(l, [AuditDAO.get(self.record_id)])

