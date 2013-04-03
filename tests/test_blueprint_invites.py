
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

from openstackclient_base import exceptions as osc_exc

from altai_api.db.tokens import Token
from tests import doubles, TestCase
from tests.mocked import MockedTestCase

from altai_api.blueprints import invites


class InvitesTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(InvitesTestCase, self).setUp()
        self.mox.StubOutWithMock(invites, 'InvitesDAO')
        self.mox.StubOutWithMock(invites, 'user_to_view')
        self.mox.StubOutWithMock(invites.auth, 'admin_client_set')

        self.code = '42'
        self.token = Token(code=self.code,
                            complete=False, user_id='UID')
        self.user = doubles.make(self.mox, doubles.User,
                                 id='UID', name='self.user', enabled=False)

        self.fake_client_set = self._fake_client_set_factory()

    def test_get_works(self):
        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        self.fake_client_set.identity_admin.users.get(self.user.id)\
                .AndReturn(self.user)
        invites.user_to_view(self.user, self.token).AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/invites/%s' % self.code)
        data = self.check_and_parse_response(rv, authenticated=False)
        self.assertEquals(data, 'REPLY')

    def test_complete_invite_404(self):
        self.token.complete = True

        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        invites.InvitesDAO.get(self.code).AndReturn(self.token)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/invites/%s' % self.code)
        self.check_and_parse_response(rv, status_code=404,
                                      authenticated=False)

    def test_user_not_found(self):
        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        self.fake_client_set.identity_admin.users.get('UID')\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/invites/%s' % self.code)
        self.check_and_parse_response(rv, status_code=404,
                                      authenticated=False)

    def test_user_enabled(self):
        self.user.enabled = True

        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        self.fake_client_set.identity_admin.users.get(self.user.id)\
                .AndReturn(self.user)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/invites/%s' % self.code)
        self.check_and_parse_response(rv, status_code=404,
                                      authenticated=False)

    def test_accept_works(self):
        params = { 'password': '123' }
        user_mgr = self.fake_client_set.identity_admin.users

        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        invites.auth.admin_client_set().AndReturn(self.fake_client_set)
        user_mgr.get(self.user.id).AndReturn(self.user)
        invites.auth.admin_client_set().AndReturn(self.fake_client_set)
        user_mgr.update(self.user, enabled=True)
        user_mgr.update_password(self.user, '123')

        invites.auth.admin_client_set().AndReturn(self.fake_client_set)
        user_mgr.get(self.user.id).AndReturn(self.user)

        invites.InvitesDAO.complete_for_user(self.user.id)
        invites.user_to_view(self.user, self.token).AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.put('/v1/invites/%s' % self.code,
                             data=json.dumps(params),
                             content_type='application/json')
        data = self.check_and_parse_response(rv, authenticated=False)
        self.assertEquals(data, 'REPLY')

    def test_accept_late_not_found(self):
        params = { 'password': '123' }

        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        user_mgr = self.fake_client_set.identity_admin.users
        user_mgr.get(self.user.id).AndReturn(self.user)
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        user_mgr.update(self.user, enabled=True)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.put('/v1/invites/%s' % self.code,
                             data=json.dumps(params),
                             content_type='application/json')
        self.check_and_parse_response(rv, status_code=404,
                                      authenticated=False)

    def test_accept_latest_not_found(self):
        params = { 'password': '123' }

        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        user_mgr = self.fake_client_set.identity_admin.users
        user_mgr.get(self.user.id).AndReturn(self.user)
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        user_mgr.update(self.user, enabled=True)
        user_mgr.update_password(self.user, '123')

        invites.auth.admin_client_set().AndReturn(self.fake_client_set)
        user_mgr.get(self.user.id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.put('/v1/invites/%s' % self.code,
                             data=json.dumps(params),
                             content_type='application/json')
        self.check_and_parse_response(rv, status_code=404,
                                      authenticated=False)

    def test_accept_no_password(self):
        self.mox.ReplayAll()
        rv = self.client.put('/v1/invites/%s' % self.code,
                             data=json.dumps({}),
                             content_type='application/json')
        self.check_and_parse_response(rv, status_code=400,
                                      authenticated=False)

    def test_drop_invite(self):
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        user_mgr = self.fake_client_set.identity_admin.users
        user_mgr.get(self.user.id).AndReturn(self.user)
        self.user.delete()
        invites.InvitesDAO.complete_for_user(self.user.id)

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/invites/%s' % self.code)
        self.check_and_parse_response(rv, status_code=204,
                                      authenticated=False)

    def test_drop_invite_late_not_found(self):
        invites.auth.admin_client_set() \
                .AndReturn(self.fake_client_set)
        invites.InvitesDAO.get(self.code).AndReturn(self.token)
        user_mgr = self.fake_client_set.identity_admin.users
        user_mgr.get(self.user.id).AndReturn(self.user)
        self.user.delete()\
                .AndRaise(osc_exc.NotFound('gone'))
        self.mox.ReplayAll()
        rv = self.client.delete('/v1/invites/%s' % self.code)
        self.check_and_parse_response(rv, status_code=404,
                                      authenticated=False)


class AuthenticatedInvitesTestCase(TestCase):

    def test_no_root(self):
        rv = self.client.get('/v1/invites/')
        self.check_and_parse_response(rv, status_code=404)

