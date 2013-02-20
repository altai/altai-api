
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

import unittest
import flask

from datetime import datetime

from tests import TestCase, ContextWrappedTestCase
from altai_api import exceptions as exc

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils import (make_json_response,
                             make_collection_response,
                             parse_request_data)
from altai_api.utils.collection import get_matcher_argument
from altai_api.utils.communication import parse_my_projects_arg
from altai_api.utils.sorting import parse_sortby, apply_sortby
from altai_api.utils.parsers import int_from_string, int_from_user
from altai_api.utils.parsers import cidr_from_user, ipv4_from_user
from altai_api.utils.parsers import timestamp_from_openstack
from altai_api.utils.parsers import split_with_escape


class MakeResponseTestCase(TestCase):

    def test_default_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = False

        with self.app.test_request_context():
            resp = make_json_response({'one': 1})
        self.assertEquals(resp.data, '{"one":1}')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')

    def test_empty_400_response(self):
        with self.app.test_request_context():
            resp = make_json_response(None, status_code=400)
        self.assertEquals(resp.data, '')
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')

    def test_pretty_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = True

        with self.app.test_request_context():
            resp = make_json_response({'one': 1})
        self.assertEquals(resp.data, '{\n    "one": 1\n}\n')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')

    def test_dates_in_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = False
        timestamp = datetime(2012, 9, 13, 15, 03, 42)
        with self.app.test_request_context():
            resp = make_json_response({'created': timestamp})
        self.assertEquals(resp.data, '{"created":"2012-09-13T15:03:42Z"}')

    def test_dates_in_pretty_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = True
        timestamp = datetime(2012, 9, 13, 15, 03, 42)
        with self.app.test_request_context():
            resp = make_json_response({'created': timestamp})
        self.assertTrue('"2012-09-13T15:03:42Z"' in resp.data)

    def test_raises_nicely(self):
        class TestClass(object):
            def __repr__(self):
                return 'TEST CLASS'
        with self.app.test_request_context():
            try:
                make_json_response({'a': TestClass()})
            except TypeError, error:
                pass
            else:
                self.fail('TypeError was not raised')
        self.assertTrue('TEST CLASS' in str(error))


class ParseRequestDataTestCase(TestCase):

    def request_context(self, data):
        return self.app.test_request_context(data=flask.json.dumps(data))

    def test_basics(self):
        params = {}
        with self.request_context(params):
            self.assertEquals(params, parse_request_data(None, None))

    def test_bad_json(self):
        with self.app.test_request_context(data='{'):
            self.assertRaises(exc.InvalidRequest,
                              parse_request_data, None, None)

    def test_object_required(self):
        with self.request_context(data='[]'):
            self.assertRaises(exc.InvalidRequest,
                              parse_request_data, None, None)

    def test_required_missing(self):
        schema = Schema((st.Int('req'),))
        with self.request_context({}):
            self.assertRaises(exc.MissingElement,
                              parse_request_data, None, schema)

    def test_required_wrong(self):
        schema = Schema((st.Int('req'),))
        with self.request_context({'req': '42'}):
            self.assertRaises(exc.IllegalValue,
                              parse_request_data, None, schema)

    def test_required_ok(self):
        schema = Schema((st.Int('req'),))
        params = {'req': 42}
        with self.request_context(params):
            self.assertEquals(params,
                              parse_request_data(None, schema))

    def test_allowed_missing(self):
        schema = Schema((st.Int('req'),))
        params = {}
        with self.request_context({}):
            self.assertEquals(params,
                              parse_request_data(schema))

    def test_allowed_wrong(self):
        schema = Schema((st.Int('test'),))
        with self.request_context({'test': '42'}):
            self.assertRaises(exc.IllegalValue,
                              parse_request_data, schema)

    def test_allowed_ok(self):
        schema = Schema((st.Int('test'),))
        params = {'test': 42}
        with self.request_context(params):
            self.assertEquals(params,
                              parse_request_data(schema))

    def test_extra_is_caught(self):
        with self.request_context({'test': '42'}):
            self.assertRaises(exc.UnknownElement,
                              parse_request_data, None, None)

    def test_date_is_parsed(self):
        timestamp = datetime(2012, 5, 11, 17, 42, 53)
        schema = Schema((st.Timestamp('test'),))
        params = {'test': '2012-05-11T17:42:53Z'}
        with self.request_context(params):
            self.assertEquals({'test': timestamp},
                              parse_request_data(schema))

    def test_checks_value_length(self):
        data = '{"9000 a": "%s"}' % ('A' * 9000)
        with self.app.test_request_context(data=data):
            self.assertRaises(exc.InvalidRequest, parse_request_data)

    def test_checks_value_in_list_length(self):
        data = '{"9000 a": ["%s"]}' % ('A' * 9000)
        with self.app.test_request_context(data=data):
            self.assertRaises(exc.InvalidRequest, parse_request_data)

    def test_checks_key_length(self):
        data = '{"%s": null}' % ('k' * 100)
        with self.app.test_request_context(data=data):
            self.assertRaises(exc.InvalidRequest, parse_request_data)

    def test_checks_key_is_string(self):
        with self.app.test_request_context(data='{5:0}'):
            self.assertRaises(exc.InvalidRequest, parse_request_data)


