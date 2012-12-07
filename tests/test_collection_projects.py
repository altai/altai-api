
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

from flask import json
import openstackclient_base.exceptions as osc_exc

from tests import doubles
from tests.mocked import mock_client_set, MockedTestCase

from altai_api.collection import projects

class ConvertersTestCase(MockedTestCase):

    def test_project_from_nova_works(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
            id=u'c4fc65e395e8408b97f6c1a27da95c43', name=u'Project X')
        net = doubles.make(self.mox, doubles.Network,
                           label=u'net22', id=u'2699a5')
        quotaset = doubles.make(self.mox, doubles.QuotaSet)

        gb = 1024 * 1024 * 1024
        expected = {
            u'id': u'c4fc65e395e8408b97f6c1a27da95c43',
            u'href': u'/v1/projects/c4fc65e395e8408b97f6c1a27da95c43',
            u'name': u'Project X',
            u'description': u'Rather long description.',
            u'cpus-limit': 33,
            u'ram-limit': 50 * gb,
            u'storage-limit': 1000 * gb,
            u'stats-href': u'/v1/projects/c4fc65e395e8408b97f6c1a27da95c43/stats',
            u'network': {
                u'id': u'2699a5',
                u'name':  u'net22',
                u'href': u'/v1/networks/2699a5'
            }
        }

        with self.app.test_request_context():
            result = projects._project_from_nova(tenant, net, quotaset)
        self.assertEquals(expected, result)

    def test_project_from_nova_no_network(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
            id=u'c4fc65e395e8408b97f6c1a27da95c43', name=u'Project X')
        quotaset = doubles.make(self.mox, doubles.QuotaSet)

        gb = 1024 * 1024 * 1024
        expected = {
            u'id': u'c4fc65e395e8408b97f6c1a27da95c43',
            u'href': u'/v1/projects/c4fc65e395e8408b97f6c1a27da95c43',
            u'name': u'Project X',
            u'description': u'Rather long description.',
            u'cpus-limit': 33,
            u'ram-limit': 50 * gb,
            u'storage-limit': 1000 * gb,
            u'stats-href': u'/v1/projects/c4fc65e395e8408b97f6c1a27da95c43/stats',
            'network': None
        }

        with self.app.test_request_context():
            result = projects._project_from_nova(tenant, None, quotaset)
        self.assertEquals(expected, result)

    def test_project_from_nova_no_quota(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
            id=u'c4fc65e395e8408b97f6c1a27da95c43', name=u'Project X')
        net = doubles.make(self.mox, doubles.Network,
                           label=u'net22', id=u'2699a5')

        expected = {
            u'id': u'c4fc65e395e8408b97f6c1a27da95c43',
            u'href': u'/v1/projects/c4fc65e395e8408b97f6c1a27da95c43',
            u'name': u'Project X',
            u'description': u'Rather long description.',
            u'stats-href': u'/v1/projects/c4fc65e395e8408b97f6c1a27da95c43/stats',
            u'network': {
                u'id': u'2699a5',
                u'name':  u'net22',
                u'href': u'/v1/networks/2699a5'
            }
        }

        with self.app.test_request_context():
            result = projects._project_from_nova(tenant, net, None)
        self.assertEquals(expected, result)



