
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

import json
from datetime import datetime

from tests import doubles
from altai_api.db.instance_data import InstanceData
from tests.mocked import MockedTestCase, mock_client_set

from novaclient.v1_1.servers import REBOOT_SOFT, REBOOT_HARD
from openstackclient_base import exceptions as osc_exc
from werkzeug.exceptions import NotFound

from altai_api.blueprints import instances


class InstanceFromNovaTestCase(MockedTestCase):
    maxDiff = None

    def setUp(self):
        super(InstanceFromNovaTestCase, self).setUp()

        self.mox.StubOutWithMock(instances, 'InstanceDataDAO')
        self.instance = doubles.make(
            self.mox, doubles.Server,
            id=u'VMID',
            name=u'test instance',
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
        self.tenant = doubles.make(self.mox, doubles.Tenant,
                              name=u'test project', id=u'TENANT')
        self.flavor = doubles.make(self.mox, doubles.Flavor,
                              name=u'test instance type', id=u'1')
        self.user = doubles.make(self.mox, doubles.User,
                            name=u'test user', id=u'UID')
        self.image = doubles.make(self.mox, doubles.Image,
                             name=u'test image', id=u'IMAGE')
        self.instancedata = InstanceData(instance_id=u'VMID',
                        expires_at=datetime(2012, 12, 11, 10, 9, 8),
                        remind_at=datetime(2012, 12, 10, 8, 6, 4))

    def test_instance_from_nova_works(self):
        expected = {
            u'id': u'VMID',
            u'href': '/v1/instances/VMID',
            u'name': u'test instance',
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
            u'expires-at': datetime(2012, 12, 11, 10, 9, 8),
            u'remind-at': datetime(2012, 12, 10, 8, 6, 4),
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
            u'links': {
                u'console-output': '/v1/instances/VMID/console-output',
                u'reboot': '/v1/instances/VMID/reboot',
                u'remove': '/v1/instances/VMID/remove',
                u'reset': '/v1/instances/VMID/reset',
                u'vnc': '/v1/instances/VMID/vnc',
                u'fw-rules': '/v1/instances/VMID/fw-rule-sets/',
            },
        }

        # ACTION
        client = self.fake_client_set
        client.identity_admin.tenants.get(u'TENANT').AndReturn(self.tenant)
        client.compute.flavors.get(u'1').AndReturn(self.flavor)
        client.identity_admin.users.get(u'UID').AndReturn(self.user)
        client.image.images.get(u'IMAGE').AndReturn(self.image)
        instances.InstanceDataDAO.get(u'VMID').AndReturn(self.instancedata)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = instances._instance_from_nova(self.instance)
        self.assertEquals(result, expected)

    def test_instance_from_nova_no_tenant(self):
        expected_project = {
            'id': 'TENANT',
            'href': '/v1/projects/%s' % 'TENANT',
            'name': None
        }
        # ACTION
        client = self.fake_client_set
        client.identity_admin.tenants.get(u'TENANT')\
                .AndRaise(osc_exc.NotFound('deleted'))
        client.compute.flavors.get(u'1').AndReturn(self.flavor)
        client.identity_admin.users.get(u'UID').AndReturn(self.user)
        client.image.images.get(u'IMAGE').AndReturn(self.image)
        instances.InstanceDataDAO.get(u'VMID').AndReturn(self.instancedata)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = instances._instance_from_nova(self.instance)
        self.assertEquals(result['project'], expected_project)

    def test_instance_from_nova_no_user(self):
        expected_user = {
            'id': 'UID',
            'href': '/v1/users/%s' % 'UID',
            'name': None
        }
        # ACTION
        client = self.fake_client_set
        client.identity_admin.tenants.get(u'TENANT').AndReturn(self.tenant)
        client.compute.flavors.get(u'1').AndReturn(self.flavor)
        client.identity_admin.users.get(u'UID') \
                .AndRaise(osc_exc.NotFound('gone'))
        client.image.images.get(u'IMAGE').AndReturn(self.image)
        instances.InstanceDataDAO.get(u'VMID').AndReturn(self.instancedata)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = instances._instance_from_nova(self.instance)
        self.assertEquals(result['created-by'], expected_user)


class InstancesListTestCase(MockedTestCase):

    def setUp(self):
        super(InstancesListTestCase, self).setUp()
        self.mox.StubOutWithMock(instances, '_instance_from_nova')
        self.mox.StubOutWithMock(instances, '_servers_for_user')
        self.mox.StubOutWithMock(instances, 'fetch_instance')

    def test_list_instances_works(self):
        self.fake_client_set.compute.servers\
                .list(search_opts={'all_tenants': 1})\
                .AndReturn([u'VM1', u'VM2'])
        instances._instance_from_nova(u'VM1').AndReturn(u'R1')
        instances._instance_from_nova(u'VM2').AndReturn(u'R2')

        expected = {
            u'collection': {
                u'name': u'instances',
                u'size': 2
            },
            u'instances': [ u'R1', u'R2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/instances/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_list_instances_my_projects(self):
        instances._servers_for_user() \
                .AndReturn([u'VM1', u'VM2'])
        instances._instance_from_nova(u'VM1').AndReturn(u'R1')
        instances._instance_from_nova(u'VM2').AndReturn(u'R2')

        expected = {
            u'collection': {
                u'name': u'instances',
                u'size': 2
            },
            u'instances': [ u'R1', u'R2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/instances/?my-projects=true')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_instance_works(self):
        instances.fetch_instance(u'VMID').AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/instances/VMID')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')


class UserInstanceTestCase(MockedTestCase):
    IS_ADMIN = False

    def test_fetch_instance_as_user(self):
        self.mox.StubOutWithMock(instances, 'admin_client_set')
        self.mox.StubOutWithMock(instances, 'assert_admin_or_project_user')
        instance = doubles.make(self.mox, doubles.Server,
                          id='VMID', tenant_id='PID', name='test')

        tcs = self._fake_client_set_factory()
        instances.admin_client_set().AndReturn(tcs)
        tcs.compute.servers.get('VMID').AndReturn(instance)
        instances.assert_admin_or_project_user('PID', eperm_status=404)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = instances.fetch_instance('VMID')
        self.assertEquals(result, instance)

    def test_fetch_instance_as_non_permitted_user(self):
        self.mox.StubOutWithMock(instances, 'admin_client_set')
        self.mox.StubOutWithMock(instances, 'assert_admin_or_project_user')
        instance = doubles.make(self.mox, doubles.Server,
                          id='VMID', tenant_id='PID', name='test')

        tcs = self._fake_client_set_factory()
        instances.admin_client_set().AndReturn(tcs)
        tcs.compute.servers.get('VMID').AndReturn(instance)
        instances.assert_admin_or_project_user('PID', eperm_status=404) \
                .AndRaise(NotFound)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(404, instances.fetch_instance, 'VMID')


class ServersForUserTestCase(MockedTestCase):

    def test_servers_for_user_work(self):
        self.mox.StubOutWithMock(instances, 'client_set_for_tenant')
        tenants = [doubles.make(self.mox, doubles.Tenant, id='P1'),
                   doubles.make(self.mox, doubles.Tenant, id='P3')]
        tcs = self._fake_client_set_factory()

        self.fake_client_set.identity_public.tenants.list() \
                .AndReturn(tenants)
        instances.client_set_for_tenant('P1').AndReturn(tcs)
        tcs.compute.servers.list().AndReturn(['V1', 'V2', 'V3'])

        self.mox.ReplayAll()
        with self.app.test_request_context('/v1/instances?my-projects=true'
                                           '&project:in=P1|P2'):
            self.install_fake_auth()
            instances.parse_collection_request(instances._SCHEMA.sortby)
            result = instances._servers_for_user()
        self.assertEquals(result, ['V1', 'V2', 'V3'])

    def test_servers_for_user_none(self):
        self.mox.StubOutWithMock(instances, 'client_set_for_tenant')
        tenants = [doubles.make(self.mox, doubles.Tenant, id='P2'),
                   doubles.make(self.mox, doubles.Tenant, id='P3')]
        self.fake_client_set.identity_public.tenants.list() \
                .AndReturn(tenants)
        self.mox.ReplayAll()
        with self.app.test_request_context('/v1/instances?my-projects=true'
                                           '&project:eq=P1'):
            self.install_fake_auth()
            instances.parse_collection_request(instances._SCHEMA.sortby)
            result = instances._servers_for_user()
        self.assertEquals(result, [])


class CreateTestCase(MockedTestCase):

    def setUp(self):
        super(CreateTestCase, self).setUp()
        self.mox.StubOutWithMock(instances, '_instance_from_nova')
        self.mox.StubOutWithMock(instances, 'client_set_for_tenant')
        self.mox.StubOutWithMock(instances, 'InstanceDataDAO')
        self.tcs = mock_client_set(self.mox)

    def interact(self, data, expected_status_code=200):
        rv = self.client.post('/v1/instances/',
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_create(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
        }
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=None,
            admin_pass=None
        ).AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_expires(self):
        server = doubles.make(self.mox, doubles.Server,
                              id=u'VMID', name=u'name')
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
            u'expires-at': u'2013-01-17T15:36:00Z'
        }
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=None,
            admin_pass=None
        ).AndReturn(server)
        instances.InstanceDataDAO.create(u'VMID',
                             expires_at=datetime(2013, 1, 17, 15, 36, 0),
                             remind_at=None)
        instances._instance_from_nova(server).AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_password(self):
        params = {
            u'project': u'PID',
            u'name': u'name',
            u'image': u'image',
            u'instance-type': u'flavor',
            u'admin-pass': u'p@ssw0rd'
        }
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=None,
            admin_pass=u'p@ssw0rd'
        ).AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

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
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
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
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.servers.create(
            name=u'name',
            image=u'image',
            flavor=u'flavor',
            security_groups=None,
            key_name=u'thisiskey',
            admin_pass=None
        ).AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

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
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
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
        instances._instance_from_nova('VM1').AndReturn('REPLY')

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
        instances.client_set_for_tenant(u'PID').AndReturn(self.tcs)
        self.tcs.compute.security_groups.get(u'3')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        data = self.interact(params, expected_status_code=400)
        self.assertEquals(u'3', data.get('element-value'))
        self.assertEquals(u'fw-rule-sets', data.get('element-name'))