class IntParseAndCheckTestCase(unittest.TestCase):

    def test_parses_string(self):
        self.assertEquals(42, int_from_string('42'))

    def test_not_parses_ints(self):
        self.assertRaises(ValueError, int_from_string, 42)

    def test_no_leading_zeroes(self):
        self.assertRaises(ValueError, int_from_string, '0042')

    def test_parses_zero_string(self):
        self.assertEquals(0, int_from_string('0'))

    def test_checks_zero(self):
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

    def test_from_user_accepts_longs(self):
        l = 311915573212624289544582358376647421533L
        self.assertEquals(l, int_from_user(l))


class IpAndCidrCheckTestCase(unittest.TestCase):

    def test_ipv4_parses(self):
        self.assertEquals(ipv4_from_user('192.168.1.42'),
                          '192.168.1.42')

    def test_ipv4_parses_zero(self):
        self.assertEquals(ipv4_from_user('192.0.1.42'),
                          '192.0.1.42')

    def test_ipv4_no_leading_zeroes(self):
        self.assertRaises(ValueError, ipv4_from_user,
                          '192.168.01.42')

    def test_ipv4_check_bounds(self):
        self.assertRaises(ValueError, ipv4_from_user, '192.368.1.42')

    def test_ipv4_all_octets(self):
        self.assertRaises(ValueError, ipv4_from_user, '192.168.1.')

    def test_ipv4_all_octets_no_dot(self):
        self.assertRaises(ValueError, ipv4_from_user, '192.168.1')

    def test_cidr_parses(self):
        self.assertEquals(cidr_from_user('192.168.1.0/24'),
                          '192.168.1.0/24')

    def test_cidr_checks_big_net(self):
        self.assertRaises(ValueError,
                          cidr_from_user, '192.168.1.0/42')

    def test_cidr_checks_lower_zeroes(self):
        self.assertRaises(ValueError,
                          cidr_from_user, '192.168.1.1/24')

    def test_cidr_no_leading_zeroes(self):
        self.assertRaises(ValueError,
                          cidr_from_user, '192.168.1.0/023')


class GetMatcherArgumentTestCase(ContextWrappedTestCase):

    def test_none(self):
        flask.g.filters = None
        self.assertEquals(None, get_matcher_argument('project', 'for'))

    def test_no_matchers(self):
        flask.g.filters = { 'some': {'other': 'matcher'} }
        self.assertEquals(None, get_matcher_argument('project', 'for'))

    def test_no_match_type(self):
        flask.g.filters = { 'project': {'eq': '42'} }
        self.assertEquals(None, get_matcher_argument('project', 'for'))

    def test_gets(self):
        value = '42'
        flask.g.filters = { 'project': {'for': value} }
        result = get_matcher_argument('project', 'for')
        self.assertEquals(value, result)
        self.assertEquals(value, flask.g.filters['project'].get('for'))

    def test_gets_and_deletes(self):
        value = '42'
        flask.g.filters = { 'project': {'for': value} }
        result = get_matcher_argument('project', 'for',
                                      delete_if_found=True)
        self.assertEquals(value, result)
        self.assertTrue('for' not in flask.g.filters['project'])


