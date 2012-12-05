
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

import json

from tests import doubles
from tests.mocked import MockedTestCase, mock_client_set

from openstackclient_base import exceptions as osc_exc

from altai_api.collection import fw_rule_sets


class ConvertersTestCase(MockedTestCase):

    def test_sg_from_nova_works(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=u'PID', name=u'Tenant')
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=42, name=u'Test SG',
                          description=u'XXX', tenant_id=u'PID')

        expected = {
            u'id': u'42',
            u'name': u'Test SG',
            u'description': u'XXX',
            u'project': {
                u'id': u'PID',
                u'href': '/v1/projects/PID',
                u'name': u'Tenant'
            },
            u'href': u'/v1/fw-rule-sets/42'
        }

        self.mox.ReplayAll()

        with self.app.test_request_context():
            res = fw_rule_sets._sg_from_nova(sg, tenant)
        self.assertEquals(expected, res)


    def test_sg_from_nova_wrong_tenant_raises(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=u'PID', name=u'Tenant')
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'SGID', name=u'Test SG',
                          description=u'XXX', tenant_id=u'WRONG TENANT')

        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.assertRaises(ValueError,
                              fw_rule_sets._sg_from_nova, sg, tenant)



class RuleSetsTestCase(MockedTestCase):

    def setUp(self):
        super(RuleSetsTestCase, self).setUp()
        self.mox.StubOutWithMock(fw_rule_sets, 'client_set_for_tenant')
        self.mox.StubOutWithMock(fw_rule_sets, '_sg_from_nova')

    def test_list_works(self):
        tenants = (
            doubles.make(self.mox, doubles.Tenant, name='t1', id=u'PID1'),
            doubles.make(self.mox, doubles.Tenant, name='systenant', id=u'S'),
            doubles.make(self.mox, doubles.Tenant, name='t2', id=u'PID2'))

        self.fake_client_set.identity_admin.tenants.list().AndReturn(tenants)

        tcs1 = mock_client_set(self.mox)
        fw_rule_sets.client_set_for_tenant(u'PID1').AndReturn(tcs1)
        tcs1.compute.security_groups.list().AndReturn(['SG1', 'SG2'])
        fw_rule_sets._sg_from_nova('SG1', tenants[0]).AndReturn('REPLY1')
        fw_rule_sets._sg_from_nova('SG2', tenants[0]).AndReturn('REPLY2')

        tcs2 = mock_client_set(self.mox)
        fw_rule_sets.client_set_for_tenant(u'PID2').AndReturn(tcs2)
        tcs2.compute.security_groups.list().AndReturn(['SG3'])
        fw_rule_sets._sg_from_nova('SG3', tenants[2]).AndReturn('REPLY3')

        expected = {
            'collection': {
                'name': 'fw-rule-sets',
                'size': 3
            },
            'fw-rule-sets': ['REPLY1', 'REPLY2', 'REPLY3']
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_works(self):
        arg = u'42'
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'SGID', name=u'Test SG',
                          description=u'XXX', tenant_id=u'TENANT')

        self.fake_client_set.compute.security_groups.get(arg).AndReturn(sg)
        self.fake_client_set.identity_admin.tenants.get(u'TENANT')\
                .AndReturn('TENANT')
        fw_rule_sets._sg_from_nova(sg, 'TENANT').AndReturn('REPLY')
        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s' % arg)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_not_found(self):
        arg = u'42'
        self.fake_client_set.compute.security_groups.get(arg)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s' % arg)
        self.check_and_parse_response(rv, 404)

    def test_delete_works(self):
        arg = u'42'
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'SGID', name=u'Test SG',
                          description=u'XXX', tenant_id=u'TENANT')

        self.fake_client_set.compute.security_groups.get(arg).AndReturn(sg)
        sg.delete()

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/fw-rule-sets/%s' % arg)
        self.check_and_parse_response(rv, 204)

    def test_delete_not_found(self):
        arg = u'42'
        self.fake_client_set.compute.security_groups.get(arg)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/fw-rule-sets/%s' % arg)
        self.check_and_parse_response(rv, 404)


class CreateFwRuleSetTestCase(MockedTestCase):

    def setUp(self):
        super(CreateFwRuleSetTestCase, self).setUp()
        self.mox.StubOutWithMock(fw_rule_sets, '_sg_from_nova')
        self.mox.StubOutWithMock(fw_rule_sets, 'client_set_for_tenant')

    def interact(self, params, expected_status_code=200):
        rv = self.client.post('/v1/fw-rule-sets/',
                              content_type='application/json',
                              data=json.dumps(params))
        return self.check_and_parse_response(rv, expected_status_code)


    def test_create_works(self):
        params = {
            'project': u'TENANT',
            'name': u'Test SG',
            'description': u'Description'
        }
        tenant = doubles.make(self.mox, doubles.Tenant,
                              name='t1', id=u'TENANT')

        tcs = mock_client_set(self.mox)
        self.fake_client_set.identity_admin.tenants\
                .get(tenant.id).AndReturn(tenant)
        fw_rule_sets.client_set_for_tenant(tenant.id).AndReturn(tcs)
        tcs.compute.security_groups.create(
            name=u'Test SG', description=u'Description').AndReturn('SG')
        fw_rule_sets._sg_from_nova('SG', tenant).AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_bad_project(self):
        params = {
            'project': u'TENANT',
            'name': u'Test SG',
            'description': u'Description'
        }

        tcs = mock_client_set(self.mox)
        self.fake_client_set.identity_admin.tenants\
                .get(u'TENANT').AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        data = self.interact(params, 400)
        self.assertEquals('project', data.get('element-name'))

