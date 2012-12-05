
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
from openstackclient_base import exceptions as osc_exc
from altai_api.collection import users
from tests.mocked import MockedTestCase

class UsersCollectionTestCase(MockedTestCase):

    def setUp(self):
        super(UsersCollectionTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_to_dict')

    def test_list_users(self):
        self.fake_client_set.identity_admin.users.list().AndReturn(['user-a', 'user-b'])
        users.user_to_dict('user-a').AndReturn('dict-a')
        users.user_to_dict('user-b').AndReturn('dict-b')
        expected = {
            'collection': {
                'name': 'users',
                'size': 2
            },
            'users': [ 'dict-a', 'dict-b' ]
        }

        self.mox.ReplayAll()

        rv = self.client.get('/v1/users/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_user(self):
        # prepare
        self.fake_client_set.identity_admin.users.get('user-a').AndReturn('user-a')
        users.user_to_dict('user-a').AndReturn('dict-a')
        self.mox.ReplayAll()
        # test
        rv = self.client.get('/v1/users/user-a')
        # verify
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'dict-a')

    def test_get_user_not_found(self):
        # prepare
        self.fake_client_set.identity_admin.users.get('user-a') \
            .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        # test
        rv = self.client.get('/v1/users/user-a')
        # verify
        self.check_and_parse_response(rv, status_code=404)

    def test_create_user(self):
        client = self.fake_client_set
        # prepare
        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        fullname = "User Userovich"
        client.identity_admin.users.create(
            name=name, password=passw, email=email).AndReturn('new-user')
        client.identity_admin.users.update('new-user', fullname=fullname)
        users.user_to_dict('new-user').AndReturn('new-user-dict')
        self.mox.ReplayAll()
        # test
        post_params = {
                       "name": name,
                       "email": email,
                       "password": passw,
                       "fullname": fullname,
                       "admin": False,
                      }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-user-dict')

    def test_create_existing_user(self):
        client = self.fake_client_set
        # prepare
        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        fullname = "User Userovich"
        client.identity_admin.users.create(
            name=name, email=email, password=passw).AndRaise(osc_exc.BadRequest('fail'))
        self.mox.ReplayAll()
        # test
        post_params = {
                       "name": name,
                       "email": email,
                       "password": passw,
                       "fullname": fullname,
                       "admin": False,
                      }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv, status_code=400)

    def test_update_user(self):
        client = self.fake_client_set
        # prepare
        (name, email, passw) = ('user-upd', 'user-upd@example.com', 'banana-upd')
        fullname = "User Userovich Upd"
        client.identity_admin.users.get('new-user').AndReturn('new-user')
        client.identity_admin.users.update('new-user', name=name, email=email,
                                           fullname=fullname).AndReturn('new-user')
        client.identity_admin.users.update_password('new-user', passw).AndReturn('new-user')
        client.identity_admin.users.get('new-user').AndReturn('new-user')
        users.user_to_dict('new-user').AndReturn('new-user-dict')
        self.mox.ReplayAll()
        # test
        post_params = {
                       "name": name,
                       "email": email,
                       "password": passw,
                       "fullname": fullname,
                       "admin": False,
                      }
        rv = self.client.put('/v1/users/new-user',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-user-dict')

    def test_delete_user(self):
        # prepare
        self.fake_client_set.identity_admin.users.delete('user-a')
        self.mox.ReplayAll()
        # test
        rv = self.client.delete('/v1/users/user-a')
        # verify
        self.assertEquals(rv.status_code, 204)

    def test_delete_user_not_found(self):
        # prepare
        self.fake_client_set.identity_admin.users.delete('user-a')\
                .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        # test
        rv = self.client.delete('/v1/users/user-a')
        # verify
        self.assertEquals(rv.status_code, 404)


