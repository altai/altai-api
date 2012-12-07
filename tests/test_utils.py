
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

import sys
import unittest
import flask

from tests import TestCase

from altai_api import exceptions as exc

from altai_api.utils import make_json_response, make_collection_response
from altai_api.utils import int_from_string, int_from_user
from altai_api.utils import _parse_sortby, _apply_sortby


class MakeResponseTestCase(TestCase):

    def test_default_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = False

        resp = make_json_response({'one': 1})
        self.assertEquals(resp.data, '{"one":1}')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')

    def test_empty_400_response(self):
        resp = make_json_response(None, status_code=400)
        self.assertEquals(resp.data, '')
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')

    def test_pretty_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = True

        resp = make_json_response({'one': 1})
        self.assertEquals(resp.data, '{\n    "one": 1\n}')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')


class IntParseAndCheckTestCase(unittest.TestCase):

    def test_parses_string(self):
        self.assertEquals(42, int_from_string('42'))

    def test_not_parses_ints(self):
        self.assertRaises(ValueError, int_from_string, 42)

    def test_no_leading_zeroes(self):
        self.assertRaises(ValueError, int_from_string, '0042')

    def test_parses_zero_string(self):
        self.assertEquals(0, int_from_string('0'))

    def test_checkes_zero(self):
        self.assertEquals(0, int_from_user(0))

    def test_not_parses_negative(self):
        self.assertRaises(ValueError, int_from_string, '-1')

    def test_not_parses_empty(self):
        self.assertRaises(ValueError, int_from_string, '')

    def test_not_parses_invalid(self):
        self.assertRaises(ValueError, int_from_string, 'a string')

    def test_not_parses_none(self):
        self.assertRaises(ValueError, int_from_string, None)

    def test_may_parse_none_if_asked(self):
        self.assertEquals(None, int_from_string(None, allow_none=True))

    def test_from_user_no_strings(self):
        self.assertRaises(ValueError, int_from_user, '42')

    def test_from_user_no_floats(self):
        self.assertRaises(ValueError, int_from_user, 42.0)

    def test_from_user_accepts_logns(self):
        l = 311915573212624289544582358376647421533L
        self.assertEquals(l, int_from_user(l))


class MakeCollectionResponseTestCase(TestCase):


    def setUp(self):
        super(MakeCollectionResponseTestCase, self).setUp()
        self.__context = self.app.test_request_context()
        self.__context.__enter__()
        self.install_fake_auth()
        flask.g.limit = None
        flask.g.offset = None
        flask.g.unused_args = set([])
        self.result = [u'TEST1', u'TEST2', u'TEST3', u'TEST4',
                       u'TEST5', u'TEST6', u'TEST7']

    def tearDown(self):
        self.__context.__exit__(*sys.exc_info())
        super(MakeCollectionResponseTestCase, self).tearDown()

    def test_it_works(self):
        expected = {
            u'collection': {
                u'name': u'test',
                u'parent-href': u'/v1/test',
                u'size': 7
            },
            u'test': self.result
        }
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_limit(self):
        expected = {
            u'collection': {
                u'name': u'test',
                u'parent-href': u'/v1/test',
                u'size': 7
            },
            u'test': [u'TEST1', u'TEST2']
        }
        flask.g.limit = 2
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_offset(self):
        expected = {
            u'collection': {
                u'name': u'test',
                u'parent-href': u'/v1/test',
                u'size': 7
            },
            u'test': [u'TEST4', u'TEST5', u'TEST6', u'TEST7']
        }
        flask.g.offset = 3
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_limit_offset(self):
        expected = {
            u'collection': {
                u'name': u'test',
                u'parent-href': u'/v1/test',
                u'size': 7
            },
            u'test': [u'TEST3', u'TEST4', u'TEST5']
        }
        flask.g.limit = 3
        flask.g.offset = 2
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)


class SortByTestCase(unittest.TestCase):
    allowed = ('first', 'second')

    def test_parses_simple(self):
        sortby = _parse_sortby('first', self.allowed)
        self.assertEquals(len(sortby), 1)
        self.assertEquals(sortby[0][0], 'first')
        self.assertEquals(sortby[0][1], True)

    def test_invalid_direction_raises(self):
        self.assertRaises(exc.InvalidRequest, _parse_sortby, 'first:i am bad', self.allowed)

    def test_invalid_parameter_raises(self):
        self.assertRaises(exc.InvalidRequest, _parse_sortby,
                          'fw-rule-sets:desc', self.allowed)

    def test_applies_nothing(self):
        victim = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        self.assertEquals(victim, _apply_sortby(None, victim))

    def test_aplies_one(self):
        victim = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        result = [
            { 'first': 1 },
            { 'first': 2 },
            { 'first': 3 }
        ]
        sortby = _parse_sortby('first', self.allowed)
        self.assertEquals(result, _apply_sortby(sortby, victim))

    def test_key_not_found(self):
        victim = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        sortby = _parse_sortby('second', self.allowed)
        try:
            _apply_sortby(sortby, victim)
        except Exception, e:
            self.fail('Unexpected exception: %s', e)


    def test_sort_by_two(self):
        victim = [
            { 'first': 2, 'second': 2 },
            { 'first': 2, 'second': 1 },
            { 'first': 1, 'second': 99 }
        ]
        result = [
            { 'first': 1, 'second': 99 },
            { 'first': 2, 'second': 1 },
            { 'first': 2, 'second': 2 }
        ]
        sortby = _parse_sortby('first,second', self.allowed)
        self.assertEquals(result, _apply_sortby(sortby, victim))

    def test_sort_one_asc(self):
        victim = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        result = [
            { 'first': 1 },
            { 'first': 2 },
            { 'first': 3 }
        ]
        sortby = _parse_sortby('first:asc', self.allowed)
        self.assertEquals(result, _apply_sortby(sortby, victim))

    def test_sort_one_desc(self):
        victim = [
            { 'first': 1 },
            { 'first': 2 },
            { 'first': 3 }
        ]
        result = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        sortby = _parse_sortby('first:desc', self.allowed)
        self.assertEquals(result, _apply_sortby(sortby, victim))

    def test_sort_two_different(self):
        victim = [
            { 'first': 2, 'second': 2 },
            { 'first': 2, 'second': 1 },
            { 'first': 1, 'second': 0 }
        ]
        result = [
            { 'first': 1, 'second': 0 },
            { 'first': 2, 'second': 2 },
            { 'first': 2, 'second': 1 }
        ]
        sortby = _parse_sortby('first,second:desc', self.allowed)
        self.assertEquals(result, _apply_sortby(sortby, victim))