class ProjectsTestCase(MockedTestCase):

    def net(self, **kwargs):
        return doubles.make(self.mox, doubles.Network, **kwargs)


    def setUp(self):
        super(ProjectsTestCase, self).setUp()
        self.nm_mock = self.fake_client_set.compute.networks
        self.tm_mock = self.fake_client_set.identity_admin.tenants

        self.mox.StubOutWithMock(projects, '_quotaset_for_project')
        self.mox.StubOutWithMock(projects, '_project_from_nova')


    def test_network_for_project(self):
        nets = (self.net(label=u'net1', id=u'netid1', project_id=u'pid1'),
                self.net(label=u'net2', id=u'netid2', project_id=u'pid2'),
                self.net(label=u'net3', id=u'netid3', project_id=u'pid3'))
        self.nm_mock.list().AndReturn(nets)
        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.install_fake_auth()
            net = projects._network_for_project(u'pid2')
        self.assertEquals(net, nets[1])

    def test_get_project(self):
        self.mox.StubOutWithMock(projects, '_network_for_project')

        tenant = doubles.make(self.mox, doubles.Tenant,
                              name=u'name', id=u'pid')

        self.tm_mock.get(u'pid').AndReturn(tenant)
        projects._quotaset_for_project(u'pid').AndReturn('QUOTA')
        projects._network_for_project(u'pid').AndReturn('FAKE_NETWORK')
        projects._project_from_nova(tenant, 'FAKE_NETWORK', 'QUOTA') \
                .AndReturn('FAKE_PROJECT')

        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'FAKE_PROJECT')

    def test_project_not_found(self):
        self.tm_mock.get(u'pid').AndRaise(osc_exc.NotFound("test message"))
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid')
        data = self.check_and_parse_response(rv, status_code=404)

    def test_systenant_not_found(self):
        systenant = doubles.make(self.mox, doubles.Tenant,
                                 name=u'systenant', id=u'PID')
        self.tm_mock.get(systenant.id).AndReturn(systenant)
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/%s' % systenant.id)
        data = self.check_and_parse_response(rv, status_code=404)

    def test_get_all_projects(self):
        tenants = (
            doubles.make(self.mox, doubles.Tenant, name=u'tnt1', id=u't1'),
            doubles.make(self.mox, doubles.Tenant, name=u'tnt2', id=u't2'),
            doubles.make(self.mox, doubles.Tenant,
                         name=u'systenant', id=u'SYSTENANT_ID'))
        nets = (
            self.net(label=u'net2', id=u'netid2', project_id=u't2'),
            self.net(label=u'net_', id=u'netid_', project_id=None), # unused network
            self.net(label=u'net1', id=u'netid1', project_id=u't1'))

        self.tm_mock.list().AndReturn(tenants)
        self.nm_mock.list().AndReturn(nets)
        projects._quotaset_for_project(u't1').AndReturn('QUOTA1')
        projects._project_from_nova(tenants[0], nets[2], 'QUOTA1')\
                .AndReturn('PROJECT1')

        projects._quotaset_for_project(u't2').AndReturn('QUOTA2')
        projects._project_from_nova(tenants[1], nets[0], 'QUOTA2')\
                .AndReturn('PROJECT2')

        expected = {
            u'collection': {
                u'name': u'projects',
                u'size': 2
            },
            u'projects': [ 'PROJECT1', 'PROJECT2' ]
        }

        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_stats_not_found(self):
        self.tm_mock.get(u'pid').AndRaise(osc_exc.NotFound("test message"))
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid/stats')
        self.check_and_parse_response(rv, 404)



class ProjectStatsTestCase(MockedTestCase):

    def test_stats_work_hard(self):
        tcs = mock_client_set(self.mox)
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=u'pid', name=u'test project')
        self.mox.StubOutWithMock(projects, 'client_set_for_tenant')

        self.fake_client_set.identity_admin\
                .tenants.get(u'pid').AndReturn(tenant)
        tenant.list_users().AndReturn(range(42))
        self.fake_client_set.compute.servers.list(search_opts={
            'project_id': u'pid',
            'all_tenants': 1
        }).AndReturn(range(3))
        projects.client_set_for_tenant(tenant_id=u'pid').AndReturn(tcs)
        tcs.image.images.list().AndReturn([])

        expected = {
            u'project': {
                u'id': u'pid',
                u'href': u'/v1/projects/pid',
                u'name': u'test project'
            },
            u'members': 42,
            u'vms': 3,
            u'local-images': 0,
            u'total-images': 0
        }

        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid/stats')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)


