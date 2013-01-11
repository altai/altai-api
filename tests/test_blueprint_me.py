
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
from tests import doubles, ContextWrappedTestCase
from tests.mocked import MockedTestCase

from altai_api.db.tokens import Token

from openstackclient_base import exceptions as osc_exc
from altai_api import exceptions as exc

from altai_api.blueprints import users, me


class MeTestCase(MockedTestCase):

    def setUp(self):
        super(MeTestCase, self).setUp()
        self.mox.StubOutWithMock(users, 'user_from_nova')

    def test_get_me(self):
        self.fake_client_set.http_client.access['user']['id'] = 'user-a'
        self.fake_client_set.identity_admin.users\
                .get('user-a').AndReturn('user-a')
        users.user_from_nova('user-a').AndReturn('dict-a')
        self.mox.ReplayAll()

        rv = self.client.get('/v1/me')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'dict-a')


class FindUserTestCase(MockedTestCase, ContextWrappedTestCase):

    def test_only_one(self):
        self.mox.ReplayAll()
        self.assertRaises(exc.InvalidRequest,
                          me._find_user, {'email': 'email', 'name': 'name'})

    def test_find_by_id(self):
        uid = 'UID42'
        self.fake_client_set.identity_admin.users.get(uid).AndReturn('USER')

        self.mox.ReplayAll()
        self.assertEquals('USER', me._find_user({'id': uid}))

    def test_find_by_name(self):
        name = 'iv'
        self.fake_client_set.identity_admin.users.find(name=name)\
                .AndReturn('USER')

        self.mox.ReplayAll()
        self.assertEquals('USER', me._find_user({'name': name}))

    def test_find_by_mail(self):
        mail = 'test@example.com'
        self.fake_client_set.identity_admin.users.find(email=mail)\
                .AndReturn('USER')

        self.mox.ReplayAll()
        self.assertEquals('USER', me._find_user({'email': mail}))

    def test_not_found(self):
        uid = 'UID42'
        self.fake_client_set.identity_admin.users.get(uid)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        self.assertEquals(None, me._find_user({'id': uid}))


class ResetPasswordTestCase(MockedTestCase):

    def setUp(self):
        super(ResetPasswordTestCase, self).setUp()
        self.mox.StubOutWithMock(me, '_find_user')
        self.mox.StubOutWithMock(me, 'fetch_user')
        self.mox.StubOutWithMock(me, 'ResetTokensDAO')
        self.mox.StubOutWithMock(me, 'send_reset_password')
        self.mox.StubOutWithMock(me, 'update_user_data')

    def test_reset_password(self):
        uid, name, email, code = 'UID', 'NAME', 'EM@IL', 'THE_CODE'
        params = {
            'name': 'USERNAME',
            'link-template': 'LINK_TEMPLATE'
        }
        user = doubles.make(self.mox, doubles.User,
                            name=name, id=uid, email=email, fullname='')
        token = Token(user_id=uid, email=email, code=code)

        me._find_user(params).AndReturn(user)
        me.ResetTokensDAO.create(uid, email).AndReturn(token)
        me.send_reset_password(email, code, name,
                               link_template='LINK_TEMPLATE',
                               greeting='')

        self.mox.ReplayAll()
        rv = self.client.post('/v1/me/reset-password',
                              data=json.dumps(params),
                              content_type='application/json')
        self.check_and_parse_response(rv, status_code=204)

    def test_reset_password_no_user(self):
        params = {
            'name': 'USERNAME',
            'link-template': 'LINK_TEMPLATE'
        }
        me._find_user(params).AndReturn(None)

        self.mox.ReplayAll()
        rv = self.client.post('/v1/me/reset-password',
                              data=json.dumps(params),
                              content_type='application/json')
        self.check_and_parse_response(rv, status_code=204)

    def test_apply_password_reset(self):
        uid, code = 'UID', 'THE_CODE'
        token = Token(user_id=uid, code=code, complete=False)
        params = { 'password': 'p@ssw0rd' }

        me.ResetTokensDAO.get('THE_CODE').AndReturn(token)
        me.fetch_user(uid).AndReturn('USER')
        me.update_user_data('USER', params)
        me.ResetTokensDAO.complete_for_user(uid)

        self.mox.ReplayAll()
        rv = self.client.post('/v1/me/reset-password/%s' % code,
                              data=json.dumps(params),
                              content_type='application/json')
        self.check_and_parse_response(rv, status_code=204)

    def test_apply_password_reset_complete(self):
        uid, code = 'UID', 'THE_CODE'
        token = Token(user_id=uid, code=code, complete=True)
        params = { 'password': 'p@ssw0rd' }

        me.ResetTokensDAO.get('THE_CODE').AndReturn(token)
        self.mox.ReplayAll()
        rv = self.client.post('/v1/me/reset-password/%s' % code,
                              data=json.dumps(params),
                              content_type='application/json')
        self.check_and_parse_response(rv, status_code=404)

    def test_apply_password_reset_empty(self):
        uid, code = 'UID', 'THE_CODE'
        token = Token(user_id=uid, code=code, complete=False)
        params = { }

        me.ResetTokensDAO.get('THE_CODE').AndReturn(token)
        me.fetch_user(uid).AndReturn('USER')

        self.mox.ReplayAll()
        rv = self.client.post('/v1/me/reset-password/%s' % code,
                              data=json.dumps(params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertEquals('password', data.get('element-name'))

    def test_apply_password_reset_exrtra(self):
        uid, code = 'UID', 'THE_CODE'
        token = Token(user_id=uid, code=code, complete=False)
        params = {
            'password': 'p@ssw0rd',
            'fullname': 'Cannot Be Set'
        }

        me.ResetTokensDAO.get('THE_CODE').AndReturn(token)
        me.fetch_user(uid).AndReturn('USER')

        self.mox.ReplayAll()
        rv = self.client.post('/v1/me/reset-password/%s' % code,
                              data=json.dumps(params),
                              content_type='application/json')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertEquals('fullname', data.get('element-name'))

