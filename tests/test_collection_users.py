
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

from datetime import datetime
from openstackclient_base import exceptions as osc_exc

from altai_api.blueprints import users

from tests.mocked import MockedTestCase
from tests import doubles
from altai_api.db.tokens import Token


class UserFromNovaTestCase(MockedTestCase):
    maxDiff = None

    def setUp(self):
        super(UserFromNovaTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'InvitesDAO')

    def test_user_from_nova_works(self):
        user = doubles.make(self.mox, doubles.User,
                            id=u'42', name=u'iv', email=u'iv@example.com',
                            fullname=u'Example User', enabled=True)

        user.list_roles().AndReturn([
            doubles.make(self.mox, doubles.Role,
                         role={'id': u'42', 'name': u'admin'},
                         tenant={'id': 'SYS', 'name': 'systenant'}),
            doubles.make(self.mox, doubles.Role,
                         role={'id': u'43', 'name': u'member'},
                         tenant={'id': 'PID', 'name': 'ptest'}),
            doubles.make(self.mox, doubles.Role,
                         role={'id': u'44', 'name': u'member'},
                         tenant={'id': 'PID2', 'name': 'other'})
        ])

        expected = {
            u'id': u'42',
            u'name': u'iv',
            u'href': u'/v1/users/42',
            u'email': u'iv@example.com',
            u'fullname': 'Example User',
            u'admin': True,
            u'projects': [
                {
                    u'id': 'PID',
                    u'name': 'ptest',
                    u'href': '/v1/projects/PID'
                },
                {
                    u'id': 'PID2',
                    u'name': 'other',
                    u'href': '/v1/projects/PID2'
                }
            ],
            u'completed-registration': True
        }

        self.mox.ReplayAll()

        with self.app.test_request_context():
            data = users.user_from_nova(user)
        self.assertEquals(data, expected)

    def test_user_from_nova_disabled_noadmin(self):
        user = doubles.make(self.mox, doubles.User,
                            id=u'42', name=u'iv', email=u'iv@example.com',
                            fullname=u'Example User', enabled=False)

        user.list_roles().AndReturn([])
        users.InvitesDAO.get_for_user(user.id).AndReturn(None)

        expected = {
            u'id': u'42',
            u'name': u'iv',
            u'href': u'/v1/users/42',
            u'email': u'iv@example.com',
            u'fullname': 'Example User',
            u'admin': False,
            u'projects': [],
            u'completed-registration': False
        }

        self.mox.ReplayAll()

        with self.app.test_request_context():
            data = users.user_from_nova(user)
        self.assertEquals(data, expected)

    def test_user_from_nova_invite(self):
        user = doubles.make(self.mox, doubles.User,
                            id=u'42', name=u'iv', email=u'iv@example.com',
                            fullname=u'Example User', enabled=False)
        date = datetime(2012, 9, 15, 15, 03, 00)
        invite = Token(user_id=user.id, created_at=date, complete=False)

        user.list_roles().AndReturn([])
        users.InvitesDAO.get_for_user(user.id).AndReturn(invite)

        expected = {
            u'id': u'42',
            u'name': u'iv',
            u'href': u'/v1/users/42',
            u'email': u'iv@example.com',
            u'fullname': 'Example User',
            u'admin': False,
            u'projects': [],
            u'completed-registration': False,
            u'invited-at': date
        }

        self.mox.ReplayAll()

        with self.app.test_request_context():
            data = users.user_from_nova(user)
        self.assertEquals(data, expected)


