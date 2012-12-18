
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
from datetime import datetime

from tests import doubles
from tests.mocked import MockedTestCase, mock_client_set

from openstackclient_base import exceptions as osc_exc
from altai_api.collection import vms

from novaclient.v1_1.servers import REBOOT_SOFT, REBOOT_HARD


class VmFromNovaTestCase(MockedTestCase):
    maxDiff = None

    def test_vm_from_nova_works(self):
        # DATA
        vm = doubles.make(self.mox, doubles.Server,
                          id=u'VMID',
                          name=u'test vm',
                          user_id=u'UID',
                          tenant_id=u'TENANT',
                          addresses={
                              u'some-network': [
                                  {
                                      u'version': 4,
                                      u'addr': u'10.5.1.3'
                                  },
                                  {
                                      u'version': 6,
                                      u'addr': u'::1'
                                  }
                              ]
                          },
                          accessIPv4=u'',
                          accessIPv6=u'',
                          image={ u'id': u'IMAGE', },
                          flavor={ u'id': u'1', },
                          status=u'BUILD',
                          updated=u'2012-12-12T06:20:37Z',
                          hostId=u'6186525952c6568e1f6f5ae666c6',
                          key_name=u'',
                          created=u'2012-12-12T06:20:27Z',
                          metadata={})
        tenant = doubles.make(self.mox, doubles.Tenant,
                              name=u'test project', id=u'TENANT')
        flavor = doubles.make(self.mox, doubles.Flavor,
                              name=u'test instance type', id=u'1')
        user = doubles.make(self.mox, doubles.User,
                            name=u'test user', id=u'UID')
        image = doubles.make(self.mox, doubles.Image,
                            name=u'test image', id=u'IMAGE')

        expected = {
            u'id': u'VMID',
            u'href': '/v1/vms/VMID',
            u'name': u'test vm',
            u'project': {
                u'id': u'TENANT',
                u'name': u'test project',
                u'href': '/v1/projects/TENANT',
            },
            u'state': u'BUILD',
            u'ipv4': [ u'10.5.1.3' ],
            u'image': {
                u'id': u'IMAGE',
                u'name': u'test image',
                u'href': '/v1/images/IMAGE'
            },
            u'created': datetime(2012, 12, 12, 6, 20, 27),
            u'created-by': {
                u'id': u'UID',
                u'name': u'test user',
                u'href': '/v1/users/UID'
            },
            u'instance-type': {
                u'id': u'1',
                u'href': '/v1/instance-types/1',
                u'name': u'test instance type'
            },
            u'tags': [],
            u'actions': {
                u'reboot': '/v1/vms/VMID/reboot',
                u'reset': '/v1/vms/VMID/reset',
                u'remove': '/v1/vms/VMID/remove',
                u'add-tags': '/v1/vms/VMID/add-tags',
                u'remove-tags': '/v1/vms/VMID/remove-tags'
            }
        }

        # ACTION
        client = self.fake_client_set
        client.identity_admin.tenants.get(u'TENANT').AndReturn(tenant)
        client.compute.flavors.get(u'1').AndReturn(flavor)
        client.identity_admin.users.get(u'UID').AndReturn(user)
        client.image.images.get(u'IMAGE').AndReturn(image)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = vms._vm_from_nova(vm)
        self.assertEquals(result, expected)


