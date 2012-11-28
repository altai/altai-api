
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
from mox import MoxTestBase

from tests import TestCase

from altai_api import error_handlers
from altai_api.exceptions import (
    InvalidRequest, MissingElement, IllegalValue, UnknownElement)



class HttpResponsesTestCase(TestCase):
    def test_404(self):
        rv = self.client.get('/i-hope-this-resource-will-never-exist')
        self.check_and_parse_response(rv, status_code=404)

    def test_illegal_value(self):
        error = IllegalValue(name='test', typename='uint', value='-42')
        with self.app.test_request_context('/test/path'):
            rv = self.app.make_response(
                error_handlers.illegal_value_handler(error))
            data = self.check_and_parse_response(rv, status_code=400)
            self.assertEquals(data, {
                u'path': u'/test/path',
                u'method': u'GET',
                u'message': u'Illegal value for resource element.',
                u'element-name': u'test',
                u'element-value': u'-42',
                u'element-type': u'uint'
            })

    def test_missing_element(self):
        error = MissingElement(name='test')
        with self.app.test_request_context('/test/path'):
            rv = self.app.make_response(
                error_handlers.missing_element_handler(error))
            data = self.check_and_parse_response(rv, status_code=400)
            self.assertEquals(data, {
                u'path': u'/test/path',
                u'method': u'GET',
                u'message': u'Required resource element missing',
                u'element-name': u'test'
            })

    def test_unknown_element(self):
        error = UnknownElement(name='test')
        with self.app.test_request_context('/test/path'):
            rv = self.app.make_response(
                error_handlers.unknown_element_handler(error))
            data = self.check_and_parse_response(rv, status_code=400)
            self.assertEquals(data, {
                u'path': u'/test/path',
                u'method': u'GET',
                u'message': u'Unknown resource element.',
                u'element-name': u'test'
            })

    def test_invalid_request(self):
        error = InvalidRequest('Test message')
        with self.app.test_request_context('/test/path'):
            rv = self.app.make_response(
                error_handlers.invalid_request_handler(error))
            data = self.check_and_parse_response(rv, status_code=400)
            self.assertEquals(data.get('path'), u'/test/path')
            self.assertEquals(data.get('method'), u'GET')
            self.assertTrue('Test message' in data.get('message'))


class ErrorHandlerTestCase(TestCase, MoxTestBase):
    def test_unauthorized_500(self):
        self.mox.StubOutWithMock(error_handlers, 'is_authenticated')
        error_handlers.is_authenticated().AndReturn(False)
        self.mox.ReplayAll()

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
        self.mox.StubOutWithMock(error_handlers, 'is_authenticated')
        error_handlers.is_authenticated().AndReturn(True)
        self.mox.ReplayAll()

        with self.app.test_request_context():
            resp = self.app.make_response(
                error_handlers.exception_handler(RuntimeError('Test message')))
        self.assertEqual(resp.status_code, 500)
        self.assertTrue('X-GD-Altai-Implementation' not in resp.headers)
        self.assertTrue('Test message' in resp.data)

    def test_authorized_500(self):
        self.mox.StubOutWithMock(error_handlers, 'is_authenticated')
        error_handlers.is_authenticated().AndReturn(True)
        self.mox.ReplayAll()

        with self.app.test_request_context():
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
        self.mox.StubOutWithMock(error_handlers, 'is_authenticated')
        error_handlers.is_authenticated().AndReturn(True)
        self.mox.ReplayAll()

        with self.app.test_request_context():
            resp = self.app.make_response(
                error_handlers.exception_handler(RuntimeError('Test message')))
        data = self.check_and_parse_response(resp, status_code=500)
        self.assertTrue('Test message' in data.get('message', ''))
        self.assertTrue('traceback' not in data)