class MakeCollectionResponseTestCase(ContextWrappedTestCase):

    def setUp(self):
        super(MakeCollectionResponseTestCase, self).setUp()
        flask.g.limit = None
        flask.g.offset = None
        flask.g.unused_args = set([])
        flask.g.collection_schema = Schema((
            st.Int('test'),
        ))
        self.result = [{'test': 1}, {'test': 2}, {'test': 3}, {'test': 4},
                       {'test': 5}, {'test': 6}, {'test': 7}]

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
            u'test': [{'test': 1}, {'test': 2}]
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
            u'test': [{'test': 4}, {'test': 5},
                      {'test': 6}, {'test': 7}]
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
            u'test': [{'test': 3}, {'test': 4}, {'test': 5}]
        }
        flask.g.limit = 3
        flask.g.offset = 2
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_filtered(self):
        expected = {
            u'collection': {
                u'name': u'test',
                u'parent-href': u'/v1/test',
                u'size': 3
            },
            u'test': [{'test': 5}, {'test': 6}, {'test': 7}]
        }
        flask.g.filters = { 'test': { 'ge': 5 } }
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_filtered_limit(self):
        expected = {
            u'collection': {
                u'name': u'test',
                u'parent-href': u'/v1/test',
                u'size': 3
            },
            u'test': [{'test': 5}, {'test': 6}]
        }
        flask.g.filters = { 'test': { 'ge': 5 } }
        flask.g.limit = 2
        rv = make_collection_response(u'test', self.result,
                                      parent_href='/v1/test')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)


class SortByTestCase(unittest.TestCase):
    allowed = ('first', 'second')

    def test_parses_simple(self):
        sortby = parse_sortby('first', self.allowed)
        self.assertEquals(len(sortby), 1)
        self.assertEquals(sortby[0][0], 'first')
        self.assertEquals(sortby[0][1], True)

    def test_invalid_direction_raises(self):
        self.assertRaises(exc.InvalidRequest, parse_sortby,
                          'first:i am bad', self.allowed)

    def test_invalid_parameter_raises(self):
        self.assertRaises(exc.InvalidRequest, parse_sortby,
                          'fw-rule-sets:desc', self.allowed)

    def test_applies_nothing(self):
        victim = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        self.assertEquals(victim, apply_sortby(None, victim))

    def test_applies_one(self):
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
        sortby = parse_sortby('first', self.allowed)
        self.assertEquals(result, apply_sortby(sortby, victim))

    def test_applies_none_is_ok(self):
        d = datetime(2012, 1, 12, 11, 12, 45, 0)
        victim = [
            { 'time': d },
            { 'time': None }
        ]
        result = [
            { 'time': None },
            { 'time': d }
        ]
        sortby = parse_sortby('time', ('time',))
        self.assertEquals(result, apply_sortby(sortby, victim))

    def test_applies_none_is_ok_desc(self):
        d = datetime(2012, 1, 12, 11, 12, 45, 0)
        victim = [
            { 'time': None },
            { 'time': d }
        ]
        result = [
            { 'time': d },
            { 'time': None }
        ]
        sortby = parse_sortby('time:desc', ('time',))
        self.assertEquals(result, apply_sortby(sortby, victim))

    def test_key_not_found(self):
        victim = [
            { 'first': 3 },
            { 'first': 2 },
            { 'first': 1 }
        ]
        sortby = parse_sortby('second', self.allowed)
        try:
            apply_sortby(sortby, victim)
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
        sortby = parse_sortby('first,second', self.allowed)
        self.assertEquals(result, apply_sortby(sortby, victim))

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
        sortby = parse_sortby('first:asc', self.allowed)
        self.assertEquals(result, apply_sortby(sortby, victim))

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
        sortby = parse_sortby('first:desc', self.allowed)
        self.assertEquals(result, apply_sortby(sortby, victim))

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
        sortby = parse_sortby('first,second:desc', self.allowed)
        self.assertEquals(result, apply_sortby(sortby, victim))


