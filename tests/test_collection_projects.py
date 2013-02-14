
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

from altai_api.blueprints import projects


class ConvertersTestCase(MockedTestCase):

    def test_project_from_nova_works(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
            id=u'c4fc65e', name=u'Project X')
        net = doubles.make(self.mox, doubles.Network,
                           label=u'net22', id=u'2699a5')
        quotaset = doubles.make(self.mox, doubles.QuotaSet)

        gb = 1024 * 1024 * 1024
        expected = {
            u'id': u'c4fc65e',
            u'href': u'/v1/projects/c4fc65e',
            u'name': u'Project X',
            u'description': u'Rather long description.',
            u'cpus-limit': 33,
            u'ram-limit': 50 * gb,
            u'storage-limit': 1000 * gb,
            u'vms-limit': 10,
            u'stats-href': u'/v1/projects/c4fc65e/stats',
            u'network': {
                u'id': u'2699a5',
                u'name': u'net22',
                u'href': u'/v1/networks/2699a5'
            }
        }

        with self.app.test_request_context():
            result = projects._project_from_nova(tenant, net, quotaset)
        self.assertEquals(expected, result)

    def test_project_from_nova_no_network(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
            id=u'c4fc65e', name=u'Project X')
        quotaset = doubles.make(self.mox, doubles.QuotaSet)

        gb = 1024 * 1024 * 1024
        expected = {
            u'id': u'c4fc65e',
            u'href': u'/v1/projects/c4fc65e',
            u'name': u'Project X',
            u'description': u'Rather long description.',
            u'cpus-limit': 33,
            u'ram-limit': 50 * gb,
            u'storage-limit': 1000 * gb,
            u'vms-limit': 10,
            u'stats-href': u'/v1/projects/c4fc65e/stats',
            'network': None
        }

        with self.app.test_request_context():
            result = projects._project_from_nova(tenant, None, quotaset)
        self.assertEquals(expected, result)

    def test_project_from_nova_no_quota(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
            id=u'c4fc65e', name=u'Project X')
        net = doubles.make(self.mox, doubles.Network,
                           label=u'net22', id=u'2699a5')

        expected = {
            u'id': u'c4fc65e',
            u'href': u'/v1/projects/c4fc65e',
            u'name': u'Project X',
            u'description': u'Rather long description.',
            u'stats-href': u'/v1/projects/c4fc65e/stats',
            u'network': {
                u'id': u'2699a5',
                u'name': u'net22',
                u'href': u'/v1/networks/2699a5'
            }
        }

        with self.app.test_request_context():
            result = projects._project_from_nova(tenant, net, None)
        self.assertEquals(expected, result)


class ProjectsHelpersTestCase(MockedTestCase):

    def test_network_for_project(self):
        def net(**kwargs):
            return doubles.make(self.mox, doubles.Network, **kwargs)

        nets = (net(label=u'net1', id=u'netid1', project_id=u'pid1'),
                net(label=u'net2', id=u'netid2', project_id=u'pid2'),
                net(label=u'net3', id=u'netid3', project_id=u'pid3'))

        self.fake_client_set.compute.networks.list().AndReturn(nets)
        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.install_fake_auth()
            result = projects._network_for_project(u'pid2')
        self.assertEquals(result, nets[1])

    def test_no_network_for_project(self):
        self.fake_client_set.compute.networks.list().AndReturn([])
        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.install_fake_auth()
            result = projects._network_for_project(u'pid2')
        self.assertEquals(result, None)

    def test_quotaset_for_project(self):
        project_id = 'PID'
        self.fake_client_set.compute.quotas.get(project_id).AndReturn('QUOTA')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            quota = projects._quotaset_for_project(project_id)
        self.assertEquals('QUOTA', quota)

    def test_project_has_servers(self):
        self.fake_client_set.compute.servers.list(
            detailed=False,
            search_opts=dict(all_tenants=1,
                             tenant_id='PID',
                             limit=1)) \
                .AndReturn(['SERVER'])
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertTrue(projects._project_has_servers('PID'))


