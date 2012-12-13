
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

from flask import exceptions as flask_exc
from base64 import b64encode

from openstackclient_base.exceptions import Unauthorized

from tests.mocked import MockedTestCase
import altai_api.authentication as _A


def _basic_auth(username, password):
    return 'Basic %s' % (
        b64encode('%s:%s' % (username, password))
    )


class Auth(object):
    """Fake auth for  keystone_auth()"""
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __eq__(self, other):
        return (self.username == other.username
                and self.password == other.password)


class AuthenticationTestCase(MockedTestCase):
    FAKE_AUTH = False

    def test_keystone_auth(self):
        self.mox.StubOutClassWithMocks(_A, 'ClientSet')
        client = _A.ClientSet(username='u$3R',
                              password='p@ssw0rd',
                              auth_uri='test_auth_uri',
                              tenant_name='test_default_tenant')
        client.http_client = self.mox.CreateMockAnything()
        client.http_client.authenticate()
        self.mox.ReplayAll()

        self.app.config['DEFAULT_TENANT'] = 'test_default_tenant'
        self.app.config['KEYSTONE_URI'] = 'test_auth_uri'
        with self.app.test_request_context():
            _A.keystone_auth(Auth('u$3R', 'p@ssw0rd'))
            self.assertTrue(_A.is_authenticated())


    def test_no_headers_401(self):
        rv = self.client.get('/')
        self.check_and_parse_response(rv, status_code=401)
        self.assertTrue('X-GD-Altai-Implementation' not in rv.headers)
        auth_hdr = rv.headers.get('WWW-Authenticate', '')
        self.assertTrue(auth_hdr.startswith('Basic '),
                        'Bad WWW-Authenticate header: %r' % auth_hdr)

    def test_success(self):
        self.mox.StubOutWithMock(_A, 'keystone_auth')
        _A.keystone_auth(Auth('u$3R', 'p@ssw0rd')) \
                .WithSideEffects(self.install_fake_auth) \
                .AndReturn(True)
        self.mox.ReplayAll()

        rv = self.client.get('/', headers={
            'Authorization': _basic_auth('u$3R', 'p@ssw0rd')
        })
        self.check_and_parse_response(rv)

    def test_failure(self):
        auth = Auth('u$3R', 'p@ssw0rd')
        self.mox.StubOutWithMock(_A, 'keystone_auth')
        _A.keystone_auth(auth).AndRaise(Unauthorized(None))
        self.mox.ReplayAll()

        rv = self.client.get('/', headers={
            'Authorization': _basic_auth('u$3R', 'p@ssw0rd')
        })
        self.check_and_parse_response(rv, status_code=403)
        self.assertTrue('WWW-Authenticate' not in rv.headers)


class AuthInfoTestCase(MockedTestCase):

    def test_default_tenant_id(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = _A.default_tenant_id()
        # look at tests/mocked.py, near line 100
        self.assertEquals(result, u'SYSTENANT_ID')

    def test_admin_role_id(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = _A.admin_role_id()
        # look at tests/mocked.py, near line 100
        self.assertEquals(result, u'ADMIN_ROLE_ID')

    def test_admin_role_id_403(self):
        # make roles empty
        self.fake_client_set.http_client.access['user']['roles'] = []

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            try:
                _A.admin_role_id()
            except flask_exc.HTTPException, e:
                self.assertEquals(e.code, 403)
            else:
                self.fail('Exception was not raised')

