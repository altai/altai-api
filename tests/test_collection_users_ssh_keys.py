
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

from tests import doubles
from tests.mocked import MockedTestCase

from altai_api.blueprints import users_ssh_keys

from openstackclient_base import exceptions as osc_exc


class UsersSShKeysListTestCase(MockedTestCase):
    user_id = '42'

    def setUp(self):
        super(UsersSShKeysListTestCase, self).setUp()
        self.mox.StubOutWithMock(users_ssh_keys, 'keypair_to_view')
        self.mox.StubOutWithMock(users_ssh_keys, 'fetch_user')
        self.mox.StubOutWithMock(users_ssh_keys.auth, 'assert_admin')

    def test_list_works(self):
        expected = {
            'collection': {
                'name': 'ssh-keys',
                'parent-href': '/v1/users/42',
                'size': 2
            },
            'ssh-keys': ['REPLY1', 'REPLY2']
        }

        users_ssh_keys.fetch_user(self.user_id, True)
        self.fake_client_set.compute_ext.user_keypairs \
                .list(self.user_id).AndReturn(['K1', 'K2'])
        users_ssh_keys.keypair_to_view('K1').AndReturn('REPLY1')
        users_ssh_keys.keypair_to_view('K2').AndReturn('REPLY2')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/users/%s/ssh-keys/' % self.user_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_works(self):
        self.fake_client_set.compute_ext.user_keypairs\
                .get(self.user_id, 'kp').AndReturn('K1')
        users_ssh_keys.keypair_to_view('K1').AndReturn('REPLY')

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
        users_ssh_keys.auth.assert_admin()
        self.fake_client_set.compute_ext.user_keypairs\
                .delete(self.user_id, 'kp')

        self.mox.ReplayAll()

        rv = self.client.delete('/v1/users/%s/ssh-keys/kp' % self.user_id)
        self.check_and_parse_response(rv, status_code=204)

    def test_delete_not_found(self):
        users_ssh_keys.auth.assert_admin()
        self.fake_client_set.compute_ext.user_keypairs\
                .delete(self.user_id, 'kp') \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        rv = self.client.delete('/v1/users/%s/ssh-keys/kp' % self.user_id)
        self.check_and_parse_response(rv, status_code=404)


class UserUsersSShKeysListTestCase(MockedTestCase):
    user_id = '42'
    IS_ADMIN = False

    def setUp(self):
        super(UserUsersSShKeysListTestCase, self).setUp()
        self.mox.StubOutWithMock(users_ssh_keys, 'keypair_to_view')
        self.mox.StubOutWithMock(users_ssh_keys, 'fetch_user')
        self.mox.StubOutWithMock(users_ssh_keys.auth, 'assert_admin')

    def test_get_works_for_user(self):
        users_ssh_keys.fetch_user(self.user_id, False)
        self.fake_client_set.compute_ext.user_keypairs\
                .get(self.user_id, 'kp').AndReturn('K1')
        users_ssh_keys.keypair_to_view('K1').AndReturn('REPLY')

        self.mox.ReplayAll()

        rv = self.client.get('/v1/users/%s/ssh-keys/kp' % self.user_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')


class CreateMySshKeyTestCase(MockedTestCase):
    user_id = '42'

    def setUp(self):
        super(CreateMySshKeyTestCase, self).setUp()
        self.mox.StubOutWithMock(users_ssh_keys, 'keypair_to_view')
        self.mox.StubOutWithMock(users_ssh_keys, 'fetch_user')
        self.mox.StubOutWithMock(users_ssh_keys.auth, 'assert_admin')

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

        users_ssh_keys.auth.assert_admin()
        users_ssh_keys.fetch_user(self.user_id, True)
        self.fake_client_set.compute_ext.user_keypairs \
                .create(self.user_id, kp.name, 'PUBLIC') \
                .AndReturn(kp)
        users_ssh_keys.keypair_to_view(kp).AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact({'name': kp.name, 'public-key': 'PUBLIC'})
        self.assertEquals(data, 'REPLY')

    def test_upload_bad(self):
        users_ssh_keys.auth.assert_admin()
        users_ssh_keys.fetch_user(self.user_id, True)
        self.fake_client_set.compute_ext.user_keypairs \
                .create(self.user_id, 'TestKP', 'PUBLIC') \
                .AndRaise(osc_exc.BadRequest('Keypair data is invalid'))

        self.mox.ReplayAll()
        data = self.interact({'name': 'TestKP', 'public-key': 'PUBLIC'},
                             expected_status_code=400)
        self.assertTrue('Keypair data' in data.get('message', ''))

    def test_public_key_required(self):
        self.mox.ReplayAll()
        self.interact({'name': 'TestKP'}, expected_status_code=400)

