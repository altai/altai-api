
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
from tests.mocked import MockedTestCase

from altai_api.blueprints import my_ssh_keys

from openstackclient_base import exceptions as osc_exc


class KeypairFromNovaTestCase(MockedTestCase):

    def test_keypair_from_nova_works(self):
        kp = doubles.make(self.mox, doubles.Keypair,
                          name='Test KP', public_key='PUBKEY',
                          fingerprint='FP')
        expected = {
            'name': 'Test KP',
            'public-key': 'PUBKEY',
            'fingerprint': 'FP',
            'href': '/v1/me/ssh-keys/Test%20KP'
        }
        self.mox.ReplayAll()
        with self.app.test_request_context():
            data = my_ssh_keys.keypair_from_nova(kp)
        self.assertEquals(data, expected)


class MySShKeysListTestCase(MockedTestCase):

    def setUp(self):
        super(MySShKeysListTestCase, self).setUp()
        self.mox.StubOutWithMock(my_ssh_keys, 'keypair_from_nova')

    def test_list_works(self):
        expected = {
            'collection': {
                'name': 'ssh-keys',
                'parent-href': '/v1/me',
                'size': 2
            },
            'ssh-keys': ['REPLY1', 'REPLY2']
        }

        self.fake_client_set.compute.keypairs.list()\
                .AndReturn(['K1', 'K2'])
        my_ssh_keys.keypair_from_nova('K1').AndReturn('REPLY1')
        my_ssh_keys.keypair_from_nova('K2').AndReturn('REPLY2')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/me/ssh-keys/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_works(self):
        self.fake_client_set.compute.keypairs.find(name='kp')\
                .AndReturn('K1')
        my_ssh_keys.keypair_from_nova('K1').AndReturn('REPLY')

        self.mox.ReplayAll()

        rv = self.client.get('/v1/me/ssh-keys/kp')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_not_found(self):
        self.fake_client_set.compute.keypairs.find(name='kp')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        rv = self.client.get('/v1/me/ssh-keys/kp')
        self.check_and_parse_response(rv, status_code=404)

    def test_delete_works(self):
        self.fake_client_set.compute.keypairs.delete('kp')

        self.mox.ReplayAll()

        rv = self.client.delete('/v1/me/ssh-keys/kp')
        self.check_and_parse_response(rv, status_code=204)

    def test_delete_not_found(self):
        self.fake_client_set.compute.keypairs.delete('kp')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        rv = self.client.delete('/v1/me/ssh-keys/kp')
        self.check_and_parse_response(rv, status_code=404)


class CreateMySshKeyTestCase(MockedTestCase):

    def setUp(self):
        super(CreateMySshKeyTestCase, self).setUp()
        self.mox.StubOutWithMock(my_ssh_keys, 'keypair_from_nova')

    def interact(self, data, expected_status_code=200):
        rv = self.client.post('/v1/me/ssh-keys/',
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
                    rv, status_code=expected_status_code)

    def test_generate_pair(self):
        kp = doubles.make(self.mox, doubles.Keypair,
                          name='TestKP', public_key='PUBKEY',
                          fingerprint='FP', private_key='PRIVATE')
        self.fake_client_set.compute.keypairs.create(kp.name, None)\
                .AndReturn(kp)
        my_ssh_keys.keypair_from_nova(kp).AndReturn({'FAKE': 1})

        self.mox.ReplayAll()

        data = self.interact({'name': kp.name})
        self.assertEquals(data, {'FAKE': 1, 'private-key': 'PRIVATE'})

    def test_upload_public(self):
        kp = doubles.make(self.mox, doubles.Keypair,
                          name='TestKP', public_key='PUBKEY',
                          fingerprint='FP')
        self.fake_client_set.compute.keypairs.create(kp.name, 'PUBLIC')\
                .AndReturn(kp)
        my_ssh_keys.keypair_from_nova(kp).AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact({'name': kp.name, 'public-key': 'PUBLIC'})
        self.assertEquals(data, 'REPLY')

