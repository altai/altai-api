
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
import unittest
import altai_api.main
import altai_api.authentication as _A
from flask import g, json


_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')


def scrpit_path(name):
    return os.path.join(_SCRIPTS_DIR, name)


class _Fake(object):
    pass


class TestCase(unittest.TestCase):
    FAKE_AUTH = True

    def __keystone_auth_test_double(self, auth_):
        self.install_fake_auth()
        return True

    def _fake_client_set_factory(self):
        return _Fake()

    def install_fake_auth(self, auth_=None):
        if not hasattr(self, 'fake_client_set'):
            self.fake_client_set = self._fake_client_set_factory()
        g.client_set = self.fake_client_set

    def setUp(self):
        super(TestCase, self).setUp()
        self.app = altai_api.main.app
        self.client = self.app.test_client()
        self.__config = self.app.config
        self.app.config = self.app.config.copy()
        if self.FAKE_AUTH:
            self.fake_client_set = self._fake_client_set_factory()
            self.__keystone_auth = _A.keystone_auth
            _A.keystone_auth = self.__keystone_auth_test_double

    def tearDown(self):
        if hasattr(self, 'fake_client_set'):
            del self.fake_client_set
        if self.FAKE_AUTH:
            _A.keystone_auth = self.__keystone_auth
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

