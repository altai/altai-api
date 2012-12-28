
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

from flask import Flask
from flask import exceptions as flask_exc
from base64 import b64encode

from openstackclient_base.exceptions import Unauthorized

from mox import MoxTestBase
from tests.mocked import MockedTestCase

from altai_api import authentication as auth
from altai_api.utils.decorators import no_auth_endpoint


def _basic_auth(username, password):
    return 'Basic %s' % (
        b64encode('%s:%s' % (username, password))
    )


class AuthenticationTestCase(MockedTestCase):
    FAKE_AUTH = False

    def test_keystone_auth(self):
        self.mox.StubOutClassWithMocks(auth, 'ClientSet')
        client = auth.ClientSet(username='u$3R',
                              password='p@ssw0rd',
                              auth_uri='test_auth_uri',
                              tenant_name='test_default_tenant')
        client.http_client = self.mox.CreateMockAnything()
        client.http_client.authenticate()
        self.mox.ReplayAll()

        self.app.config['DEFAULT_TENANT'] = 'test_default_tenant'
        self.app.config['KEYSTONE_URI'] = 'test_auth_uri'
        with self.app.test_request_context():
            auth.keystone_auth('u$3R', 'p@ssw0rd')
            self.assertTrue(auth.is_authenticated())

    def test_keystone_auth_failure(self):
        self.mox.StubOutClassWithMocks(auth, 'ClientSet')
        client = auth.ClientSet(username='u$3R',
                              password='p@ssw0rd',
                              auth_uri='test_auth_uri',
                              tenant_name='test_default_tenant')
        client.http_client = self.mox.CreateMockAnything()
        client.http_client.authenticate().AndRaise(Unauthorized('fail'))

        self.mox.ReplayAll()

        self.app.config['DEFAULT_TENANT'] = 'test_default_tenant'
        self.app.config['KEYSTONE_URI'] = 'test_auth_uri'
        with self.app.test_request_context():
            result = auth.keystone_auth('u$3R', 'p@ssw0rd')
            self.assertEquals(False, result)
            self.assertFalse(auth.is_authenticated())

    def test_no_headers_401(self):
        self.mox.ReplayAll()
        rv = self.client.get('/')
        self.check_and_parse_response(rv, status_code=401)
        self.assertTrue('X-GD-Altai-Implementation' not in rv.headers)
        auth_hdr = rv.headers.get('WWW-Authenticate', '')
        self.assertTrue(auth_hdr.startswith('Basic '),
                        'Bad WWW-Authenticate header: %r' % auth_hdr)

    def test_success(self):
        user, password = 'u$3R', 'p@ssw0rd'
        self.mox.StubOutWithMock(auth, 'keystone_auth')
        auth.keystone_auth(user, password) \
                .WithSideEffects(self.install_fake_auth) \
                .AndReturn(True)
        self.mox.ReplayAll()

        rv = self.client.get('/', headers={
            'Authorization': _basic_auth(user, password)
        })
        self.check_and_parse_response(rv)

    def test_failure(self):
        user, password = 'u$3R', 'p@ssw0rd'
        self.mox.StubOutWithMock(auth, 'keystone_auth')
        auth.keystone_auth(user, password).AndReturn(False)
        self.mox.ReplayAll()

        rv = self.client.get('/', headers={
            'Authorization': _basic_auth(user, password)
        })
        self.check_and_parse_response(rv, status_code=403)
        self.assertTrue('WWW-Authenticate' not in rv.headers)


class NoAuthEndpointTestCase(MoxTestBase):

    def setUp(self):
        super(NoAuthEndpointTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, 'keystone_auth')

        self.test_app = Flask(__name__)
        self.test_app.config['KEYSTONE_ADMIN'] = 'admin'
        self.test_app.config['KEYSTONE_ADMIN_PASSWORD'] = 'admin_pw'

        @self.test_app.route('/')
        @no_auth_endpoint
        def hello_():
            return 'hello, world!'

    def test_no_auth_endpoint(self):
        auth.keystone_auth('admin', 'admin_pw').AndReturn(True)

        self.mox.ReplayAll()
        with self.test_app.test_request_context():
            result = auth.require_auth()
            self.assertEquals(result, None)

    def test_no_auth_endpoint_fail(self):
        auth.keystone_auth('admin', 'admin_pw').AndReturn(False)

        self.mox.ReplayAll()
        with self.test_app.test_request_context():
            self.assertRaises(RuntimeError, auth.require_auth)


class AuthInfoTestCase(MockedTestCase):

    def test_default_tenant_id(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = auth.default_tenant_id()
        # look at tests/mocked.py, near line 100
        self.assertEquals(result, u'SYSTENANT_ID')

    def test_admin_role_id(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = auth.admin_role_id()
        # look at tests/mocked.py, near line 100
        self.assertEquals(result, u'ADMIN_ROLE_ID')

    def test_admin_role_id_403(self):
        # make roles empty
        self.fake_client_set.http_client.access['user']['roles'] = []

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            try:
                auth.admin_role_id()
            except flask_exc.HTTPException, e:
                self.assertEquals(e.code, 403)
            else:
                self.fail('Exception was not raised')