class UsersCollectionTestCase(MockedTestCase):

    def setUp(self):
        super(UsersCollectionTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')

    def test_list_users(self):
        self.fake_client_set.identity_admin \
                .users.list().AndReturn(['user-a', 'user-b'])
        users.user_from_nova('user-a').AndReturn('dict-a')
        users.user_from_nova('user-b').AndReturn('dict-b')
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
        self.fake_client_set.identity_admin.users\
                .get('user-a').AndReturn('user-a')
        users.user_from_nova('user-a').AndReturn('dict-a')
        self.mox.ReplayAll()
        # test
        rv = self.client.get('/v1/users/user-a')
        # verify
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'dict-a')

    def test_get_me(self):
        self.fake_client_set.http_client.access['user']['id'] = 'user-a'
        self.fake_client_set.identity_admin.users\
                .get('user-a').AndReturn('user-a')
        users.user_from_nova('user-a').AndReturn('dict-a')
        self.mox.ReplayAll()

        rv = self.client.get('/v1/me')
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
            name=name, password=passw, email=email,
            enabled=True).AndReturn('new-user')
        client.identity_admin.users.update('new-user', fullname=fullname)
        users.user_from_nova('new-user').AndReturn('new-user-dict')
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

    def test_invite_user(self):
        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        link_template = 'http://altai.example.com/invite?code={{code}}'
        user = doubles.make(self.mox, doubles.User,
                            id='UID', name=name, email=email)
        invite = Token(user_id=user.id, code='THE_CODE', complete=False)
        self.mox.StubOutWithMock(users, 'send_invitation')
        self.mox.StubOutWithMock(users, 'InvitesDAO')

        self.fake_client_set.identity_admin.users.create(
            name=name, password=passw, email=email,
            enabled=False).AndReturn(user)
        users.InvitesDAO.create(user.id, email).AndReturn(invite)
        users.send_invitation(email, 'THE_CODE',
                              link_template, greeting=None)
        users.user_from_nova(user).AndReturn('new-user-dict')

        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "password": passw,
            "admin": False,
            "invite": True,
            "link-template": link_template
        }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-user-dict')

    def test_create_admin(self):
        client = self.fake_client_set
        new_user = doubles.make(self.mox, doubles.User, id='NUID')

        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        client.identity_admin.users.create(
            name=name, password=passw, email=email,
            enabled=True).AndReturn(new_user)

        # see doubles.py, near line 100 for role id and tenant id here
        client.identity_admin.roles.add_user_role(
            'NUID', u'ADMIN_ROLE_ID', u'SYSTENANT_ID')
        users.user_from_nova(new_user).AndReturn('new-user-dict')

        self.mox.ReplayAll()
        post_params = {"name": name, "email": email,
                       "password": passw, "admin": True}
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
            name=name, email=email, password=passw, enabled=True) \
                .AndRaise(osc_exc.BadRequest('fail'))
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

        self.check_and_parse_response(rv, status_code=400)

    def test_update_user(self):
        ia = self.fake_client_set.identity_admin
        # prepare
        (name, email, passw) = ('user-upd', 'user-upd@example.com', 'orange')

        fullname = "User Userovich Upd"
        ia.users.get('new-user').AndReturn('new-user')
        ia.users.update('new-user', name=name, email=email,
                        fullname=fullname).AndReturn('new-user')
        ia.users.update_password('new-user', passw).AndReturn('new-user')
        ia.users.get('new-user').AndReturn('new-user')
        users.user_from_nova('new-user').AndReturn('new-user-dict')
        self.mox.ReplayAll()
        # test
        post_params = {
                       "name": name,
                       "email": email,
                       "password": passw,
                       "fullname": fullname
                      }
        rv = self.client.put('/v1/users/new-user',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-user-dict')

    def test_update_user_not_found(self):
        client = self.fake_client_set

        (name, email, passw) = ('user-upd', 'user-upd@example.com', 'orange')
        client.identity_admin.users.get('new-user')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        post_params = { "name": name, "email": email, "password": passw }
        rv = self.client.put('/v1/users/new-user',
                              data=json.dumps(post_params),
                              content_type='application/json')

        self.check_and_parse_response(rv, status_code=404)

    def test_update_grant_admin(self):
        client = self.fake_client_set
        uid = u'user-a'

        user = doubles.make(self.mox, doubles.User, id=uid)
        client.identity_admin.users.get(uid).AndReturn(user)
        client.identity_admin.roles.add_user_role(
            u'user-a', u'ADMIN_ROLE_ID', u'SYSTENANT_ID')
        client.identity_admin.users.get(uid).AndReturn('same-user')
        users.user_from_nova('same-user').AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.put(u'/v1/users/%s' % uid,
                             data=json.dumps({'admin': True}),
                             content_type='application/json')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_update_revoke_admin(self):
        client = self.fake_client_set
        uid = u'user-a'

        user = doubles.make(self.mox, doubles.User, id=uid)
        client.identity_admin.users.get(uid).AndReturn(user)
        client.identity_admin.roles.remove_user_role(
            u'user-a', u'ADMIN_ROLE_ID', u'SYSTENANT_ID')
        client.identity_admin.users.get(uid).AndReturn('same-user')
        users.user_from_nova('same-user').AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.put(u'/v1/users/%s' % uid,
                             data=json.dumps({'admin': False}),
                             content_type='application/json')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_update_revoke_admin_idemptent(self):
        client = self.fake_client_set
        uid = u'user-a'

        user = doubles.make(self.mox, doubles.User, id=uid)
        client.identity_admin.users.get(uid).AndReturn(user)
        client.identity_admin.roles.remove_user_role(
            u'user-a', u'ADMIN_ROLE_ID', u'SYSTENANT_ID')\
                .AndRaise(osc_exc.NotFound('failure'))
        # raised, but nothing should happen
        client.identity_admin.users.get(uid).AndReturn('same-user')
        users.user_from_nova('same-user').AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.put(u'/v1/users/%s' % uid,
                             data=json.dumps({'admin': False}),
                             content_type='application/json')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

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

