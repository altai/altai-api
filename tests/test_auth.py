
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

from flask import Flask, g
from base64 import b64encode

from openstackclient_base.exceptions import Unauthorized, Forbidden

from mox import MoxTestBase, IsA
from tests.mocked import MockedTestCase
from tests import doubles

from altai_api import auth
from altai_api.utils.decorators import (no_auth_endpoint,
                                        user_endpoint,
                                        admin_endpoint)


def _basic_auth(username, password):
    return 'Basic %s' % (
        b64encode('%s:%s' % (username, password))
    )


class AuthClientSetTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(AuthClientSetTestCase, self).setUp()
        self.mox.StubOutClassWithMocks(auth, 'ClientSet')
        self.app.config['KEYSTONE_URI'] = 'test_auth_uri'

    def mock_client_set(self):
        self.client = auth.ClientSet(username='u$3R',
                                     password='p@ssw0rd',
                                     auth_uri='test_auth_uri',
                                     tenant_id=None,
                                     token=None,
                                     tenant_name='test_tenant')
        self.client.http_client = self.mox.CreateMockAnything()
        return self.client.http_client.authenticate()

    def test_auth_client_set(self):
        self.mock_client_set()
        self.mox.ReplayAll()

        with self.app.test_request_context():
            cs = auth._client_set('u$3R', 'p@ssw0rd',
                                  tenant_name='test_tenant')
            self.assertEquals(cs, self.client)

    def test_auth_client_set_by_id(self):
        self.client = auth.ClientSet(username='u$3R',
                                     password='p@ssw0rd',
                                     auth_uri='test_auth_uri',
                                     tenant_name=None,
                                     token=None,
                                     tenant_id='PID')
        self.client.http_client = self.mox.CreateMockAnything()
        self.client.http_client.authenticate()

        self.mox.ReplayAll()
        with self.app.test_request_context():
            cs = auth._client_set('u$3R', 'p@ssw0rd', tenant_id='PID')
            self.assertEquals(cs, self.client)

    def test_auth_failure(self):
        self.mock_client_set().AndRaise(Unauthorized('fail'))
        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.assertRaises(Unauthorized, auth._client_set,
                              'u$3R', 'p@ssw0rd', tenant_name='test_tenant')

    def test_auth_ioerror(self):
        self.mock_client_set().AndRaise(IOError('IO ERROR'))
        self.mox.ReplayAll()

        with self.app.test_request_context():
            self.assertRaises(RuntimeError, auth._client_set,
                              'u$3R', 'p@ssw0rd', tenant_name='test_tenant')


class AuthenticationTestCase(MockedTestCase):
    FAKE_AUTH = False
    url = '/non/existant'

    def setUp(self):
        super(AuthenticationTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, '_client_set')
        self.mox.StubOutWithMock(auth, 'admin_role_id')

    def test_no_headers_401(self):
        self.mox.ReplayAll()
        rv = self.client.get(self.url)
        self.check_and_parse_response(rv, status_code=401,
                                      authenticated=False)
        self.assertTrue('X-GD-Altai-Implementation' not in rv.headers)
        auth_hdr = rv.headers.get('WWW-Authenticate', '')
        self.assertTrue(auth_hdr.startswith('Basic '),
                        'Bad WWW-Authenticate header: %r' % auth_hdr)

    def test_success(self):
        user, password = 'u$3R', 'p@ssw0rd'
        self.fake_client_set = self._fake_client_set_factory()

        auth._client_set(user, password, tenant_name='systenant') \
                .AndReturn(self.fake_client_set)
        auth.admin_role_id(self.fake_client_set).AndReturn('AR_ID')
        self.mox.ReplayAll()

        rv = self.client.get(self.url, headers={
            'Authorization': _basic_auth(user, password)
        })
        self.check_and_parse_response(rv, status_code=404)

    def test_failure(self):
        user, password = 'u$3R', 'p@ssw0rd'
        auth._client_set(user, password, tenant_name='systenant') \
                .AndRaise(Unauthorized('denied'))
        auth._client_set(user, password) \
                .AndRaise(Unauthorized('denied'))
        self.mox.ReplayAll()

        rv = self.client.get(self.url, headers={
            'Authorization': _basic_auth(user, password)
        })
        self.check_and_parse_response(rv, status_code=403,
                                      authenticated=False)
        self.assertTrue('WWW-Authenticate' not in rv.headers)


