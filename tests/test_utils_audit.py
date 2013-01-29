
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

import mox
from tests import ContextWrappedTestCase
from tests.mocked import MockedTestCase

from flask import g
from altai_api.utils import audit


class AuditTestCase(MockedTestCase):

    def setUp(self):
        super(AuditTestCase, self).setUp()
        self.mox.StubOutWithMock(audit, 'AuditDAO')

    def test_audit_works(self):
        class IsCorrectData(mox.Comparator):
            def equals(inner_self, data):
                self.assertTrue(isinstance(data, dict))
                self.assertEquals(data.get('method'), 'GET')
                self.assertEquals(data.get('message'), 'OK')
                self.assertEquals(data.get('response_status'), 200)
                return True

        self.app.config['AUDIT_VERBOSITY'] = 2
        audit.AuditDAO.create_record(IsCorrectData())

        self.mox.ReplayAll()
        rv = self.client.get('/')
        self.check_and_parse_response(rv)

    def test_audit_db_failure(self):
        self.app.config['AUDIT_VERBOSITY'] = 2
        audit.AuditDAO.create_record(mox.IsA(dict)) \
                .AndRaise(RuntimeError('FAILURE'))

        self.mox.ReplayAll()
        rv = self.client.get('/')
        data = self.check_and_parse_response(rv, status_code=500)
        self.assertTrue('FAILURE' in data.get('message'))

    def test_audit_nonverbose_get(self):
        self.app.config['AUDIT_VERBOSITY'] = 1

        self.mox.ReplayAll()
        rv = self.client.get('/')
        self.check_and_parse_response(rv)
        # let mox ensure that AuditDAO was never called

    def test_audit_nonverbose_400(self):
        self.app.config['AUDIT_VERBOSITY'] = 1

        self.mox.ReplayAll()
        rv = self.client.post('/')
        self.check_and_parse_response(rv, status_code=400)


class SetAuditResourceIdTestCase(ContextWrappedTestCase):

    def setUp(self):
        super(SetAuditResourceIdTestCase, self).setUp()
        g.audit_data = {}

    def test_set_resource_from_string(self):
        arg = 'test'
        audit.set_audit_resource_id(arg)
        self.assertEquals(g.audit_data, {'resource_id': arg})

    def test_set_from_resource(self):
        self.id = 42
        audit.set_audit_resource_id(self)
        self.assertEquals(g.audit_data, {'resource_id': '42'})

    def test_from_other(self):
        audit.set_audit_resource_id(42)
        self.assertEquals(g.audit_data, {'resource_id': '42'})

