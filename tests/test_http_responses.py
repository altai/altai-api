
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

from altai_api import error_handlers, utils
from altai_api.exceptions import (
    InvalidRequest, MissingElement, IllegalValue, UnknownElement)


class HttpResponsesTestCase(TestCase):
    def test_404(self):
        rv = self.client.get('/i-hope-this-resource-will-never-exist')
        self.check_and_parse_response(rv, status_code=404)

    def test_404_with_args(self):
        rv = self.client.get('/i-hope-this-resource-will-never-exist?bad-arg=1')
        self.check_and_parse_response(rv, status_code=404)

    def test_unknown_arg_checked(self):
        rv = self.client.get('/?i-hope-this-arg=will-never-be-passed')
        self.check_and_parse_response(rv, status_code=400)

    def test_mime_checked(self):
        rv = self.client.post('/v1/instance-types',
                              content_type='invalid')
        self.check_and_parse_response(rv, status_code=400)

    def test_no_empty_posts(self):
        rv = self.client.post('/v1/instance-types/',
                              content_type='application/json',
                              data='')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('object expected' in data.get('message'))

    def test_object_reuqired(self):
        rv = self.client.post('/v1/instance-types/',
                              content_type='application/json',
                              data='[]')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('object expected' in data.get('message'))

    def test_limit_checked(self):
        rv = self.client.get('/v1/instance-types/?limit=limit-no-exist')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('limit-no-exist' in data.get('message'))

    def test_offset_checked(self):
        rv = self.client.get('/v1/instance-types/?offset=bad-offset')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('bad-offset' in data.get('message'))

    def test_charset_checked(self):
        rv = self.client.get('/', headers={'Accept-charset': 'cp1251'})
        self.check_and_parse_response(rv, status_code=400)

    def test_accept_checked(self):
        rv = self.client.get('/', headers={'Accept': 'text/html'})
        self.check_and_parse_response(rv, status_code=400)

    def test_accept_any(self):
        rv = self.client.get('/', headers={'Accept': '*/*'})
        self.check_and_parse_response(rv, status_code=200)

    def test_conditional_checked(self):
        rv = self.client.get('/', headers={'If-Modified-Since':
                                           'Sat, 29 Oct 1994 19:43:31 GMT'})
        self.check_and_parse_response(rv, status_code=400)

    def test_except_works(self):
        rv = self.client.get('/', headers={'Expect': '200-ok'})
        self.check_and_parse_response(rv, status_code=200)

    def test_except_works_delete(self):
        rv = self.client.delete('/', headers={'Expect': '204-no-data'})
        self.check_and_parse_response(rv, status_code=405)

    def test_except_checks_204(self):
        rv = self.client.get('/', headers={'Expect': '204-no-data'})
        self.check_and_parse_response(rv, status_code=417)

    def test_except_checks_202(self):
        rv = self.client.get('/', headers={'Expect': '202-accepted'})
        self.check_and_parse_response(rv, status_code=417)

    def test_no_slash_redirects(self):
        with self.app.test_request_context():
            loc = flask.url_for('instance_types.list_instance_types',
                                _external=True)
        rv = self.client.get('/v1/instance-types')
        self.check_and_parse_response(rv, status_code=301)
        self.assertEquals(loc, rv.headers['Location'])

    def test_no_slash_redirects_with_args(self):
        with self.app.test_request_context():
            loc = flask.url_for('instance_types.list_instance_types',
                                _external=True, sortby='name')
        rv = self.client.get('/v1/instance-types?sortby=name')
        self.check_and_parse_response(rv, status_code=301)
        self.assertEquals(loc, rv.headers['Location'])


class ExceptionsTestCase(TestCase):

    def test_illegal_value(self):
        error = IllegalValue(name='test', typename='uint', value='-42')
        with self.app.test_request_context('/test/path'):
            self.install_fake_auth()
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

    def test_unknown_param(self):
        error = UnknownElement(name='test')
        with self.app.test_request_context('/test/path'):
            self.install_fake_auth()
            rv = self.app.make_response(
                error_handlers.unknown_param_handler(error))
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertEquals(data, {
            u'path': u'/test/path',
            u'method': u'GET',
            u'message': u"Unknown resource element: 'test'",
            u'element-name': u'test'
        })

    def test_invalid_request(self):
        error = InvalidRequest('Test message')
        with self.app.test_request_context('/test/path'):
            self.install_fake_auth()
            rv = self.app.make_response(
                error_handlers.invalid_request_handler(error))
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertEquals(data.get('path'), u'/test/path')
        self.assertEquals(data.get('method'), u'GET')
        self.assertTrue('Test message' in data.get('message'))


class ErrorHandlerTestCase(TestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(ErrorHandlerTestCase, self).setUp()

    def test_unauthorized_500(self):
        with self.app.test_request_context():
            # create exception context for test
            try:
                raise RuntimeError('Test message')
            except RuntimeError, ex:
                resp = self.app.make_response(
                    error_handlers.exception_handler(ex))
        self.check_and_parse_response(resp, status_code=500)
        self.assertTrue('Test message' in resp.data)
        self.assertTrue('traceback' not in resp.data)

    def test_authorized_500_other_error(self):
        with self.app.test_request_context():
            self.install_fake_auth()
            resp = self.app.make_response(
                error_handlers.exception_handler(RuntimeError('Test message')))
        self.assertEqual(resp.status_code, 500)
        self.assertTrue('X-GD-Altai-Implementation' not in resp.headers)
        self.assertTrue('Test message' in resp.data)

    def test_authorized_500(self):
        with self.app.test_request_context():
            self.install_fake_auth()
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
            self.install_fake_auth()
            resp = self.app.make_response(
                error_handlers.exception_handler(RuntimeError('Test message')))
        data = self.check_and_parse_response(resp, status_code=500)
        self.assertTrue('Test message' in data.get('message', ''))
        self.assertTrue('traceback' not in data)