class CurrentUserIdTestCase(MockedTestCase):

    def test_current_user_id(self):
        self.mox.ReplayAll()
        self.fake_client_set.http_client.access['user'] = { 'id' : 'THE_UID' }
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertEquals('THE_UID', auth.current_user_id())

    def test_current_user_id_aborts(self):
        self.mox.ReplayAll()
        del self.fake_client_set.http_client.access['user']
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(403, auth.current_user_id)


class CurrentUserProjectIds(MockedTestCase):

    def test_current_user_project_ids_no_auth(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            # we don't install fake auth, so user is not authenticated
            ids = auth.current_user_project_ids()
            self.assertEquals(ids, set())

    def test_current_user_project_ids(self):
        tenants = [doubles.make(self.mox, doubles.Tenant, id='PID1'),
                   doubles.make(self.mox, doubles.Tenant, id='PID2')]
        self.fake_client_set.identity_public.tenants.list() \
                .AndReturn(tenants)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            ids = auth.current_user_project_ids()
            self.assertEquals(ids, set(('PID1', 'PID2')))


def make_test_app():
    test_app = Flask(__name__)
    test_app.config['DEFAULT_TENANT'] = 'test_default_tenant'

    @test_app.before_request
    def test_check():
        g.audit_data = {}
        auth.require_auth()

    @test_app.errorhandler(500)
    def error(error):
        return str(error), 500

    return test_app


class NoAuthEndpointTestCase(MoxTestBase):

    def setUp(self):
        super(NoAuthEndpointTestCase, self).setUp()
        self.test_app = make_test_app()

        @self.test_app.route('/hello')
        @no_auth_endpoint
        def hello_():
            assert not g.is_admin
            return 'hello, world!'

    def test_no_auth_endpoint(self):
        self.mox.ReplayAll()
        with self.test_app.test_request_context('/hello'):
            result = auth.require_auth()
            self.assertEquals(result, None)
            self.assertEquals(g.client_set, None)

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

        self.mox.ReplayAll()
        rv = self.test_app.test_client().get('/cu')
        self.assertEquals(rv.status_code, 500)
        self.assertTrue('No current user' in rv.data)


class UserEndpointTestCase(MoxTestBase):

    def setUp(self):
        super(UserEndpointTestCase, self).setUp()
        self.test_app = make_test_app()

        @self.test_app.route('/hello')
        @user_endpoint
        def hello_():
            assert g.audit_data['user_id'] == 'FAKE_UID'
            assert g.client_set == 'FAKE_CLIENT_SET'
            return 'hello, world!'

        self.mox.StubOutWithMock(auth, '_client_set')
        self.mox.StubOutWithMock(auth, 'admin_role_id')
        self.mox.StubOutWithMock(auth, 'current_user_id')

    def test_user_endpoint_no_auth(self):
        self.mox.ReplayAll()
        rv = self.test_app.test_client().get('/hello')
        self.assertEquals(rv.status_code, 401, rv.data)

    def test_user_endpoint_as_user(self):
        user, password = 'u$3R', 'p@ssw0rd'
        auth._client_set(user, password, tenant_name='test_default_tenant') \
                .AndRaise(Unauthorized('denied'))
        auth._client_set(user, password) \
                .AndReturn('FAKE_CLIENT_SET')
        auth.admin_role_id('FAKE_CLIENT_SET').AndReturn(None)
        auth.current_user_id().AndReturn('FAKE_UID')
        self.mox.ReplayAll()

        rv = self.test_app.test_client().get(
            '/hello',
            headers={'Authorization': _basic_auth(user, password)}
        )
        self.assertEquals(rv.status_code, 200, rv.data)

    def test_user_endpoint_as_admin(self):
        user, password = 'u$3R', 'p@ssw0rd'
        auth._client_set(user, password, tenant_name='test_default_tenant') \
                .AndReturn('FAKE_CLIENT_SET')
        auth.admin_role_id('FAKE_CLIENT_SET').AndReturn('AR_ID')
        auth.current_user_id().AndReturn('FAKE_UID')
        self.mox.ReplayAll()

        rv = self.test_app.test_client().get(
            '/hello',
            headers={'Authorization': _basic_auth(user, password)}
        )
        self.assertEquals(rv.status_code, 200, rv.data)

    def test_user_endpoint_fail(self):
        user, password = 'u$3R', 'p@ssw0rd'
        auth._client_set(user, password, tenant_name='test_default_tenant') \
                .AndRaise(Unauthorized('denied'))
        auth._client_set(user, password) \
                .AndRaise(Unauthorized('denied'))
        self.mox.ReplayAll()

        rv = self.test_app.test_client().get(
            '/hello',
            headers={'Authorization': _basic_auth(user, password)}
        )
        self.assertEquals(rv.status_code, 403, rv.data)


class AdminEndpointTestCase(MoxTestBase):

    def setUp(self):
        super(AdminEndpointTestCase, self).setUp()
        self.test_app = make_test_app()

        @self.test_app.route('/hello')
        @admin_endpoint
        def hello_():
            assert g.audit_data['user_id'] == 'FAKE_UID'
            assert g.client_set == 'FAKE_CLIENT_SET'
            assert g.admin_client_set == 'FAKE_CLIENT_SET'
            return 'hello, world!'

        self.mox.StubOutWithMock(auth, '_client_set')
        self.mox.StubOutWithMock(auth, 'admin_role_id')
        self.mox.StubOutWithMock(auth, 'current_user_id')

    def test_admin_endpoint_no_auth(self):
        self.mox.ReplayAll()
        rv = self.test_app.test_client().get('/hello')
        self.assertEquals(rv.status_code, 401, rv.data)

    def test_admin_endpoint_ok(self):
        admin, password = '@Dm33n', 'p@ssw0rd'
        auth._client_set(admin, password,
                         tenant_name='test_default_tenant') \
                .AndReturn('FAKE_CLIENT_SET')
        auth.admin_role_id('FAKE_CLIENT_SET').AndReturn('AR_ID')
        auth.current_user_id().AndReturn('FAKE_UID')
        self.mox.ReplayAll()

        rv = self.test_app.test_client().get(
            '/hello',
            headers={'Authorization': _basic_auth(admin, password)}
        )
        self.assertEquals(rv.status_code, 200, rv.data)

    def test_admin_endpoint_fail(self):
        admin, password = '@Dm33n', 'p@ssw0rd'
        auth._client_set(admin, password,
                         tenant_name='test_default_tenant') \
                .AndRaise(Unauthorized('denied'))
        self.mox.ReplayAll()

        rv = self.test_app.test_client().get(
            '/hello',
            headers={'Authorization': _basic_auth(admin, password)}
        )
        self.assertEquals(rv.status_code, 403, rv.data)

    def test_admin_endpoint_no_admin(self):
        admin, password = '@Dm33n', 'p@ssw0rd'
        auth._client_set(admin, password,
                         tenant_name='test_default_tenant') \
                .AndReturn('FAKE_CLIENT_SET')
        auth.admin_role_id('FAKE_CLIENT_SET').AndReturn(None)
        self.mox.ReplayAll()

        rv = self.test_app.test_client().get(
            '/hello',
            headers={'Authorization': _basic_auth(admin, password)}
        )
        self.assertEquals(rv.status_code, 403, rv.data)


class ClientSetForTenantTestCase(MockedTestCase):

    def setUp(self):
        super(ClientSetForTenantTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, 'ClientSet')
        self.mox.StubOutWithMock(auth, 'api_client_set')

    def mock_client_set(self):
        access = self.fake_client_set.http_client.access
        return auth.ClientSet(token=access['token']['id'],
                              tenant_id='PID',
                              tenant_name=None,
                              username=None,
                              password=None,
                              auth_uri=self.app.config['KEYSTONE_URI'])

    def test_client_set_for_tenant_works(self):
        tcs = self._fake_client_set_factory()
        self.mock_client_set().AndReturn(tcs)
        tcs.http_client.authenticate()

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            cs = auth.client_set_for_tenant('PID')
            self.assertEquals(cs, tcs)

    def test_client_set_for_tenant_no_auth(self):
        tcs = self._fake_client_set_factory()
        self.mock_client_set().AndReturn(tcs)
        tcs.http_client.authenticate()\
                .AndRaise(Unauthorized('denied'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(403, auth.client_set_for_tenant, 'PID')

    def test_client_set_for_tenant_fallback(self):
        tcs = self._fake_client_set_factory()
        self.mock_client_set().AndReturn(tcs)
        tcs.http_client.authenticate()\
                .AndRaise(Unauthorized('denied'))
        auth.api_client_set('PID').AndReturn('REPLY')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = auth.client_set_for_tenant('PID',
                                                fallback_to_api=True)
        self.assertEquals('REPLY', result)

    def test_client_set_for_tenant_forbidden(self):
        tcs = self._fake_client_set_factory()
        self.mock_client_set().AndReturn(tcs)
        tcs.http_client.authenticate()\
                .AndRaise(Forbidden('denied'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            ex = self.assertAborts(403, auth.client_set_for_tenant, 'PID')
            self.assertEquals(str(ex), "You are not member of project 'PID'")
            self.assertEquals(ex.exc_type, 'AdministratorIsNotMemberOfTenant')

    def test_client_set_for_tenant_forbidden_no_admin(self):
        tcs = self._fake_client_set_factory()
        self.mock_client_set().AndReturn(tcs)
        tcs.http_client.authenticate()\
                .AndRaise(Forbidden('denied'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            g.is_admin = False
            ex = self.assertAborts(403, auth.client_set_for_tenant, 'PID')
            self.assertNotEquals(getattr(ex, 'exc_type', None),
                                 'AdministratorIsNotMemberOfTenant')


class AdminClientSetTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(AdminClientSetTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, '_client_set')
        self.mox.StubOutWithMock(auth, 'admin_role_id')
        self.app.config['KEYSTONE_ADMIN'] = 'test_admin'
        self.app.config['DEFAULT_TENANT'] = 'test_default_tenant'
        self.app.config['KEYSTONE_ADMIN_PASSWORD'] = 'test_p@ssw0rd'

    def test_admin_client_set_works(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_name='test_default_tenant')\
                .AndReturn('FAKE_CLIENT_SET')
        auth.admin_role_id('FAKE_CLIENT_SET').AndReturn('AR_ID')
        self.mox.ReplayAll()
        with self.app.test_request_context():
            cs = auth.admin_client_set()
            self.assertEquals(cs, 'FAKE_CLIENT_SET')
            self.assertEquals(g.admin_client_set, 'FAKE_CLIENT_SET')

    def test_admin_client_set_failure(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_name='test_default_tenant')\
                .AndRaise(Unauthorized('denied'))
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.assertRaises(RuntimeError, auth.admin_client_set)

    def test_admin_client_set_no_admin(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_name='test_default_tenant')\
                .AndReturn('FAKE_CLIENT_SET')
        auth.admin_role_id('FAKE_CLIENT_SET').AndReturn(None)
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.assertRaises(RuntimeError, auth.admin_client_set)

    def test_admin_client_set_cached(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            g.admin_client_set = 'FAKE_CLIENT_SET'
            cs = auth.admin_client_set()
            self.assertEquals(cs, 'FAKE_CLIENT_SET')


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
            g.is_admin = False
            self.assertEquals(None, auth.admin_role_id())
            self.assertAborts(403, auth.assert_admin)

    def test_admin_or_project_user(self):
        # make roles empty
        self.fake_client_set.http_client.access['user']['roles'] = []

        self.fake_client_set.identity_public.tenants.list() \
                .AndReturn([])

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            g.is_admin = False
            self.assertAborts(
                418, auth.assert_admin_or_project_user, 'PID', 418)

    def test_with_my_client_set(self):
        result = auth.admin_role_id(self.fake_client_set)
        # look at tests/mocked.py, near line 100
        self.assertEquals(result, u'ADMIN_ROLE_ID')


class AddApiSuperUserToProjectTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(AddApiSuperUserToProjectTestCase, self).setUp()
        self.mox.StubOutWithMock(self.app.logger, 'exception')
        self.mox.StubOutWithMock(auth, 'api_client_set')

    def test_add_api_superuser_to_project_works(self):
        tcs = self._fake_client_set_factory()
        tcs.http_client.access['user'] = {
            'id': 'API_SU_UID',
            'roles': [ { 'id': 'AR_ID', 'name': 'admin' } ]
        }

        auth.api_client_set().AndReturn(tcs)
        tcs.identity_admin.roles.add_user_role('API_SU_UID', 'AR_ID', 'PID')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            auth.add_api_superuser_to_project('PID')

    def test_add_api_superuser_to_project_logs_error(self):
        auth.api_client_set().AndRaise(RuntimeError('catch me'))
        self.app.logger.exception(IsA(basestring), 'PID', IsA(RuntimeError))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            auth.add_api_superuser_to_project('PID')


class ApiClientSetTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(ApiClientSetTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, '_client_set')
        self.mox.StubOutWithMock(auth, 'admin_role_id')
        self.mox.StubOutWithMock(auth, 'add_api_superuser_to_project')
        self.app.config['DEFAULT_TENANT'] = 'test_default_tenant'
        self.app.config['KEYSTONE_ADMIN'] = 'test_admin'
        self.app.config['KEYSTONE_ADMIN_PASSWORD'] = 'test_p@ssw0rd'

    def test_api_cs_for_admin(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_name='test_default_tenant') \
                .AndReturn('FAKE_CS')
        auth.admin_role_id('FAKE_CS').AndReturn('ROLE')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            cs = auth.api_client_set()
        self.assertEquals(cs, 'FAKE_CS')

    def test_api_cs_for_admin_denied(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_name='test_default_tenant') \
                .AndRaise(Unauthorized('denied'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.assertRaises(RuntimeError, auth.api_client_set)

    def test_api_cs_for_project(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_id='PID') \
                .AndReturn('FAKE_CS')
        auth.admin_role_id('FAKE_CS').AndReturn('ROLE')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            cs = auth.api_client_set('PID')
        self.assertEquals(cs, 'FAKE_CS')

    def test_api_cs_for_project_denied_at_first(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_id='PID') \
                .AndRaise(Unauthorized('denied'))
        auth.add_api_superuser_to_project('PID')
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_id='PID') \
                .AndReturn('FAKE_CS')
        auth.admin_role_id('FAKE_CS').AndReturn('ROLE')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            cs = auth.api_client_set('PID')
        self.assertEquals(cs, 'FAKE_CS')

    def test_api_cs_for_project_denied_at_last(self):
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_id='PID') \
                .AndRaise(Unauthorized('denied'))
        auth.add_api_superuser_to_project('PID')
        auth._client_set('test_admin', 'test_p@ssw0rd',
                         tenant_id='PID') \
                .AndReturn('FAKE_CS')
        auth.admin_role_id('FAKE_CS').AndReturn(None)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.assertRaises(RuntimeError, auth.api_client_set, 'PID')


class BoundClientSetTestCase(MockedTestCase):

    def setUp(self):
        super(BoundClientSetTestCase, self).setUp()
        self.mox.StubOutWithMock(auth, 'client_set_for_tenant')

    def test_bound_client_admin(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertEquals(auth.bound_client_set(), g.client_set)

    def test_bound_client_user(self):
        # pretend we have unbound client set:
        self.fake_client_set.http_client.access['user']['roles'] = []
        tenants = [doubles.make(self.mox, doubles.Tenant, id='PID1'),
                   doubles.make(self.mox, doubles.Tenant, id='PID2')]

        self.fake_client_set.identity_public.tenants.list() \
                .AndReturn(tenants)
        auth.client_set_for_tenant('PID1').AndReturn('FAKE_CS')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertEquals(auth.bound_client_set(), 'FAKE_CS')

    def test_bound_client_user_no_projects(self):
        # pretend we have unbound client set:
        self.fake_client_set.http_client.access['user']['roles'] = []
        self.fake_client_set.identity_public.tenants.list() \
                .AndReturn([])

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            self.assertAborts(403, auth.bound_client_set)

