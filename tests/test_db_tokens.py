
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


from tests.db import ContextWrappedDBTestCase
from altai_api.db.tokens import TokensDAO


class TokensDAOTestCase(ContextWrappedDBTestCase):
    userid = 'UID'
    email = 'user@example.com'

    def setUp(self):
        super(TokensDAOTestCase, self).setUp()
        token = TokensDAO('test').create(self.userid, self.email)
        self.code = token.code

    def test_create(self):
        token = TokensDAO('test').create(self.userid, self.email)
        self.assertEquals(token.user_id, self.userid)
        self.assertEquals(token.email, self.email)
        self.assertTrue(len(token.code) > 10)
        self.assertEquals(token.token_type, 'test')
        self.assertEquals(token.complete, False)

    def test_get_for_user(self):
        inv = TokensDAO('test').get_for_user(self.userid)
        self.assertEquals(self.userid, inv.user_id)
        self.assertEquals(self.email, inv.email)
        self.assertEquals(self.code, inv.code)
        self.assertEquals(False, inv.complete)

    def test_get_for_wrong_user(self):
        inv = TokensDAO('test').get_for_user('wrong user')
        self.assertEquals(inv, None)

    def test_wrong_type_for_user(self):
        inv = TokensDAO('wrong type').get_for_user(self.userid)
        self.assertEquals(inv, None)

    def test_get_for_user_no_complete(self):
        dao = TokensDAO('test')
        inv = dao.get(self.code)
        dao.complete(inv)
        inv = TokensDAO('test').get_for_user(self.userid)
        self.assertEquals(inv, None)

    def test_get_for_user_respects_order(self):
        # create second token
        TokensDAO('test').create(self.userid, self.email)
        # check that we get first token back
        inv = TokensDAO('test').get_for_user(self.userid)
        self.assertEquals(self.code, inv.code)

    def test_wrong_type_get(self):
        self.assertAborts(404, TokensDAO('wrong type').get, self.code)

    def test_get_token(self):
        inv = TokensDAO('test').get(self.code)
        self.assertEquals(self.userid, inv.user_id)
        self.assertEquals(self.email, inv.email)
        self.assertEquals(self.code, inv.code)
        self.assertEquals(False, inv.complete)

    def test_get_not_found(self):
        self.assertAborts(404, TokensDAO('test').get, 'wrong code')

    def test_complete(self):
        dao = TokensDAO('test')
        inv = dao.get(self.code)
        dao.complete(inv)
        inv = TokensDAO('test').get(self.code)
        self.assertEquals(True, inv.complete)

    def test_complete_wrong_type(self):
        inv = TokensDAO('test').get(self.code)
        self.assertRaises(ValueError, TokensDAO('xxx').complete, inv)
        inv = TokensDAO('test').get(self.code)
        self.assertEquals(False, inv.complete)
        self.assertEquals(None, inv.complete_at)

    def test_complete_for_user(self):
        # create second token
        TokensDAO('test').create(self.userid, self.email)
        # complete all tokens for user
        TokensDAO('test').complete_for_user(self.userid)
        # check there are no incomplete token for the user
        inv = TokensDAO('test').get_for_user(self.userid)
        self.assertEquals(inv, None)