class VmsListTestCase(MockedTestCase):

    def setUp(self):
        super(VmsListTestCase, self).setUp()
        self.mox.StubOutWithMock(vms, '_vm_from_nova')

    def test_list_vms_works(self):
        self.fake_client_set.compute.servers\
                .list(search_opts={'all_tenants': 1})\
                .AndReturn([u'VM1', u'VM2'])
        vms._vm_from_nova(u'VM1').AndReturn(u'R1')
        vms._vm_from_nova(u'VM2').AndReturn(u'R2')

        expected = {
            u'collection': {
                u'name': u'vms',
                u'size': 2
            },
            u'vms': [ u'R1', u'R2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/vms/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_vm_works(self):
        self.fake_client_set.compute.servers.get(u'VMID').AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/vms/VMID')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_vm_not_found(self):
        self.fake_client_set.compute.servers.get(u'VMID')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/vms/VMID')
        self.check_and_parse_response(rv, 404)


class CreateTestCase(MockedTestCase):

    def setUp(self):
        super(CreateTestCase, self).setUp()
        self.mox.StubOutWithMock(vms, '_vm_from_nova')
        self.mox.StubOutWithMock(vms, 'client_set_for_tenant')
        self.tcs = mock_client_set(self.mox)

    def interact(self, data, expected_status_code=200):
        rv = self.client.post('/v1/vms/',
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)


    def test_create_password(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
            u'admin-pass': u'p@ssw0rd'
        }
        vms.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=None,
            admin_pass=u'p@ssw0rd'
        ).AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_overlimit(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor'
        }
        vms.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=None,
            admin_pass=None
        ).AndRaise(osc_exc.OverLimit('failure'))

        self.mox.ReplayAll()
        data = self.interact(params, expected_status_code=403)
        self.assertTrue('limits' in data.get('message', '').lower())

    def test_create_keypair(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
            u'ssh-key-pair': u'thisiskey'
        }
        vms.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=u'thisiskey',
            admin_pass=None
        ).AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_fw_rule_sets(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
            u'fw-rule-sets': [u'3', u'8']
        }
        sgs = [
            doubles.make(self.mox, doubles.SecurityGroup, id=u'3', name='sg3'),
            doubles.make(self.mox, doubles.SecurityGroup, id=u'8', name='sg8')
        ]
        vms.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.security_groups.get(u'3').AndReturn(sgs[0])
        self.tcs.compute.security_groups.get(u'8').AndReturn(sgs[1])
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=['sg3', 'sg8'],
            key_name=None,
            admin_pass=None
        ).AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_fw_rule_set_not_found(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
            u'fw-rule-sets': [u'3', u'8']
        }
        vms.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.security_groups.get(u'3')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        data = self.interact(params, expected_status_code=400)
        self.assertEquals(u'3', data.get('element-value'))
        self.assertEquals(u'fw-rule-sets', data.get('element-name'))

class ActionsTestCase(MockedTestCase):

    def setUp(self):
        super(ActionsTestCase, self).setUp()
        self.server = doubles.make(self.mox, doubles.Server, id=u'VICTIM')
        self.mox.StubOutWithMock(vms, '_vm_from_nova')

    def interact(self, url, data, expected_status_code=200):
        rv = self.client.post(url,
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_reboot_works(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)
        s.reboot(REBOOT_SOFT)
        self.fake_client_set.compute.servers.get(s.id).AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact('/v1/vms/%s/reboot' % s.id, {})
        self.assertEquals(data, 'REPLY')

    def test_reboot_not_found(self):
        self.fake_client_set.compute.servers.get(u'VMID')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/vms/VMID/reboot', {}, expected_status_code=404)

    def test_reboot_vm_checks_input(self):
        self.mox.ReplayAll()
        data = self.interact('/v1/vms/%s/reboot' % self.server.id,
                             {'role': 'victim'},
                             expected_status_code=400)
        self.assertEquals('role', data.get('element-name'))


    # NOTE(imelnikov): reset is almost the same as reboot, so
    #  there is no need to repeat all that tests once again
    def test_reset_works(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)
        s.reboot(REBOOT_HARD)
        self.fake_client_set.compute.servers.get(s.id).AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact('/v1/vms/%s/reset' % s.id, {})
        self.assertEquals(data, 'REPLY')

    def test_remove_vm_works(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)
        s.delete()
        self.fake_client_set.compute.servers.get(s.id).AndReturn('VM1')
        vms._vm_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact('/v1/vms/%s/remove' % s.id, {})
        self.assertEquals(data, 'REPLY')

    def test_remove_vm_fast(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)
        s.delete()
        self.fake_client_set.compute.servers.get(s.id)\
                .AndRaise(osc_exc.NotFound('gone'))

        self.mox.ReplayAll()
        self.interact('/v1/vms/%s/remove' % s.id, {},
                      expected_status_code=204)

    def test_remove_vm_not_found(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/vms/%s/remove' % s.id, {},
                      expected_status_code=404)
    def test_remove_vm_checks_input(self):
        self.mox.ReplayAll()
        data = self.interact('/v1/vms/%s/remove' % self.server.id,
                             {'role': 'victim'},
                             expected_status_code=400)
        self.assertEquals('role', data.get('element-name'))

    def test_delete_vm_works(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)
        s.delete()
        self.fake_client_set.compute.servers.get(s.id)\
                .AndRaise(osc_exc.NotFound('gone'))

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/vms/%s' % s.id)
        self.check_and_parse_response(rv, status_code=204)

    def test_delete_vm_pretends_waiting(self):
        s = self.server
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)
        s.delete()
        self.fake_client_set.compute.servers.get(s.id).AndReturn(s)

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/vms/%s' % s.id)
        self.check_and_parse_response(rv, status_code=202)