class UpdateTestCase(MockedTestCase):
    instance_id = u'VMID'

    def setUp(self):
        super(UpdateTestCase, self).setUp()
        self.mox.StubOutWithMock(instances, '_instance_from_nova')
        self.mox.StubOutWithMock(instances, 'InstanceDataDAO')
        self.mox.StubOutWithMock(instances, 'fetch_instance')
        self.server = doubles.make(self.mox, doubles.Server,
                                   id=self.instance_id, name=u'VICTIM VM')

    def interact(self, data, expected_status_code=200):
        rv = self.client.put('/v1/instances/%s' % self.instance_id,
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_rename_works(self):
        params = { 'name': u'new name' }

        instances.fetch_instance(self.instance_id).AndReturn(self.server)
        self.server.update(name=u'new name')
        instances.fetch_instance(self.instance_id).AndReturn('VM')
        instances._instance_from_nova('VM').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_rename_not_found(self):
        params = { 'name': u'new name' }

        instances.fetch_instance(self.instance_id).AndReturn(self.server)
        self.server.update(name=u'new name') \
                .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        self.interact(params, expected_status_code=404)

    def test_update_empty(self):
        params = {}

        instances.fetch_instance(self.instance_id).AndReturn('VM')
        instances._instance_from_nova('VM').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_rename_extra(self):
        params = {
            'name': 'new name',
            'test-parameter': u'catch me'
        }
        self.mox.ReplayAll()
        data = self.interact(params, expected_status_code=400)
        self.assertEquals('test-parameter', data.get('element-name'))

    def test_update_expires(self):
        params = {
            'expires-at': u'2013-02-17T15:36:00Z'
        }
        server = doubles.make(self.mox, doubles.Server, id='VMID')

        instances.fetch_instance(self.instance_id).AndReturn(server)
        instances.InstanceDataDAO.update('VMID',
                             expires_at=datetime(2013, 2, 17, 15, 36, 0))
        instances._instance_from_nova(server).AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_update_never_expires_and_remind(self):
        params = {
            'expires-at': None,
            'remind-at': None
        }
        server = doubles.make(self.mox, doubles.Server, id='VMID')

        instances.fetch_instance(self.instance_id).AndReturn(server)
        instances.InstanceDataDAO.update('VMID', expires_at=None,
                                         remind_at=None)
        instances._instance_from_nova(server).AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_update_remind(self):
        params = {
            'remind-at': u'2013-02-17T15:36:00Z'
        }
        server = doubles.make(self.mox, doubles.Server, id='VMID')

        instances.fetch_instance(self.instance_id).AndReturn(server)
        instances.InstanceDataDAO.update('VMID',
                             remind_at=datetime(2013, 2, 17, 15, 36, 0))
        instances._instance_from_nova(server).AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')


class ActionsTestCase(MockedTestCase):

    def setUp(self):
        super(ActionsTestCase, self).setUp()
        self.server = doubles.make(self.mox, doubles.Server,
                                   id=u'VICTIM', name=u'VICTIM VM')
        self.mox.StubOutWithMock(instances, '_instance_from_nova')
        self.mox.StubOutWithMock(instances, 'InstanceDataDAO')
        self.mox.StubOutWithMock(instances, 'fetch_instance')

    def interact(self, url, data, expected_status_code=200):
        rv = self.client.post(url,
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_reboot_works(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.reboot(REBOOT_SOFT)
        instances.fetch_instance(s.id).AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/reboot' % s.id, {})
        self.assertEquals(data, 'REPLY')

    def test_reboot_not_found(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.reboot(REBOOT_SOFT).AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/reboot' % s.id,
                      {}, expected_status_code=404)

    def test_reboot_instance_checks_input(self):
        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/reboot' % self.server.id,
                             {'role': 'victim'},
                             expected_status_code=400)
        self.assertEquals('role', data.get('element-name'))

    # NOTE(imelnikov): reset is almost the same as reboot, so
    #  there is no need to repeat all that tests once again
    def test_reset_works(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.reboot(REBOOT_HARD)
        instances.fetch_instance(s.id).AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/reset' % s.id, {})
        self.assertEquals(data, 'REPLY')

    def test_remove_instance_works(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.delete()
        instances.InstanceDataDAO.delete(s.id)
        instances.fetch_instance(s.id).AndReturn('VM1')
        instances._instance_from_nova('VM1').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/remove' % s.id, {})
        self.assertEquals(data, 'REPLY')

    def test_remove_instance_fast(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.delete()
        instances.InstanceDataDAO.delete(s.id)
        instances.fetch_instance(s.id)\
                .AndRaise(NotFound())

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/remove' % s.id, {},
                      expected_status_code=204)

    def test_remove_instance_not_found(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.delete().AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/remove' % s.id, {},
                      expected_status_code=404)

    def test_remove_instance_checks_input(self):
        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/remove' % self.server.id,
                             {'role': 'victim'},
                             expected_status_code=400)
        self.assertEquals('role', data.get('element-name'))

    def test_delete_instance_works(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.delete()
        instances.InstanceDataDAO.delete(s.id)
        instances.fetch_instance(s.id).AndRaise(NotFound())

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/instances/%s' % s.id)
        self.check_and_parse_response(rv, status_code=204)

    def test_delete_instance_pretends_waiting(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.delete()
        instances.InstanceDataDAO.delete(s.id)
        instances.fetch_instance(s.id).AndReturn(s)

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/instances/%s' % s.id)
        self.check_and_parse_response(rv, status_code=202)

    def test_console_output_works(self):
        s = self.server
        expected = {
            'instance': {
                'id': s.id,
                'name': s.name,
                'href': '/v1/instances/%s' % s.id
            },
            'console-output': 'CONSOLE LOG'
        }

        instances.fetch_instance(s.id).AndReturn(s)
        s.get_console_output(length=None).AndReturn('CONSOLE LOG')

        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/console-output' % s.id, {})
        self.assertEquals(expected, data)

    def test_console_output_length(self):
        s = self.server
        expected = {
            'instance': {
                'id': s.id,
                'name': s.name,
                'href': '/v1/instances/%s' % s.id
            },
            'console-output': 'CONSOLE LOG'
        }
        length = 42

        instances.fetch_instance(s.id).AndReturn(s)
        s.get_console_output(length=length).AndReturn('CONSOLE LOG')

        self.mox.ReplayAll()
        url = '/v1/instances/%s/console-output?length=%s' % (s.id, length)
        data = self.interact(url, {})
        self.assertEquals(expected, data)

    def test_console_output_not_found(self):
        s = self.server
        instances.fetch_instance(s.id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/console-output' % s.id, {},
                      expected_status_code=404)

    def test_console_output_late_not_found(self):
        s = self.server

        instances.fetch_instance(s.id).AndReturn(s)
        s.get_console_output(length=None) \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/console-output' % s.id, {},
                      expected_status_code=404)

    def test_vnc_works(self):
        s = self.server
        expected = {
            'instance': {
                'id': s.id,
                'name': s.name,
                'href': '/v1/instances/%s' % s.id
            },
            'url': 'CONSOLE URL',
            'console-type': 'novnc'
        }
        console = {
            'url': 'CONSOLE URL',
            'type': 'novnc'
        }

        instances.fetch_instance(s.id).AndReturn(s)
        s.get_vnc_console(console_type='novnc')\
                .AndReturn({'console': console})

        self.mox.ReplayAll()
        data = self.interact('/v1/instances/%s/vnc' % s.id, {})
        self.assertEquals(expected, data)

    def test_vnc_not_found(self):
        s = self.server
        instances.fetch_instance(s.id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/vnc' % s.id, {},
                      expected_status_code=404)

    def test_vnc_late_not_found(self):
        s = self.server
        instances.fetch_instance(s.id).AndReturn(s)
        s.get_vnc_console(console_type='novnc')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact('/v1/instances/%s/vnc' % s.id, {},
                      expected_status_code=404)