class CreateProjectTestCase(MockedTestCase):

    name, description, net_id = 'ptest', 'DECRIPTION', 'NETID'

    def interact(self, expected_status_code=200):
        post_params = {
            'name': self.name,
            'description': self.description,
            'network': self.net_id
        }
        rv = self.client.post('/v1/projects/',
                              data=json.dumps(post_params),
                              content_type='application/json')
        # verify
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_project_creation_works(self):
        self.mox.StubOutWithMock(projects, '_project_from_nova')
        self.mox.StubOutWithMock(projects, '_quotaset_for_project')

        networks = self.fake_client_set.compute.networks
        tenants = self.fake_client_set.identity_admin.tenants
        tenant = doubles.make(self.mox, doubles.Tenant,
                              name=self.name, id='PID',
                              description=self.description)

        networks.get(self.net_id).AndReturn(
            doubles.make(self.mox, doubles.Network,
                         label='NETLABEL', id=self.net_id, project_id=None))
        tenants.create(self.name, self.description).AndReturn(tenant)
        networks.associate(self.net_id, tenant.id)

        networks.get(self.net_id).AndReturn('UPDATED NETWORK')
        projects._quotaset_for_project(tenant.id).AndReturn('QUOTA')
        projects._project_from_nova(tenant, 'UPDATED NETWORK', 'QUOTA')\
                .AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact()
        self.assertEquals(data, 'REPLY')

    def test_project_creation_checks_network_exists(self):
        name, description, net_id = 'ptest', 'DECRIPTION', 'NETID'
        self.fake_client_set.compute. \
            networks.get(net_id).AndRaise(osc_exc.NotFound('network'))

        self.mox.ReplayAll()
        data = self.interact(expected_status_code=400)
        self.assertEquals(data.get('element-name'), 'network')

    def test_project_creation_checks_network_unused(self):
        name, description, net_id = 'ptest', 'DECRIPTION', 'NETID'
        self.fake_client_set.compute. \
            networks.get(net_id).AndReturn(
                doubles.make(self.mox, doubles.Network,
                             label='LABEL', id='NETID', project_id='42'))

        self.mox.ReplayAll()
        data = self.interact(expected_status_code=400)
        self.assertEquals(data.get('element-name'), 'network')

    def test_project_creation_associate_fails(self):
        self.mox.StubOutWithMock(projects, '_project_from_nova')
        self.mox.StubOutWithMock(projects, '_quotaset_for_project')

        networks = self.fake_client_set.compute.networks
        tenants = self.fake_client_set.identity_admin.tenants
        tenant = doubles.make(self.mox, doubles.Tenant,
                              name=self.name, id='PID',
                              description=self.description)

        networks.get(self.net_id).AndReturn(
            doubles.make(self.mox, doubles.Network,
                         label='NETLABEL', id=self.net_id, project_id=None))
        tenants.create(self.name, self.description).AndReturn(tenant)
        networks.associate(self.net_id, tenant.id).AndRaise(
            osc_exc.BadRequest('failure'))
        tenant.delete()

        self.mox.ReplayAll()
        data = self.interact(expected_status_code=400)
        self.assertTrue(self.net_id in data.get('message'))


class DeleteProjectTestCase(MockedTestCase):
    tenant_id = u'PID'

    def interact(self, expected_status_code):
        rv = self.client.delete('/v1/projects/%s' % self.tenant_id)
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_project_deletion_checks_existance(self):
        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=404)

    def test_project_deletion_works(self):
        tenant = doubles.make(self.mox, doubles.Tenant, id=self.tenant_id)
        servers = [doubles.make(self.mox, doubles.Server, id=vmid)
                   for vmid in ('vm1', 'vm2', 'vm3')]
        nets = [
            doubles.make(self.mox, doubles.Network, id='n1', project_id=self.tenant_id),
            doubles.make(self.mox, doubles.Network, id='n2', project_id=u'other'),
            doubles.make(self.mox, doubles.Network, id='n3', project_id=self.tenant_id)
        ]

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(tenant)
        self.fake_client_set.compute.servers.list(search_opts={
            'project_id': tenant.id,
            'all_tenants': 1
        }).AndReturn(servers)
        servers[0].delete()
        servers[1].delete()
        servers[2].delete()

        self.fake_client_set.compute.networks.list().AndReturn(nets)
        self.fake_client_set.compute.networks.disassociate(nets[0])
        self.fake_client_set.compute.networks.disassociate(nets[2])

        tenant.delete()

        self.mox.ReplayAll()
        self.interact(expected_status_code=204)


class UpdatePojectTestCase(MockedTestCase):
    tenant_id = u'PID'

    def interact(self, put_params, expected_status_code=200):
        rv = self.client.put('/v1/projects/%s' % self.tenant_id,
                             data=json.dumps(put_params),
                             content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_update_project_not_exists(self):
        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        self.interact({}, expected_status_code=404)

    def test_update_project_updates(self):
        self.mox.StubOutWithMock(projects, '_network_for_project')
        self.mox.StubOutWithMock(projects, '_quotaset_for_project')
        self.mox.StubOutWithMock(projects, '_project_from_nova')

        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=self.tenant_id, name='old name',
                              description='old description')

        updated = doubles.make(self.mox, doubles.Tenant,
                               id=self.tenant_id, name='new name',
                               description='new description')

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(tenant)
        tenant.update(name=updated.name, description=updated.description)\
                .AndReturn(updated)
        projects._network_for_project(self.tenant_id).AndReturn('NET')
        projects._quotaset_for_project(self.tenant_id).AndReturn('QUOTA')
        projects._project_from_nova(updated, 'NET', 'QUOTA').AndReturn('UPDATED')

        self.mox.ReplayAll()
        data = self.interact({'name': updated.name,
                              'description': updated.description})
        self.assertEquals(data, 'UPDATED')
