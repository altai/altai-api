
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

from openstackclient_base import exceptions as osc_exc

from tests import doubles
from tests.mocked import MockedTestCase

from altai_api import auth
from altai_api.blueprints import stats


class StatsTestCase(MockedTestCase):

    def setUp(self):
        super(StatsTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, 'default_tenant_id')
        self.mox.StubOutWithMock(auth, 'client_set_for_tenant')
        self.mox.StubOutWithMock(stats, 'list_all_images')

    def test_stats_work(self):
        images = [doubles.make(self.mox, doubles.Image,
                               id=str(i), name='image%s' % i, is_public=p)
                  for i, p in enumerate((True, False, False, True, False))]

        expected = {
            'projects': 3,
            'instances': 14,
            'users': 9,
            'total-images': 5,
            'global-images': 2,
            'by-project-stats-href': u'/v1/stats/by-project/'
        }
        tenants = ['systenant', 'tenant1', 'tenant2', 'tenant3']

        cs = self.fake_client_set
        cs.identity_admin.tenants.list().AndReturn(tenants)
        cs.identity_admin.users.list()\
                .AndReturn(['user%s' % i for i in xrange(9)])
        cs.compute.servers.list(search_opts={'all_tenants': 1})\
                .AndReturn(['instance%s' % i for i in xrange(14)])
        stats.list_all_images(cs.image.images).AndReturn(images)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/stats')
        data = self.check_and_parse_response(rv)
        self.assertEquals(expected, data)

    def test_list_works(self):
        tenants = [doubles.make(self.mox, doubles.Tenant, **kwargs)
                   for kwargs in (dict(id=u'p1', name=u'test1'),
                                  dict(id=u'p2', name=u'test2'),
                                  dict(id=u'SYS', name=u'systenant'))]
        servers = [
            doubles.make(self.mox, doubles.Server, tenant_id='p2'),
            doubles.make(self.mox, doubles.Server, tenant_id='SYS'),
        ]
        images = [doubles.make(self.mox, doubles.Image, **kwargs)
                  for kwargs in (dict(id='x', is_public=True),
                                 dict(id='y', is_public=False, owner='p2'),
                                 dict(id='z', is_public=True, owner='p1'))]

        self.fake_client_set.identity_admin.tenants.list()\
                .AndReturn(tenants)
        auth.default_tenant_id().AndReturn('SYS')
        self.fake_client_set.identity_admin.tenants.list_users('p1')\
                .AndReturn([])
        auth.default_tenant_id().AndReturn('SYS')
        self.fake_client_set.identity_admin.tenants.list_users('p2')\
                .AndReturn([])
        auth.default_tenant_id().AndReturn('SYS')

        self.fake_client_set.compute.servers\
                .list(search_opts={'all_tenants': 1})\
                .AndReturn(servers)
        stats.list_all_images(self.fake_client_set.image.images)\
                .AndReturn(images)

        expected = [
            {
                'href': '/v1/stats/by-project/p1',
                'project': {
                    'href': '/v1/projects/p1',
                    'id': 'p1',
                    'name': 'test1'
                },
                'instances': 0,
                'members': 0,
                'local-images': 1,
                'total-images': 2
            },
            {
                'href': '/v1/stats/by-project/p2',
                'project': {
                    'href': '/v1/projects/p2',
                    'id': 'p2',
                    'name': 'test2'
                },
                'instances': 1,
                'members': 0,
                'local-images': 1,
                'total-images': 3
            },
        ]

        self.mox.ReplayAll()
        rv = self.client.get('/v1/stats/by-project/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data['stats'], expected)

    def test_list_for_pure_user(self):
        self.fake_client_set.identity_public.tenants.list()\
                .AndReturn([])
        self.fake_client_set.compute.servers\
                .list(search_opts={'all_tenants': 1})\
                .AndReturn([])
        stats.list_all_images(self.fake_client_set.image.images)\
                .AndReturn([])
        self.mox.ReplayAll()
        expected = {
            'collection': {
                'name': 'stats',
                'size': 0,
                'parent-href': '/v1/stats'
            },
            'stats': []
        }
        rv = self.client.get('/v1/stats/by-project/?my-projects=True')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_project_stats_work(self):
        tcs = self._fake_client_set_factory()
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=u'pid', name=u'test project')
        self.fake_client_set.identity_admin.tenants.get(u'pid') \
                .AndReturn(tenant)
        self.fake_client_set.identity_admin.tenants.list_users(u'pid') \
                .AndReturn(range(42))
        auth.client_set_for_tenant(u'pid', fallback_to_api=True) \
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
            u'instances': 3,
            u'local-images': 0,
            u'total-images': 0,
            u'href': u'/v1/stats/by-project/pid'
        }

        self.mox.ReplayAll()

        rv = self.client.get('/v1/stats/by-project/pid')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_stats_not_found(self):
        self.fake_client_set.identity_admin.tenants.get(u'pid') \
                .AndRaise(osc_exc.NotFound("test message"))
        self.mox.ReplayAll()

        rv = self.client.get('/v1/stats/by-project/pid')
        self.check_and_parse_response(rv, 404)

