
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

from altai_api.blueprints import users_ssh_keys

from openstackclient_base import exceptions as osc_exc


class UsersSShKeysListTestCase(MockedTestCase):
    user_id = '42'

    def setUp(self):
        super(UsersSShKeysListTestCase, self).setUp()
        self.mox.StubOutWithMock(users_ssh_keys, 'keypair_from_nova')

    def test_list_works(self):
        expected = {
            'collection': {
                'name': 'ssh-keys',
                'parent-href': '/v1/users/42',
                'size': 2
            },
            'ssh-keys': ['REPLY1', 'REPLY2']
        }

        self.fake_client_set.identity_admin.users \
                .get(self.user_id).AndReturn('USER')
        self.fake_client_set.compute_ext.user_keypairs \
                .list('USER').AndReturn(['K1', 'K2'])
        users_ssh_keys.keypair_from_nova('K1').AndReturn('REPLY1')
        users_ssh_keys.keypair_from_nova('K2').AndReturn('REPLY2')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/users/%s/ssh-keys/' % self.user_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_works(self):
        self.fake_client_set.compute_ext.user_keypairs\
                .get(self.user_id, 'kp').AndReturn('K1')
        users_ssh_keys.keypair_from_nova('K1').AndReturn('REPLY')

        self.mox.ReplayAll()

        rv = self.client.get('/v1/users/%s/ssh-keys/kp' % self.user_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_not_found(self):
        self.fake_client_set.compute_ext.user_keypairs\
                .get(self.user_id, 'kp') \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        rv = self.client.get('/v1/users/%s/ssh-keys/kp' % self.user_id)
        self.check_and_parse_response(rv, status_code=404)

    def test_delete_works(self):
        self.fake_client_set.compute_ext.user_keypairs\
                .delete(self.user_id, 'kp')

        self.mox.ReplayAll()

        rv = self.client.delete('/v1/users/%s/ssh-keys/kp' % self.user_id)
        self.check_and_parse_response(rv, status_code=204)

    def test_delete_not_found(self):
        self.fake_client_set.compute_ext.user_keypairs\
                .delete(self.user_id, 'kp') \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        rv = self.client.delete('/v1/users/%s/ssh-keys/kp' % self.user_id)
        self.check_and_parse_response(rv, status_code=404)


class CreateMySshKeyTestCase(MockedTestCase):
    user_id = '42'

    def setUp(self):
        super(CreateMySshKeyTestCase, self).setUp()
        self.mox.StubOutWithMock(users_ssh_keys, 'keypair_from_nova')

    def interact(self, data, expected_status_code=200):
        rv = self.client.post('/v1/users/%s/ssh-keys/' % self.user_id,
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
                    rv, status_code=expected_status_code)

    def test_upload_public(self):
        kp = doubles.make(self.mox, doubles.Keypair,
                          name='TestKP', public_key='PUBKEY',
                          fingerprint='FP')
        self.fake_client_set.identity_admin.users \
                .get(self.user_id).AndReturn('USER')
        self.fake_client_set.compute_ext.user_keypairs \
                .create('USER', kp.name, 'PUBLIC') \
                .AndReturn(kp)
        users_ssh_keys.keypair_from_nova(kp).AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact({'name': kp.name, 'public-key': 'PUBLIC'})
        self.assertEquals(data, 'REPLY')

    def test_public_key_required(self):
        self.mox.ReplayAll()
        self.interact({'name': 'TestKP'}, expected_status_code=400)