class TimestampFromOpenstackTestCase(unittest.TestCase):

    def test_timestamp_can_be_parsed(self):
        value = "2012-09-13T15:00:42Z"
        expected = datetime(2012, 9, 13, 15, 0, 42)
        self.assertEquals(expected,
                          timestamp_from_openstack(value))

    def test_timestamp_without_zone_can_be_parsed(self):
        value = "2012-09-13T15:00:42"
        expected = datetime(2012, 9, 13, 15, 0, 42)
        self.assertEquals(expected,
                          timestamp_from_openstack(value))

    def test_timestamp_with_microseconds_can_be_parsed(self):
        value = "2012-09-13T15:00:42.000Z"
        expected = datetime(2012, 9, 13, 15, 0, 42)
        self.assertEquals(expected,
                          timestamp_from_openstack(value))

    def test_invalid_timestamp_shall_not_pass(self):
        value = "2012-09-13T15:00:42ZZ"
        self.assertRaises(ValueError,
                          timestamp_from_openstack, value)

    def test_invalid_type_rejected(self):
        self.assertRaises(TypeError,
                          timestamp_from_openstack, 42)


class SplitWithEscapeTestCase(unittest.TestCase):

    def test_split_single(self):
        result = list(split_with_escape('abc', '|'))
        self.assertEquals(['abc'], result)

    def test_split_simple(self):
        result = list(split_with_escape('abc|def|qwe', '|'))
        self.assertEquals(['abc', 'def', 'qwe'], result)

    def test_split_with_esc(self):
        result = list(split_with_escape(r'abc|def\|qwe', '|'))
        self.assertEquals(['abc', 'def|qwe'], result)

    def test_split_with_esc_esc(self):
        result = list(split_with_escape(r'abc|def\\|qwe', '|'))
        self.assertEquals(['abc', 'def\\', 'qwe'], result)

    def test_split_empty(self):
        result = list(split_with_escape(r'abc||def|', '|'))
        self.assertEquals(['abc', '', 'def', ''], result)

    def test_split_single_char(self):
        gen = split_with_escape('abc', '||')
        self.assertRaises(ValueError, list, gen)

    def test_split_esc_single_char(self):
        gen = split_with_escape('abc', '|', 'escape')
        self.assertRaises(ValueError, list, gen)

    def test_split_no_last_esc(self):
        gen = split_with_escape('abc\\', '|')
        self.assertRaises(ValueError, list, gen)

    def test_split_unknown_esc(self):
        gen = split_with_escape(r'abc\a', '|')
        self.assertRaises(ValueError, list, gen)


class ParseMyProjectsArgTestCase(TestCase):

    def test_default_for_admins_is_false(self):
        with self.app.test_request_context('/'):
            self.install_fake_auth()
            flask.g.unused_args = set(flask.request.args.iterkeys())

            flask.g.is_admin = True
            parse_my_projects_arg()
            self.assertEquals(flask.g.my_projects, False)
            self.assertEquals(flask.g.unused_args, set())

    def test_default_for_non_admins_is_true(self):
        with self.app.test_request_context('/'):
            self.install_fake_auth()
            flask.g.unused_args = set(flask.request.args.iterkeys())

            flask.g.is_admin = False
            parse_my_projects_arg()
            self.assertEquals(flask.g.my_projects, True)
            self.assertEquals(flask.g.unused_args, set())

    def test_non_admin_can_set_true(self):
        with self.app.test_request_context('/?my-projects=true'):
            self.install_fake_auth()
            flask.g.unused_args = set(flask.request.args.iterkeys())

            flask.g.is_admin = False
            parse_my_projects_arg()
            self.assertEquals(flask.g.my_projects, True)
            self.assertEquals(flask.g.unused_args, set())

    def test_non_admin_can_not_set_false(self):
        with self.app.test_request_context('/?my-projects=false'):
            self.install_fake_auth()
            flask.g.unused_args = set(flask.request.args.iterkeys())

            flask.g.is_admin = False
            self.assertRaises(exc.IllegalValue, parse_my_projects_arg)

    def test_admin_can_set_true(self):
        with self.app.test_request_context('/?my-projects=true'):
            self.install_fake_auth()
            flask.g.unused_args = set(flask.request.args.iterkeys())

            flask.g.is_admin = True
            parse_my_projects_arg()
            self.assertEquals(flask.g.my_projects, True)
            self.assertEquals(flask.g.unused_args, set())

    def test_admin_can_set_false(self):
        with self.app.test_request_context('/?my-projects=false'):
            self.install_fake_auth()
            flask.g.unused_args = set(flask.request.args.iterkeys())

            flask.g.is_admin = True
            parse_my_projects_arg()
            self.assertEquals(flask.g.my_projects, False)
            self.assertEquals(flask.g.unused_args, set())

