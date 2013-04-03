
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2013 Grid Dynamics Consulting Services, Inc
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

from openstackclient_base import exceptions as osc_exc
from altai_api.blueprints import nodes


_TEST_DATA = [
    {
        u'project': u'(total)',
        u'memory_mb': 3831,
        u'host': u'test',
        u'cpu': 2,
        u'disk_gb': 3
    },
    {
        u'project': u'(used_now)',
        u'memory_mb': 1156,
        u'host': u'test',
        u'cpu': 5,
        u'disk_gb': 2
    },
    {
        u'project': u'(used_max)',
        u'memory_mb': 1024,
        u'host': u'test',
        u'cpu': 5,
        u'disk_gb': 10
    },
    {
        u'project': u'a76af281cbc4491e8bdf479008edea34',
        u'memory_mb': 512,
        u'host': u'test',
        u'cpu': 1,
        u'disk_gb': 0
    },
    {
        u'project': u'ac9954f44ab44bf3abba166ac9660cb6',
        u'memory_mb': 512,
        u'host': u'test',
        u'cpu': 4,
        u'disk_gb': 10
    }
]

_MB = 1024 * 1024


class NodeToViewTestCase(MockedTestCase):

    def test_node_to_view_works(self):
        data = [doubles.make(self.mox, doubles.Host, **kwargs)
                for kwargs in _TEST_DATA]

        expected = {
            'name': 'test',
            'href': '/v1/nodes/test',
            'memory': 3831 * _MB,
            'cpus': 2,
            'memory-used': 1156 * _MB,
            'cpus-used': 5,
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            result = nodes._node_to_view('test', data)
        self.assertEquals(result, expected)

_TEST_HOSTS = [
    {u'host_name': u'master', u'service': u'network'},
    {u'host_name': u'master', u'service': u'scheduler'},
    {u'host_name': u'master', u'service': u'consoleauth'},
    {u'host_name': u'master', u'service': u'compute'},
    {u'host_name': u'slave1', u'service': u'compute'},
    {u'host_name': u'slave2', u'service': u'compute'}
]


class NodesTestCase(MockedTestCase):

    def setUp(self):
        super(NodesTestCase, self).setUp()
        self.mox.StubOutWithMock(nodes, '_node_to_view')

    def test_get_node_works(self):
        hostname = 'TEST_HOST'
        host_info = ['H1', 'H2']
        self.fake_client_set.compute.hosts.get(hostname)\
                .AndReturn(host_info)
        nodes._node_to_view(hostname, host_info)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/nodes/%s' % hostname)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_node_not_found(self):
        hostname = 'TEST_HOST'
        self.fake_client_set.compute.hosts.get(hostname)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/nodes/%s' % hostname)
        self.check_and_parse_response(rv, status_code=404)

    def test_list_nodes_work(self):
        hm = self.fake_client_set.compute.hosts
        hm.list_all().AndReturn(
                [doubles.make(self.mox, doubles.Host, _info=info)
                 for info in _TEST_HOSTS])
        hm.get('master').AndReturn('MASTER_DATA')
        nodes._node_to_view('master', 'MASTER_DATA').AndReturn('H1')
        hm.get('slave1').AndRaise(osc_exc.NotFound('gone'))
        hm.get('slave2').AndReturn('SLAVE_DATA')
        nodes._node_to_view('slave2', 'SLAVE_DATA').AndReturn('H3')

        expected = {
            'collection': {
                'name': 'nodes',
                'size': 2,
            },
            'nodes': ['H1', 'H3']
        }
        self.mox.ReplayAll()
        rv = self.client.get('/v1/nodes/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

