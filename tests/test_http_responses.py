
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

import flask

from tests import TestCase
from altai_api import error_handlers

class HttpResponsesTestCase(TestCase):
    def test_404(self):
        rv = self.client.get('/i-hope-this-resource-will-never-exist')
        self.check_and_parse_response(rv, status_code=404)


class ErrorHandlersTestCase(TestCase):
    def test_unauthorized_500(self):
        with self.app.test_request_context():
            # create exception context for test
            try:
                raise RuntimeError('Test message')
            except RuntimeError, ex:
                resp = self.app.make_response(
                    error_handlers.exception_handler(ex))
        self.assertEqual(resp.status_code, 500)
        self.assertTrue('X-GD-Altai-Implementation' not in resp.headers)
        self.assertTrue('Test message' in resp.data)

    def test_authorized_500_other_error(self):
        with self.app.test_request_context():
            resp = self.app.make_response(
                error_handlers.exception_handler(RuntimeError('Test message')))
        self.assertEqual(resp.status_code, 500)
        self.assertTrue('X-GD-Altai-Implementation' not in resp.headers)
        self.assertTrue('Test message' in resp.data)

    def test_authorized_500(self):
        with self.app.test_request_context():
            # fake authorized conetxt
            flask.g.http_client = None
            # create exception context for test
            try:
                raise RuntimeError('Test message')
            except RuntimeError, ex:
                resp = self.app.make_response(
                    error_handlers.exception_handler(ex))
        data = self.check_and_parse_response(resp, status_code=500)
        self.assertTrue('Test message' in data.get('message', ''))
        self.assertTrue(isinstance(data.get('traceback'), list))

    def test_authorized_500_other_error(self):
        with self.app.test_request_context():
            # fake authorized conetxt
            flask.g.http_client = None
            resp = self.app.make_response(
                error_handlers.exception_handler(RuntimeError('Test message')))
        data = self.check_and_parse_response(resp, status_code=500)
        self.assertTrue('Test message' in data.get('message', ''))
        self.assertTrue('traceback' not in data)




