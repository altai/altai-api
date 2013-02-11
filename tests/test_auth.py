
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
from base64 import b64encode

from openstackclient_base.exceptions import Unauthorized

from mox import MoxTestBase
from tests.mocked import MockedTestCase

from altai_api import auth
from altai_api.utils.decorators import no_auth_endpoint


def _basic_auth(username, password):
    return 'Basic %s' % (
        b64encode('%s:%s' % (username, password))
    )


class KeystoneAuthTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(KeystoneAuthTestCase, self).setUp()

        self.mox.StubOutClassWithMocks(auth, 'ClientSet')
        self.client = auth.ClientSet(username='u$3R',
                                     password='p@ssw0rd',
                                     auth_uri='test_auth_uri',
                                     tenant_name='test_default_tenant')
        self.client.http_client = self.mox.CreateMockAnything()
        self.app.config['DEFAULT_TENANT'] = 'test_default_tenant'
        self.app.config['KEYSTONE_URI'] = 'test_auth_uri'

    def test_keystone_auth(self):
        self.client.http_client.authenticate()
        self.mox.ReplayAll()

        with self.app.test_request_context():
            auth.keystone_auth('u$3R', 'p@ssw0rd')
            self.assertTrue(auth.is_authenticated())

    def test_keystone_auth_failure(self):
        self.client.http_client.authenticate().AndRaise(Unauthorized('fail'))

        self.mox.ReplayAll()

        with self.app.test_request_context():
            result = auth.keystone_auth('u$3R', 'p@ssw0rd')
            self.assertEquals(False, result)
            self.assertFalse(auth.is_authenticated())

    def test_keystone_auth_ioerror(self):
        self.client.http_client.authenticate().AndRaise(IOError('IO ERROR'))

        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.assertRaises(RuntimeError,
                              auth.keystone_auth, 'u$3R', 'p@ssw0rd')
            self.assertFalse(auth.is_authenticated())


class AuthenticationTestCase(MockedTestCase):
    FAKE_AUTH = False

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


class CurrentUserIdTestCase(MockedTestCase):

    def test_current_user_id(self):
        self.fake_client_set.http_client.access['user'] = { 'id' : 'THE_UID' }
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertEquals('THE_UID', auth.current_user_id())

    def test_current_user_id_aborts(self):
        del self.fake_client_set.http_client.access['user']
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(403, auth.current_user_id)


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

    def test_no_auth_request_no_rule(self):
        self.test_app.before_request(auth.require_auth)

        self.mox.ReplayAll()
        rv = self.test_app.test_client().get('/non/existing/resource')
        # no rule found, so we have to authorize as usual
        self.assertEquals(rv.status_code, 401)

    def test_no_auth_request_no_current_user(self):
        self.test_app.before_request(auth.require_auth)

        @self.test_app.route('/cu')
        @no_auth_endpoint
        def current_user_():
            return auth.current_user_id()

        @self.test_app.errorhandler(500)
        def error_handler_(error):
            return str(error), 500

        auth.keystone_auth('admin', 'admin_pw').AndReturn(True)
        self.mox.ReplayAll()
        rv = self.test_app.test_client().get('/cu')
        self.assertEquals(rv.status_code, 500)
        self.assertTrue('No current user' in rv.data)


class ClientSetForTenantTestCase(MockedTestCase):

    def setUp(self):
        super(ClientSetForTenantTestCase, self).setUp()
        self.mox.StubOutClassWithMocks(auth, 'ClientSet')

    def test_client_set_for_tenant_works(self):
        access = self.fake_client_set.http_client.access
        auth.ClientSet(token=access['token']['id'],
                       tenant_name=None,
                       tenant_id='PID',
                       auth_uri=self.app.config['KEYSTONE_URI'])\

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            auth.client_set_for_tenant('PID')

    def test_needs_something(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertRaises(ValueError, auth.client_set_for_tenant)


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
            self.assertAborts(403, auth.admin_role_id)

    def test_assert_admin_403(self):
        # make roles empty
        self.fake_client_set.http_client.access['user']['roles'] = []

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(403, auth.assert_admin)