class UserProjectsTestCase(MockedTestCase):
    IS_ADMIN = False

    def net(self, **kwargs):
        return doubles.make(self.mox, doubles.Network, **kwargs)

    def setUp(self):
        super(UserProjectsTestCase, self).setUp()
        self.nm_mock = self.fake_client_set.compute.networks
        self.tm_mock = self.fake_client_set.identity_public.tenants

        self.mox.StubOutWithMock(projects, '_quotaset_for_project')
        self.mox.StubOutWithMock(projects, '_project_from_nova')
        self.mox.StubOutWithMock(projects, '_network_for_project')

    def test_get_project(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
                              name=u'name', id=u'pid')

        self.tm_mock.find(id=u'pid').AndReturn(tenant)
        projects._quotaset_for_project(u'pid').AndReturn('QUOTA')
        projects._network_for_project(u'pid').AndReturn('FAKE_NETWORK')
        projects._project_from_nova(tenant, 'FAKE_NETWORK', 'QUOTA') \
                .AndReturn('FAKE_PROJECT')

        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'FAKE_PROJECT')

    def test_project_not_found(self):
        self.tm_mock.find(id=u'pid').AndRaise(osc_exc.NotFound("test message"))
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid')
        self.check_and_parse_response(rv, status_code=404)

    def test_systenant_not_found(self):
        systenant = doubles.make(self.mox, doubles.Tenant,
                                 name=u'systenant', id=u'PID')
        self.tm_mock.find(id=systenant.id).AndReturn(systenant)
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/%s' % systenant.id)
        self.check_and_parse_response(rv, status_code=404)

    def test_get_all_projects(self):
        tenants = (
            doubles.make(self.mox, doubles.Tenant, name=u'tnt1', id=u't1'),
            doubles.make(self.mox, doubles.Tenant, name=u'tnt2', id=u't2'),
            doubles.make(self.mox, doubles.Tenant,
                         name=u'systenant', id=u'SYSTENANT_ID'))
        nets = (
            self.net(label=u'net2', id=u'netid2', project_id=u't2'),
            self.net(label=u'net_', id=u'netid_', project_id=None),  # unused
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


class ProjectsTestCase(MockedTestCase):

    def net(self, **kwargs):
        return doubles.make(self.mox, doubles.Network, **kwargs)

    def setUp(self):
        super(ProjectsTestCase, self).setUp()
        self.nm_mock = self.fake_client_set.compute.networks
        self.tm_mock = self.fake_client_set.identity_admin.tenants

        self.mox.StubOutWithMock(projects, '_quotaset_for_project')
        self.mox.StubOutWithMock(projects, '_project_from_nova')
        self.mox.StubOutWithMock(projects, '_network_for_project')

    def test_get_project(self):

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
        self.check_and_parse_response(rv, status_code=404)

    def test_systenant_not_found(self):
        systenant = doubles.make(self.mox, doubles.Tenant,
                                 name=u'systenant', id=u'PID')
        self.tm_mock.get(systenant.id).AndReturn(systenant)
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/%s' % systenant.id)
        self.check_and_parse_response(rv, status_code=404)

    def test_get_all_projects(self):
        tenants = (
            doubles.make(self.mox, doubles.Tenant, name=u'tnt1', id=u't1'),
            doubles.make(self.mox, doubles.Tenant, name=u'tnt2', id=u't2'),
            doubles.make(self.mox, doubles.Tenant,
                         name=u'systenant', id=u'SYSTENANT_ID'))
        nets = (
            self.net(label=u'net2', id=u'netid2', project_id=u't2'),
            self.net(label=u'net_', id=u'netid_', project_id=None),  # unused
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


class ProjectStatsTestCase(MockedTestCase):

    def test_stats_work(self):
        tcs = mock_client_set(self.mox)
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=u'pid', name=u'test project')
        self.mox.StubOutWithMock(projects, 'client_set_for_tenant')

        self.fake_client_set.identity_admin.tenants.get(u'pid') \
                .AndReturn(tenant)
        self.fake_client_set.identity_admin.tenants.list_users(u'pid') \
                .AndReturn(range(42))
        projects.client_set_for_tenant(u'pid', fallback_to_api=True) \
                .AndReturn(tcs)
        tcs.compute.servers.list().AndReturn(range(3))
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

    def test_stats_not_found(self):
        self.fake_client_set.identity_admin.tenants.get(u'pid') \
                .AndRaise(osc_exc.NotFound("test message"))
        self.mox.ReplayAll()

        rv = self.client.get('/v1/projects/pid/stats')
        self.check_and_parse_response(rv, 404)


class CreateProjectTestCase(MockedTestCase):

    name, description, net_id = 'ptest', 'DESCRIPTION', 'NETID'

    def interact(self, data=None, expected_status_code=200):
        if data is None:
            data = {
                'name': self.name,
                'description': self.description,
                'network': self.net_id
            }
        rv = self.client.post('/v1/projects/',
                              data=json.dumps(data),
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

    def test_project_creation_checks_name_required(self):
        self.mox.ReplayAll()
        data = self.interact(data={'network': self.net_id},
                             expected_status_code=400)
        self.assertEquals(data.get('element-name'), 'name')

    def test_project_creation_checks_name_is_string(self):
        self.mox.ReplayAll()
        data = {
            'name': 42,
            'network': self.net_id
        }
        data = self.interact(data=data, expected_status_code=400)
        self.assertEquals(data.get('element-name'), 'name')

    def test_project_creation_checks_network_required(self):
        self.mox.ReplayAll()
        data = self.interact(data={'name': self.name},
                             expected_status_code=400)
        self.assertEquals(data.get('element-name'), 'network')

    def test_project_creation_checks_network_exists(self):
        self.fake_client_set.compute.networks.get(self.net_id)\
                .AndRaise(osc_exc.NotFound('network'))

        self.mox.ReplayAll()
        data = self.interact(expected_status_code=400)
        self.assertEquals(data.get('element-name'), 'network')

    def test_project_creation_checks_network_unused(self):
        network = doubles.make(self.mox, doubles.Network,
                               label='LABEL', id=self.net_id,
                               project_id='42')
        self.fake_client_set.compute.networks.get(self.net_id)\
                .AndReturn(network)

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

    def setUp(self):
        super(DeleteProjectTestCase, self).setUp()
        self.tenant_id = u'PID'
        self.tenant = doubles.make(self.mox, doubles.Tenant,
                                   id=self.tenant_id)
        self.mox.StubOutWithMock(projects, '_project_has_servers')

    def interact(self, expected_status_code):
        rv = self.client.delete('/v1/projects/%s' % self.tenant_id)
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_project_deletion_checks_existence(self):
        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=404)

    def test_project_deletion_works(self):

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(self.tenant)
        projects._project_has_servers(self.tenant_id).AndReturn(False)
        self.fake_client_set.compute.networks.list().AndReturn([])

        self.tenant.delete()

        self.mox.ReplayAll()
        self.interact(expected_status_code=204)

    def test_project_deletion_late_not_found(self):
        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(self.tenant)
        projects._project_has_servers(self.tenant_id).AndReturn(False)
        self.fake_client_set.compute.networks.list().AndReturn([])

        self.tenant.delete().AndRaise(osc_exc.NotFound('deleted'))

        self.mox.ReplayAll()
        self.interact(expected_status_code=204)

    def test_project_deletion_with_servers_fails(self):
        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(self.tenant)
        projects._project_has_servers(self.tenant_id).AndReturn(True)

        self.mox.ReplayAll()
        data = self.interact(expected_status_code=400)
        self.assertTrue('VMs' in data['message'])

    def test_project_deletion_with_networks(self):
        def _net(**kwargs):
            return doubles.make(self.mox, doubles.Network, **kwargs)

        nets = [_net(id='n1', project_id=self.tenant_id),
                _net(id='n2', project_id=u'other'),
                _net(id='n3', project_id=self.tenant_id)]

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(self.tenant)
        projects._project_has_servers(self.tenant_id).AndReturn(False)

        self.fake_client_set.compute.networks.list().AndReturn(nets)
        self.fake_client_set.compute.networks.disassociate(nets[0])
        self.fake_client_set.compute.networks.disassociate(nets[2])

        self.tenant.delete()

        self.mox.ReplayAll()
        self.interact(expected_status_code=204)


class UpdateProjectTestCase(MockedTestCase):
    tenant_id = u'PID'

    def setUp(self):
        super(UpdateProjectTestCase, self).setUp()

        self.mox.StubOutWithMock(projects, '_network_for_project')
        self.mox.StubOutWithMock(projects, '_quotaset_for_project')
        self.mox.StubOutWithMock(projects, '_project_from_nova')

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
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=self.tenant_id, name='old name',
                              description='old description')

        updated = doubles.make(self.mox, doubles.Tenant,
                               id=self.tenant_id, name='old name',
                               description='new description')

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(tenant)
        tenant.update(description=updated.description).AndReturn(updated)
        projects._network_for_project(self.tenant_id).AndReturn('NET')
        projects._quotaset_for_project(self.tenant_id).AndReturn('QUOTA')
        projects._project_from_nova(updated, 'NET', 'QUOTA')\
                .AndReturn('UPDATED')

        self.mox.ReplayAll()
        data = self.interact({'description': updated.description})
        self.assertEquals(data, 'UPDATED')

    def test_update_project_late_not_found(self):
        description = 'new description'
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=self.tenant_id, name='old name',
                              description='old description')

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(tenant)
        tenant.update(description=description) \
                .AndRaise(osc_exc.NotFound('deleted'))

        self.mox.ReplayAll()
        self.interact({'description': description},
                      expected_status_code=404)

    def test_update_project_limits(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=self.tenant_id, name='old name',
                              description='old description')
        gb = 1024 * 1024 * 1024
        params = {
            u'cpus-limit': 13,
            u'ram-limit': 11 * gb,
            u'storage-limit': 1000 * gb,
            u'vms-limit': 8
        }

        self.fake_client_set.identity_admin \
            .tenants.get(self.tenant_id).AndReturn(tenant)
        self.fake_client_set.compute.quotas.update(self.tenant_id,
            instances=8, ram=11 * 1024, gigabytes=1000, cores=13)

        projects._network_for_project(self.tenant_id).AndReturn('NET')
        projects._quotaset_for_project(self.tenant_id).AndReturn('QUOTA')
        projects._project_from_nova(tenant, 'NET', 'QUOTA')\
                .AndReturn('UPDATED')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'UPDATED')

