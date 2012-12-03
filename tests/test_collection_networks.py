
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
from openstackclient_base.nova.networks import NetworkManager
from openstackclient_base import exceptions as osc_exc

from altai_api.collection import networks

from tests.mocked import MockedTestCase

class NetworksCollectionTestCase(MockedTestCase):

    def setUp(self):
        super(NetworksCollectionTestCase, self).setUp()
        self.mox.StubOutWithMock(networks, 'net_to_dict')

    def test_list_networks_normally(self):
        self.fake_client_set.compute.networks.list() \
                .AndReturn(['net-a', 'net-b'])
        networks.net_to_dict('net-a').AndReturn('dict-a')
        networks.net_to_dict('net-b').AndReturn('dict-b')
        expected = {
            'collection': {
                'name': 'networks',
                'size': 2
            },
            'networks': [ 'dict-a', 'dict-b' ]
        }

        self.mox.ReplayAll()

        rv = self.client.get('/v1/networks/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_network(self):
        # prepare
        self.fake_client_set.compute.networks.get('net-a').AndReturn('net-a')
        networks.net_to_dict('net-a').AndReturn('dict-a')
        self.mox.ReplayAll()
        # test
        rv = self.client.get('/v1/networks/net-a')
        # verify
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'dict-a')

    def test_get_network_not_found(self):
        # prepare
        self.fake_client_set.compute.networks.get('net-a') \
            .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        # test
        rv = self.client.get('/v1/networks/net-a')
        # verify
        data = self.check_and_parse_response(rv, status_code=404)

    def test_create_network(self):
        # prepare
        (name, vlan, cidr) = ('net-name', 3301, 'ip/mask')
        self.fake_client_set.compute.networks.create(
            label=name, vlan=vlan, cidr=cidr).AndReturn('new-net')
        networks.net_to_dict('new-net').AndReturn('new-net-dict')
        self.mox.ReplayAll()
        # test
        post_params = {"name": name, "vlan": vlan, "cidr": cidr}
        rv = self.client.post('/v1/networks/',
                              data=json.dumps(post_params),
                              content_type='application/json')
        # verify
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-net-dict')

    def test_create_existing_network(self):
        (name, vlan, cidr) = ('net-name', 3301, 'ip/mask')
        self.fake_client_set.compute.networks.create(
            label=name, vlan=vlan, cidr=cidr).AndRaise(osc_exc.BadRequest('fail'))

        self.mox.ReplayAll()

        post_params = {"name": name, "vlan": vlan, "cidr": cidr}
        rv = self.client.post('/v1/networks/',
                              data=json.dumps(post_params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv, status_code=400)

    def test_delete_network(self):
        # prepare
        self.fake_client_set.compute.networks.delete('net-a')
        self.mox.ReplayAll()
        # test
        rv = self.client.delete('/v1/networks/net-a')
        # verify
        self.assertEquals(rv.status_code, 204)

    def test_delete_network_not_found(self):
        # prepare
        self.fake_client_set.compute.networks.delete('net-a')\
                .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        # test
        rv = self.client.delete('/v1/networks/net-a')
        # verify
        self.assertEquals(rv.status_code, 404)

