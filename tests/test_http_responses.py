
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

import flask

from tests import TestCase


class HttpResponsesTestCase(TestCase):
    def test_404(self):
        rv = self.client.get('/i-hope-this-resource-will-never-exist')
        self.check_and_parse_response(rv, status_code=404)

    def test_404_with_args(self):
        rv = self.client.get('/i-hope-this-resource-will-never-exist?arg=1')
        data = self.check_and_parse_response(rv, status_code=404)
        self.assertTrue('not found' in data.get('message'))

    def test_unknown_arg_checked(self):
        rv = self.client.get('/?i-hope-this-arg=will-never-be-passed')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('argument' in data.get('message'))

    def test_mime_checked(self):
        rv = self.client.post('/v1/instance-types',
                              content_type='invalid')
        self.check_and_parse_response(rv, status_code=400)

    def test_no_empty_posts(self):
        rv = self.client.post('/v1/projects/',
                              content_type='application/json',
                              data='')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('decoding error' in data.get('message'))

    def test_no_whitespace_posts(self):
        rv = self.client.post('/v1/projects/',
                              content_type='application/json',
                              data='     ')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('decoding error' in data.get('message'))

    def test_object_required(self):
        rv = self.client.post('/v1/projects/',
                              content_type='application/json',
                              data='[]')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('object expected' in data.get('message'))

    def test_limit_checked(self):
        rv = self.client.get('/v1/instance-types/?limit=limit-no-exist')
        data = self.check_and_parse_response(rv, status_code=400)
        self.assertTrue('limit-no-exist' in data.get('message'))
        self.assertEquals('InvalidArgumentValue', data['error-type'])

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
        data = self.check_and_parse_response(rv, status_code=405)
        self.assertTrue('Method not allowed' in data.get('message'))

    def test_except_checks_204(self):
        rv = self.client.get('/', headers={'Expect': '204-no-data'})
        data = self.check_and_parse_response(rv, status_code=417)
        self.assertTrue('Expect header' in data.get('message'))

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
    # TODO(imelnikov): test how exceptions are raised and handled
    pass

