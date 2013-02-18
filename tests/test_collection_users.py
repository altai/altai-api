
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

import flask
from flask import json

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
        self.roles = [
            doubles.make(self.mox, doubles.Role,
                         role={'id': u'42', 'name': u'admin'},
                         tenant={'id': 'SYS', 'name': 'systenant'}),
            doubles.make(self.mox, doubles.Role,
                         role={'id': u'43', 'name': u'member'},
                         tenant={'id': 'PID', 'name': 'ptest'}),
            doubles.make(self.mox, doubles.Role,
                         role={'id': u'44', 'name': u'member'},
                         tenant={'id': 'PID2', 'name': 'other'})
        ]

    def test_user_from_nova_works(self):
        user = doubles.make(self.mox, doubles.User,
                            id=u'42', name=u'iv', email=u'iv@example.com',
                            fullname=u'Example User', enabled=True)
        user.list_roles().AndReturn(self.roles)

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
            self.install_fake_auth()
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
            self.install_fake_auth()
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
            self.install_fake_auth()
            data = users.user_from_nova(user)
        self.assertEquals(data, expected)

    def test_user_from_nova_send_invite_code(self):
        """What we got when resending invite without disabling user"""
        user = doubles.make(self.mox, doubles.User,
                            id=u'42', name=u'iv', email=u'iv@example.com',
                            fullname=u'Example User', enabled=True)
        date = datetime(2012, 9, 15, 15, 03, 00)
        invite = Token(user_id=user.id, created_at=date,
                       complete=False, code='THE_CODE')

        user.list_roles().AndReturn([])
        expected = {
            u'id': u'42',
            u'name': u'iv',
            u'href': u'/v1/users/42',
            u'email': u'iv@example.com',
            u'fullname': 'Example User',
            u'admin': False,
            u'projects': [],
            u'completed-registration': True,  # because user can work
            u'invited-at': date,
            u'invitation-code': 'THE_CODE'
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            data = users.user_from_nova(user, invite, send_code=True)
        self.assertEquals(data, expected)

    def test_user_from_nova_with_my_projects(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id='PID', name='ptest')
        user = doubles.make(self.mox, doubles.User,
                            id=u'42', name=u'iv', email=u'iv@example.com',
                            fullname=u'Example User', enabled=True)

        user.list_roles().AndReturn(self.roles)
        self.fake_client_set.identity_public.tenants.list()\
                .AndReturn([tenant])

        expected_projects = [{
            u'id': 'PID',
            u'name': 'ptest',
            u'href': '/v1/projects/PID'
        }]
        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.install_fake_auth()
            flask.g.my_projects = True
            data = users.user_from_nova(user)
        self.assertEquals(data['projects'], expected_projects)


class GetUsersTestCase(MockedTestCase):

    def setUp(self):
        super(GetUsersTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')
        self.mox.StubOutWithMock(users, 'member_role_id')

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

    def test_get_user_not_found(self):
        # prepare
        self.fake_client_set.identity_admin.users.get('user-a') \
            .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        # test
        rv = self.client.get('/v1/users/user-a')
        # verify
        self.check_and_parse_response(rv, status_code=404)


class CreateUserTestCase(MockedTestCase):

    def setUp(self):
        super(CreateUserTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')
        self.mox.StubOutWithMock(users, 'member_role_id')

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

    def test_create_user_with_projects(self):
        client = self.fake_client_set

        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        client.identity_admin.users.create(
            name=name, password=passw, email=email,
            enabled=True).AndReturn('new-user')
        users.member_role_id().AndReturn('member-role')
        client.identity_admin.roles.add_user_role(
            user='new-user', role='member-role', tenant='PID1')
        client.identity_admin.roles.add_user_role(
            user='new-user', role='member-role', tenant='PID2')
        users.user_from_nova('new-user').AndReturn('new-user-dict')
        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "password": passw,
            "projects": ['PID1', 'PID2'],
            "admin": False,
        }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-user-dict')

    def test_create_user_with_bad_projects(self):
        client = self.fake_client_set

        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        client.identity_admin.users.create(
            name=name, password=passw, email=email,
            enabled=True).AndReturn('new-user')
        users.member_role_id().AndReturn('member-role')
        client.identity_admin.roles.add_user_role(
            user='new-user', role='member-role', tenant='PID1') \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "password": passw,
            "projects": ['PID1', 'PID2'],
            "admin": False,
        }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')

        data = self.check_and_parse_response(rv, 400)
        self.assertEquals('projects', data.get('element-name'))
        self.assertEquals('PID1', data.get('element-value'))

    def test_create_without_password_fails(self):
        name, email = 'user-a', 'user-a@example.com'
        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "projects": ['PID1', 'PID2'],
            "admin": False,
        }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv, 400)
        self.assertEquals('password', data.get('element-name'))

    def test_create_no_link_template(self):
        name, email, passw = 'user-a', 'user-a@example.com', 'bananas'
        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "password": passw,
            "projects": ['PID1', 'PID2'],
            "admin": False,
            "link-template": "http://{{code}}"
        }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv, 400)
        self.assertEquals('link-template', data.get('element-name'))

    def test_create_no_send_invite_mail(self):
        name, email, passw = 'user-a', 'user-a@example.com', 'bananas'
        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "password": passw,
            "projects": ['PID1', 'PID2'],
            "admin": False,
            "send-invite-mail": False
        }
        rv = self.client.post('/v1/users/',
                              data=json.dumps(post_params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv, 400)
        self.assertEquals('send-invite-mail', data.get('element-name'))

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
        users.user_from_nova(user, invite, send_code=False)\
                .AndReturn('new-user-dict')

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

    def test_invite_user_no_mail(self):
        (name, email, passw) = ('user-a', 'user-a@example.com', 'bananas')
        user = doubles.make(self.mox, doubles.User,
                            id='UID', name=name, email=email)
        invite = Token(user_id=user.id, code='THE_CODE', complete=False)
        self.mox.StubOutWithMock(users, 'send_invitation')
        self.mox.StubOutWithMock(users, 'InvitesDAO')

        self.fake_client_set.identity_admin.users.create(
            name=name, password=passw, email=email,
            enabled=False).AndReturn(user)
        users.InvitesDAO.create(user.id, email).AndReturn(invite)
        users.user_from_nova(user, invite, send_code=True)\
                .AndReturn('new-user-dict')

        self.mox.ReplayAll()

        post_params = {
            "name": name,
            "email": email,
            "password": passw,
            "send-invite-mail": False,
            "invite": True,
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


class UpdateUserTestCase(MockedTestCase):

    def setUp(self):
        super(UpdateUserTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')
        self.mox.StubOutWithMock(users, 'member_role_id')

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

    def test_update_user_late_not_found(self):
        ia = self.fake_client_set.identity_admin
        # prepare
        (name, email, passw) = ('user-upd', 'user-upd@example.com', 'orange')

        ia.users.get('new-user').AndReturn('new-user')
        ia.users.update('new-user', name=name, email=email) \
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

    def test_update_revoke_admin_idempotent(self):
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


class UpdateUserSelfTestCase(MockedTestCase):
    IS_ADMIN = False
    name = 'user-upd'

    def setUp(self):
        super(UpdateUserSelfTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')
        self.mox.StubOutWithMock(users, 'member_role_id')
        self.mox.StubOutWithMock(users.auth, 'current_user_id')
        self.mox.StubOutWithMock(users, 'fetch_user')
        self.user = doubles.make(self.mox, doubles.User,
                                 id='UID', name='old-name')

    def test_update_self(self):
        users.fetch_user(self.user.id, False).AndReturn(self.user)
        users.auth.current_user_id().AndReturn(self.user.id)  # to compare
        self.fake_client_set.identity_admin \
                    .users.update(self.user, name=self.name) \
                    .AndReturn('new-user')

        users.fetch_user(self.user.id, False).AndReturn('new-user')
        users.user_from_nova('new-user').AndReturn('new-user-dict')
        self.mox.ReplayAll()

        post_params = { "name": self.name }
        rv = self.client.put('/v1/users/%s' % self.user.id,
                              data=json.dumps(post_params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'new-user-dict')

    def test_update_paranoia(self):
        # NOTE(imelnikov): this can never happen, as other users
        # are 'invisible', but it's still better to double check
        users.fetch_user(self.user.id, False).AndReturn(self.user)
        users.auth.current_user_id().AndReturn('OTHER_UID')  # to compare

        self.mox.ReplayAll()

        post_params = { "name": self.name }
        rv = self.client.put('/v1/users/%s' % self.user.id,
                              data=json.dumps(post_params),
                              content_type='application/json')
        self.check_and_parse_response(rv, status_code=403)


class DeleteUserTestCase(MockedTestCase):

    def setUp(self):
        super(DeleteUserTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')
        self.mox.StubOutWithMock(users, 'member_role_id')

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


class SendInviteTestCase(MockedTestCase):

    def setUp(self):
        super(SendInviteTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')
        self.mox.StubOutWithMock(users, 'send_invitation')
        self.mox.StubOutWithMock(users, 'InvitesDAO')
        self.mox.StubOutWithMock(users, 'update_user_data')
        self.mox.StubOutWithMock(users.auth, 'assert_admin')

        self.uid = 'UID'
        self.user = doubles.make(self.mox, doubles.User,
                                 id=self.uid,
                                 email='user@example.com',
                                 fullname='Test User')
        self.invite = Token(user_id=self.uid, code='THE_CODE', complete=False)

    def interact(self, data, expected_status_code=200):
        rv = self.client.post('/v1/users/%s/send-invite' % self.uid,
                              data=json.dumps(data),
                              content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_resend_works(self):
        self.fake_client_set.identity_admin.users.get(self.uid)\
                .AndReturn(self.user)
        users.InvitesDAO.create(self.uid, self.user.email)\
                .AndReturn(self.invite)
        users.send_invitation(self.user.email, self.invite.code,
                              None, greeting=self.user.fullname)
        users.user_from_nova(self.user, self.invite, send_code=False)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact({})
        self.assertEquals(data, 'REPLY')

    def test_resend_user_not_found(self):
        self.fake_client_set.identity_admin.users.get(self.uid)\
                .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        self.interact({}, expected_status_code=404)

    def test_resend_disable_user(self):
        self.fake_client_set.identity_admin.users.get(self.uid)\
                .AndReturn(self.user)
        users.InvitesDAO.create(self.uid, self.user.email)\
                .AndReturn(self.invite)
        users.auth.assert_admin()
        users.update_user_data(self.user, {
            'enabled': False,
            'password': None
        })
        users.send_invitation(self.user.email, self.invite.code,
                              None, greeting=self.user.fullname)
        users.user_from_nova(self.user, self.invite, send_code=False)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact({'disable-user': True})
        self.assertEquals(data, 'REPLY')

    def test_resend_no_mail(self):
        self.fake_client_set.identity_admin.users.get(self.uid)\
                .AndReturn(self.user)
        users.InvitesDAO.create(self.uid, self.user.email)\
                .AndReturn(self.invite)
        users.auth.assert_admin()
        users.user_from_nova(self.user, self.invite, send_code=True)\
                .AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact({'send-invite-mail': False})
        self.assertEquals(data, 'REPLY')


class UserFetchesUserTestCase(MockedTestCase):
    IS_ADMIN = False

    def setUp(self):
        super(UserFetchesUserTestCase, self).setUp()
        self.mox.StubOutWithMock(users.auth, 'admin_client_set')
        self.mox.StubOutWithMock(users.auth, 'current_user_id')
        self.mox.StubOutWithMock(users.auth, 'current_user_project_ids')
        self.user = doubles.make(self.mox, doubles.User,
                                 id='UID', name='Test')
        self.role = doubles.make(self.mox, doubles.Role,
                                 tenant={'id': 'PID'},
                                 id='ROLE', name='Role')
        self.admin_cs = self._fake_client_set_factory()

    def test_fetch_user_as_user(self):
        users.auth.admin_client_set().AndReturn(self.admin_cs)
        self.admin_cs.identity_admin.users.get('UID').AndReturn(self.user)
        users.auth.current_user_id().AndReturn('ME')
        self.user.list_roles().AndReturn([self.role])
        users.auth.current_user_project_ids().AndReturn(['PID', 'PID2'])

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            user = users.fetch_user('UID', False)
        self.assertEquals(user, self.user)

    def test_fetch_self(self):
        users.auth.admin_client_set().AndReturn(self.admin_cs)
        self.admin_cs.identity_admin.users.get('UID').AndReturn(self.user)
        users.auth.current_user_id().AndReturn('UID')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            user = users.fetch_user('UID', False)
        self.assertEquals(user, self.user)

    def test_fetch_invisible(self):
        users.auth.admin_client_set().AndReturn(self.admin_cs)
        self.admin_cs.identity_admin.users.get('UID').AndReturn(self.user)
        users.auth.current_user_id().AndReturn('ME')
        self.user.list_roles().AndReturn([self.role])
        users.auth.current_user_project_ids().AndReturn(['PID1', 'PID2'])

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(404, users.fetch_user, 'UID', False)

    def test_fetch_not_found(self):
        users.auth.admin_client_set().AndReturn(self.admin_cs)
        self.admin_cs.identity_admin.users.get('UID') \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(404, users.fetch_user, 'UID', False)

    def test_fetch_user_error(self):
        users.auth.admin_client_set().AndReturn(self.admin_cs)
        self.admin_cs.identity_admin.users.get('UID').AndReturn(self.user)
        users.auth.current_user_id().AndReturn('ME')
        self.user.list_roles() \
                .AndRaise(osc_exc.NotFound('gone'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(404, users.fetch_user, 'UID', False)

