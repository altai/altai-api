
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

from altai_api.collection import vm_fw_rule_sets


class VmRuleSetsTestCase(MockedTestCase):

    def setUp(self):
        super(VmRuleSetsTestCase, self).setUp()
        self.server = doubles.make(self.mox, doubles.Server,
                                   id=u'VMID', name=u'ExampleVM')

        self.sg = doubles.make(self.mox, doubles.SecurityGroup,
                               id=2, name=u'ExampleSG')
        self.sg2 = doubles.make(self.mox, doubles.SecurityGroup,
                               id=142, name=u'AnotherSG')
        self.sg_id = unicode(self.sg.id)

    def test_list_works(self):
        self.mox.StubOutWithMock(vm_fw_rule_sets, 'link_for_security_group')

        compute = self.fake_client_set.compute
        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups._list(
            '/servers/%s/os-security-groups' % self.server.id,
            'security_groups').AndReturn([u'SG1', u'SG2', u'SG3'])

        vm_fw_rule_sets.link_for_security_group(u'SG1').AndReturn(u'L1')
        vm_fw_rule_sets.link_for_security_group(u'SG2').AndReturn(u'L2')
        vm_fw_rule_sets.link_for_security_group(u'SG3').AndReturn(u'L3')

        expected = {
            'collection': {
                'parent-href': '/v1/vms/%s' % self.server.id,
                'name': 'fw-rule-sets',
                'size': 3
            },
            'fw-rule-sets': [u'L1', u'L2', u'L3']
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/vms/%s/fw-rule-sets/' % self.server.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_list_not_found(self):
        self.fake_client_set.compute.servers.get(self.server.id) \
                .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        rv = self.client.get('/v1/vms/%s/fw-rule-sets/' % self.server.id)
        self.check_and_parse_response(rv, status_code=404)

    def test_get_works(self):
        compute = self.fake_client_set.compute
        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups._list(
            '/servers/%s/os-security-groups' % self.server.id,
            'security_groups').AndReturn([self.sg2, self.sg])
        expected = {
            u'id': u'2',
            u'name': u'ExampleSG',
            u'href': '/v1/fw-rule-sets/2'
        }

        self.mox.ReplayAll()

        rv = self.client.get('/v1/vms/%s/fw-rule-sets/%s'
                             % (self.server.id, u'2'))
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_vm_not_found(self):
        self.fake_client_set.compute.servers.get(self.server.id) \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/vms/%s/fw-rule-sets/%s'
                             % (self.server.id, u'2'))
        self.check_and_parse_response(rv, status_code=404)

    def test_get_no_sg(self):
        compute = self.fake_client_set.compute
        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups._list(
            '/servers/%s/os-security-groups' % self.server.id,
            'security_groups').AndReturn([self.sg2, self.sg])

        self.mox.ReplayAll()

        rv = self.client.get('/v1/vms/%s/fw-rule-sets/%s'
                             % (self.server.id, u'1555'))
        self.check_and_parse_response(rv, status_code=404)


