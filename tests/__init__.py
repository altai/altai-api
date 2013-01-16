
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

import os
import sys
import unittest
import altai_api.main
import altai_api.authentication as auth
from flask import g, json


_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')


def scrpit_path(name):
    return os.path.join(_SCRIPTS_DIR, name)


class TestCase(unittest.TestCase):
    FAKE_AUTH = True

    def _fake_client_set_factory(self):
        class _Fake(object):
            master = self
        return _Fake()

    def install_fake_auth(self, *args_):
        if not hasattr(self, 'fake_client_set'):
            self.fake_client_set = self._fake_client_set_factory()
        g.client_set = self.fake_client_set
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

    def check_and_parse_response(self, resp, status_code=200):
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
        if hasattr(self, 'fake_client_set'):
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

