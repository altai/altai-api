
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

import sys
import unittest

from flask import g, json
from flask.exceptions import HTTPException

import altai_api.main
from altai_api import auth
from altai_api import exceptions as exc


class TestCase(unittest.TestCase):
    FAKE_AUTH = True
    # by default, pretend to be admin
    IS_ADMIN = True

    def _fake_client_set_factory(self):
        class _Fake(object):
            master = self
        return _Fake()

    def install_fake_auth(self, *args_):
        if not hasattr(self, 'fake_client_set'):
            self.fake_client_set = self._fake_client_set_factory()
        g.client_set = self.fake_client_set
        g.admin_client_set = self.fake_client_set
        g.is_admin = self.IS_ADMIN
        g.my_projects = not self.IS_ADMIN
        return None

    def setUp(self):
        super(TestCase, self).setUp()
        self.app = altai_api.main.app
        self.client = self.app.test_client()
        self.__config = self.app.config
        self.app.config = self.app.config.copy()
        self.app.config['AUDIT_VERBOSITY'] = 0
        if self.FAKE_AUTH:
            self.fake_client_set = self._fake_client_set_factory()
            self.__require_auth = auth.require_auth
            auth.require_auth = self.install_fake_auth

    def tearDown(self):
        if hasattr(self, 'fake_client_set'):
            del self.fake_client_set
        if self.FAKE_AUTH:
            auth.require_auth = self.__require_auth
        self.app.config = self.__config

    def assertAborts(self, status_code, callable_obj, *args, **kwargs):
        """Check that callable raises HTTP exception with given code"""
        try:
            callable_obj(*args, **kwargs)
        except HTTPException, ex:
            self.assertEquals(ex.code, status_code,
                              "Bad HTTP status code: expected %s, got %s"
                              % (status_code, ex.code))
            return ex
        except exc.AltaiApiException, ex:
            self.assertEquals(ex.status_code, status_code,
                              "Bad HTTP status code: expected %s, got %s"
                              % (status_code, ex.status_code))
            return ex
        else:
            self.fail("HTTPException was not raised")

    def check_and_parse_response(self, resp, status_code=200,
                                 authenticated=True):
        try:
            if resp.data:
                data = json.loads(resp.data)
            else:
                data = None
        except Exception:
            self.fail('Invalid response data: %r' % resp.data)

        self.assertEquals(resp.status_code, status_code,
                          'Expected HTTP response %s but got %s, with: %s' % (
                              status_code, resp.status_code,
                              json.dumps(data, indent=4, sort_keys=True)))
        self.assertEquals(resp.content_type, 'application/json')
        if authenticated:
            self.assertTrue('X-GD-Altai-Implementation' in resp.headers)
        else:
            self.assertTrue('X-GD-Altai-Implementation' not in resp.headers)

        if status_code == 204:
            self.assertEquals(data, None)

        return data


class ContextWrappedTestCase(TestCase):
    """Wraps all tests with request context"""

    def setUp(self):
        super(ContextWrappedTestCase, self).setUp()
        self.__context = self.app.test_request_context()
        self.__context.__enter__()
        if self.FAKE_AUTH:
            self.install_fake_auth()

    def tearDown(self):
        self.__context.__exit__(*sys.exc_info())
        super(ContextWrappedTestCase, self).tearDown()

