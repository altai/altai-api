
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

from tests import doubles
from tests.mocked import MockedTestCase

from altai_api import stats


class StatsTestCase(MockedTestCase):

    def test_stats_work(self):
        self.mox.StubOutWithMock(stats, 'list_all_images')
        images = [doubles.make(self.mox, doubles.Image,
                               id=str(i), name='image%s' % i, is_public=p)
                  for i, p in enumerate((True, False, False, True, False))]

        expected = {
            'projects': 3,
            'vms': 14,
            'users': 9,
            'total-images': 5,
            'global-images': 2
        }
        tenants = ['systenant', 'tenant1', 'tenant2', 'tenant3']

        cs = self.fake_client_set
        cs.identity_admin.tenants.list().AndReturn(tenants)
        cs.identity_admin.users.list()\
                .AndReturn(['user%s' % i for i in xrange(9)])
        cs.compute.servers.list(search_opts={'all_tenants': 1})\
                .AndReturn(['vm%s' % i for i in xrange(14)])
        stats.list_all_images().AndReturn(images)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/stats')
        data = self.check_and_parse_response(rv)
        self.assertEquals(expected, data)