class AddFwRuleSetToVMTestCase(MockedTestCase):
    def setUp(self):
        super(AddFwRuleSetToVMTestCase, self).setUp()
        self.mox.StubOutWithMock(vm_fw_rule_sets, 'client_set_for_tenant')
        self.mox.StubOutWithMock(vm_fw_rule_sets, 'link_for_security_group')
        self.server = doubles.make(self.mox, doubles.Server,
                                   id=u'VMID', name=u'ExampleVM')
        self.sg = doubles.make(self.mox, doubles.SecurityGroup,
                               id=2, name=u'ExampleSG')
        self.sg_id = unicode(self.sg.id)

    def interact(self, expected_status_code=200):
        rv = self.client.post('/v1/vms/%s/fw-rule-sets/' % self.server.id,
                              content_type='application/json',
                              data=json.dumps({'id': self.sg_id}))
        return self.check_and_parse_response(
                rv, status_code=expected_status_code)

    def test_add_works(self):
        compute = self.fake_client_set.compute
        tcs = mock_client_set(self.mox)

        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups.get(self.sg_id).AndReturn(self.sg)
        vm_fw_rule_sets.client_set_for_tenant(self.server.tenant_id)\
                .AndReturn(tcs)
        tcs.compute.servers.add_security_group(self.server, self.sg.name)
        vm_fw_rule_sets.link_for_security_group(self.sg).AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact()
        self.assertEquals(data, 'REPLY')

    def test_add_no_server(self):
        compute = self.fake_client_set.compute
        compute.servers.get(self.server.id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=404)

    def test_add_no_sg(self):
        compute = self.fake_client_set.compute

        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups.get(self.sg_id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        data = self.interact(expected_status_code=400)
        self.assertEquals('id', data.get('element-name'))
        self.assertEquals(self.sg_id, data.get('element-value'))

    def test_add_failure(self):
        compute = self.fake_client_set.compute
        tcs = mock_client_set(self.mox)

        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups.get(self.sg_id).AndReturn(self.sg)
        vm_fw_rule_sets.client_set_for_tenant(self.server.tenant_id)\
                .AndReturn(tcs)
        tcs.compute.servers.add_security_group(self.server, self.sg.name)\
                .AndRaise(osc_exc.BadRequest('failure'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=400)


class RemoveFwRuleSetFromVMTestCase(MockedTestCase):

    def setUp(self):
        super(RemoveFwRuleSetFromVMTestCase, self).setUp()
        self.mox.StubOutWithMock(vm_fw_rule_sets, 'link_for_security_group')
        self.mox.StubOutWithMock(vm_fw_rule_sets, 'client_set_for_tenant')
        self.server = doubles.make(self.mox, doubles.Server,
                                   id=u'VMID', name=u'ExampleVM',
                                   tenant_id=u'FWPROJECT')
        self.sg = doubles.make(self.mox, doubles.SecurityGroup,
                               id=2, name=u'ExampleSG',
                               tenant_id=u'FWPROJECT')
        self.tcs = mock_client_set(self.mox)
        self.sg_id = unicode(self.sg.id)

    def interact(self, expected_status_code=204):
        rv = self.client.delete('/v1/vms/%s/fw-rule-sets/%s'
                                % (self.server.id, self.sg_id))
        return self.check_and_parse_response(
                rv, status_code=expected_status_code)

    def test_remove_works(self):
        compute = self.fake_client_set.compute

        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups._list(
            '/servers/%s/os-security-groups' % self.server.id,
            'security_groups').AndReturn([self.sg])
        vm_fw_rule_sets.client_set_for_tenant(u'FWPROJECT')\
                .AndReturn(self.tcs)
        self.tcs.compute.servers.remove_security_group(
            self.server, self.sg.name)

        self.mox.ReplayAll()
        self.interact()

    def test_remove_no_server(self):
        compute = self.fake_client_set.compute
        compute.servers.get(self.server.id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=404)

    def test_remove_no_sg(self):
        compute = self.fake_client_set.compute

        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups._list(
            '/servers/%s/os-security-groups' % self.server.id,
            'security_groups').AndReturn([])

        self.mox.ReplayAll()
        self.interact(expected_status_code=404)

    def test_remove_failure(self):
        compute = self.fake_client_set.compute

        compute.servers.get(self.server.id).AndReturn(self.server)
        compute.security_groups._list(
            '/servers/%s/os-security-groups' % self.server.id,
            'security_groups').AndReturn([self.sg])
        vm_fw_rule_sets.client_set_for_tenant(u'FWPROJECT')\
                .AndReturn(self.tcs)
        self.tcs.compute.servers.remove_security_group(
            self.server, self.sg.name) \
                .AndRaise(osc_exc.BadRequest('failure'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=400)


