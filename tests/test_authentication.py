
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

from mox import MoxTestBase
from tests import TestCase
from flask import g
from base64 import b64encode
from openstackclient_base.exceptions import Unauthorized
import altai_api.authentication as _A


def _basic_auth(username, password):
    return 'Basic %s' % (
        b64encode('%s:%s' % (username, password))
    )

class AuthenticationTestCase(TestCase, MoxTestBase):

    def test_keystone_authorize(self):
        self.mox.StubOutClassWithMocks(_A, 'HttpClient')
        client = _A.HttpClient(username='u$3R',
                               password='p@ssw0rd',
                               auth_uri='test_auth_uri')
        client.authenticate()
        self.mox.ReplayAll()

        self.app.config['KEYSTONE_URI'] = 'test_auth_uri'
        with self.app.test_request_context():
            _A.keystone_authorize('u$3R', 'p@ssw0rd')
            self.assertTrue(hasattr(g, 'http_client'))


    def test_no_headers_401(self):
        self.app.config['AUTHORIZATION_MODE'] = 'keystone'
        rv = self.client.get('/')
        self.assertEquals(rv.status_code, 401)
        self.assertTrue('X-GD-Altai-Implementation' not in rv.headers)
        auth_hdr = rv.headers.get('WWW-Authenticate', '')
        self.assertTrue(auth_hdr.startswith('Basic '),
                        'Bad WWW-Authenticate header: %r' % auth_hdr)

    def test_success(self):
        self.mox.StubOutWithMock(_A, 'keystone_authorize')
        _A.keystone_authorize('u$3R', 'p@ssw0rd').AndReturn(True)
        self.app.config['AUTHORIZATION_MODE'] = 'keystone'
        self.mox.ReplayAll()

        rv = self.client.get('/', headers={
            'Authorization': _basic_auth('u$3R', 'p@ssw0rd')
        })
        self.check_and_parse_response(rv)

    def test_bad_auth(self):
        self.app.config['AUTHORIZATION_MODE'] = 'invalid value'
        rv = self.client.get('/')
        self.assertEquals(rv.status_code, 500,
                          'Expeceted response %s, got %s, with: %s' %(
                              500, rv.status_code, rv.data
                          ))
        self.assertTrue('WWW-Authenticate' not in rv.headers)
        self.assertTrue('traceback' not in rv.data)



    def test_failure(self):
        self.mox.StubOutWithMock(_A, 'keystone_authorize')
        _A.keystone_authorize('u$3R', 'p@ssw0rd').AndRaise(Unauthorized(None))
        self.app.config['AUTHORIZATION_MODE'] = 'keystone'
        self.mox.ReplayAll()

        rv = self.client.get('/', headers={
            'Authorization': _basic_auth('u$3R', 'p@ssw0rd')
        })
        self.assertEquals(rv.status_code, 403,
                          'Expeceted response %s, got %s, with: %s' %(
                              403, rv.status_code, rv.data
                          ))
        self.assertTrue('X-GD-Altai-Implementation' not in rv.headers)
        self.assertTrue('WWW-Authenticate' not in rv.headers)


