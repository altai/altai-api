
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

from datetime import datetime
from altai_api import exceptions as exc

from altai_api.schema import Schema
from altai_api.schema import types as st


class ElementTypeTestCase(unittest.TestCase):

    def test_constructor(self):
        t = st.ElementType('test', 'test type')
        self.assertEquals(t.name, 'test')
        self.assertEquals(t.typename, 'test type')

    def test_from_requests_rise(self):
        t = st.ElementType('test', 'test type')
        self.assertRaises(exc.IllegalValue, t.from_string, None)
        self.assertRaises(exc.IllegalValue, t.from_request, None)

    def test_not_implemented_matcher_is_not_implemented(self):
        self.assertRaises(NotImplementedError,
                          st.not_implemented_matcher, 1, 1)


class LinkObjectTestCase(unittest.TestCase):

    def setUp(self):
        super(LinkObjectTestCase, self).setUp()
        self.lo = st.LinkObject('test')

    def test_lo_typename(self):
        self.assertEquals(self.lo.typename, 'link object')

    def test_parses(self):
        self.assertEquals('42', self.lo.from_string('42'))

    def test_eq_matcher(self):
        lo_eq = self.lo.get_search_matcher('eq')
        self.assertTrue(lo_eq({'id': '42'}, '42'))
        self.assertFalse(lo_eq({'id': '42'}, '43'))

    def test_from_request_ok(self):
        self.assertEquals('42', self.lo.from_request('42'))

    def test_from_request_fail(self):
        self.assertRaises(exc.IllegalValue,
                          self.lo.from_request, {'id': '42'})

    def test_in_matcher(self):
        lo_in = self.lo.get_search_matcher('in')
        self.assertTrue(lo_in({'id': '42'}, ['41', '42', 'id']))
        self.assertFalse(lo_in({'id': '42'}, ['41', 'id']))


class LinkObjectListTestCase(unittest.TestCase):
    def setUp(self):
        super(LinkObjectListTestCase, self).setUp()
        self.ll = st.List(st.LinkObject('test'))

    def test_ll_typename(self):
        self.assertEquals(self.ll.typename, 'list<link object>')

    def test_parse_raises(self):
        self.assertRaises(exc.IllegalValue,
                          self.ll.from_string, '[42]')

    def test_no_eq_matcher(self):
        self.assertRaises(exc.InvalidRequest,
                          self.ll.get_search_matcher, 'eq')

    def test_from_request_ok(self):
        value = ['42', '43']
        self.assertEquals(value, self.ll.from_request(value))

    def test_from_request_bad_value(self):
        self.assertRaises(exc.IllegalValue,
                          self.ll.from_request, ['42', 43])

    def test_from_request_fail(self):
        self.assertRaises(exc.IllegalValue,
                          self.ll.from_request, '42')


class BooleanTestCase(unittest.TestCase):

    def setUp(self):
        super(BooleanTestCase, self).setUp()
        self.b = st.Boolean('test')

    def test_boolean_typename(self):
        self.assertEquals(self.b.typename, 'boolean')

    def test_boolean_parses(self):
        self.assertEquals(True, self.b.from_string('True'))

    def test_boolean_accepts_lower(self):
        self.assertEquals(False, self.b.from_string('false'))

    def test_boolean_no_upper(self):
        self.assertRaises(exc.IllegalValue, self.b.from_string, 'FALSE')

    def test_boolean_no_ones(self):
        self.assertRaises(exc.IllegalValue, self.b.from_string, '1')

    def test_matcher_eq(self):
        b_eq = self.b.get_search_matcher('eq')
        self.assertTrue(b_eq(True, True))
        self.assertFalse(b_eq(True, False))

    def test_from_request_ok(self):
        self.assertEquals(True, self.b.from_request(True))
        self.assertEquals(False, self.b.from_request(False))

    def test_from_request_fail(self):
        self.assertRaises(exc.IllegalValue, self.b.from_request, 42)


class TimestampTestCase(unittest.TestCase):
    def setUp(self):
        super(TimestampTestCase, self).setUp()
        self.ts = st.Timestamp('test')
        self.d = datetime(2012, 9, 13, 19, 46, 0)
        self.ge = self.ts.get_search_matcher('ge')

    def test_timestamp_typename(self):
        self.assertEquals(self.ts.typename, 'timestamp')

    def test_timestamp_parses(self):
        self.assertEquals(
            self.ts.from_string('2012-09-13T19:46:00Z'), self.d)

    def test_timestamp_forces_seconds(self):
        self.assertRaises(exc.IllegalValue, self.ts.from_string,
                          '2012-09-13T19:46Z')

    def test_timestamp_forces_T(self):
        self.assertRaises(exc.IllegalValue, self.ts.from_string,
                          '2012-09-13 19:46:00Z')

    def test_timestamp_forces_Z(self):
        self.assertRaises(exc.IllegalValue, self.ts.from_string,
                          '2012-09-13T19:46:00')

    def test_timestamp_ge_same(self):
        self.assertEquals(self.ge(self.d, self.d), True)

    def test_timestamp_ge_other(self):
        other_date = datetime(2012, 9, 13, 19, 46, 1)
        self.assertEquals(self.ge(self.d, other_date), False)

    def test_timestamp_ge_none(self):
        self.assertEquals(self.ge(None, self.d), False)

    def test_timestamp_from_request(self):
        self.assertEquals(
            self.ts.from_request('2012-09-13T19:46:00Z'), self.d)

    def test_timestamp_list_from_request(self):
        lts = st.List(st.Timestamp('test'))
        self.assertEquals(
            lts.from_request(['2012-09-13T19:46:00Z']), [self.d])


class Ipv4TestCase(unittest.TestCase):

    def setUp(self):
        super(Ipv4TestCase, self).setUp()
        self.i = st.Ipv4('test')

    def test_ipv4_typename(self):
        self.assertEquals(self.i.typename, 'ipv4')

    def test_ipv4_parses(self):
        self.assertEquals(self.i.from_string('192.168.1.42'),
                          '192.168.1.42')

    def test_ipv4_parses_zero(self):
        self.assertEquals(self.i.from_string('192.0.1.42'),
                          '192.0.1.42')

    def test_ipv4_no_leading_zeroes(self):
        self.assertRaises(exc.IllegalValue, self.i.from_string,
                          '192.168.01.42')

    def test_ipv4_check_bounds(self):
        self.assertRaises(exc.IllegalValue, self.i.from_string, '192.368.1.42')

    def test_ipv4_all_octets(self):
        self.assertRaises(exc.IllegalValue, self.i.from_string, '192.168.1.')

    def test_ipv4_all_octets_no_dot(self):
        self.assertRaises(exc.IllegalValue, self.i.from_string, '192.168.1')

    def test_from_request(self):
        self.assertRaises(exc.IllegalValue, self.i.from_request, 'xxx')


class CidrTestCase(unittest.TestCase):

    def setUp(self):
        super(CidrTestCase, self).setUp()
        self.c = st.Cidr('test')

    def test_cidr_typename(self):
        self.assertEquals(self.c.typename, 'cidr')

    def test_cidr_parses(self):
        self.assertEquals(self.c.from_string('192.168.1.0/24'),
                          '192.168.1.0/24')

    def test_cidr_checks_big_net(self):
        self.assertRaises(exc.IllegalValue,
                          self.c.from_string, '192.168.1.0/42')

    def test_cidr_no_leading_zeroes(self):
        self.assertRaises(exc.IllegalValue,
                          self.c.from_string, '192.168.1.0/023')

    def test_from_request(self):
        self.assertRaises(exc.IllegalValue, self.c.from_request, 'xxx')


class StringTestCase(unittest.TestCase):

    def setUp(self):
        super(StringTestCase, self).setUp()
        self.s = st.String('test', add_search_matchers={
            'contains': lambda a, b: b in a
        })

    def test_strng_typename(self):
        self.assertEquals(self.s.typename, 'string')

    def test_from_string_string(self):
        self.assertEquals('test', self.s.from_string('test'))

    def test_eq(self):
        s_eq = self.s.get_search_matcher('eq')
        self.assertTrue(s_eq('test', 'test'))
        self.assertFalse(s_eq('test', ''))

    def test_no_lt(self):
        self.assertRaises(exc.InvalidRequest, self.s.get_search_matcher, 'lt')

    def test_startswith(self):
        s_sw = self.s.get_search_matcher('startswith')
        self.assertTrue(s_sw('abcd', 'ab'))
        self.assertFalse(s_sw('abcd', 'cd'))

    def test_our_additional_matcher(self):
        s_cc = self.s.get_search_matcher('contains')
        self.assertTrue(s_cc('abcd', 'ab'))
        self.assertTrue(s_cc('abcd', 'cd'))
        self.assertFalse(s_cc('abcd', 'bd'))

    def test_from_request_ok(self):
        self.assertEquals('test', self.s.from_request('test'))

    def test_from_request_fail(self):
        self.assertRaises(exc.IllegalValue, self.s.from_request, 42)


class IntTestCase(unittest.TestCase):

    def setUp(self):
        super(IntTestCase, self).setUp()
        self.u = st.Int('test')

    def test_typename(self):
        self.assertEquals(self.u.typename, 'uint')

    def test_parses_string(self):
        self.assertEquals(42, self.u.from_string('42'))

    def test_not_parses_ints(self):
        self.assertRaises(exc.IllegalValue, self.u.from_string, 42)

    def test_no_leading_zeroes(self):
        self.assertRaises(exc.IllegalValue, self.u.from_string, '0042')

    def test_parses_zero_string(self):
        self.assertEquals(0, self.u.from_string('0'))

    def test_not_parses_negative(self):
        self.assertRaises(exc.IllegalValue, self.u.from_string, '-1')

    def test_not_parses_empty(self):
        self.assertRaises(exc.IllegalValue, self.u.from_string, '')

    def test_not_parses_invalid(self):
        self.assertRaises(exc.IllegalValue, self.u.from_string, 'a string')

    def test_from_request_ok(self):
        self.assertEquals(self.u.from_request(42), 42)

    def test_from_request_fail(self):
        self.assertRaises(exc.IllegalValue, self.u.from_request, '42')


class SchemaTestCase(unittest.TestCase):

    def setUp(self):
        super(SchemaTestCase, self).setUp()
        self.schema = Schema((
            st.String('name'),
            st.LinkObject('project'),
            st.Int('intval')
        ))

    def test_info(self):
        self.assertEquals(len(self.schema.info), 3)
        self.assertEquals(self.schema.info[1].name, 'project')

    def test_sortby_names(self):
        self.assertEquals(self.schema.sortby_names,
                          set(['name', 'intval',
                               'project.name', 'project.id']))

    def test_argument_matcher(self):
        eq = self.schema.argument_matcher('name', 'eq')
        self.assertTrue(eq('a', 'a'))
        self.assertFalse(eq('a', 'b'))

    def test_argument_matcher_bad_type(self):
        self.assertRaises(exc.InvalidRequest,
                          self.schema.argument_matcher, 'name', 'qwe')

    def test_argument_matcher_bad_name(self):
        self.assertRaises(KeyError,
                          self.schema.argument_matcher, 'stuff', 'eq')

    def test_parse_argument_parses(self):
        self.assertEquals(42, self.schema.parse_argument('intval', 'eq', '42'))

    def test_stuff_works(self):
        m = self.schema.argument_matcher('project', 'eq')
        v = self.schema.parse_argument('project', 'eq', 'PID')
        self.assertTrue(m({ 'id': 'PID' }, v))

    def test_doesnt_replace_methods(self):
        self.assertRaises(ValueError, Schema,
                          (st.Int('test'),), argument_matcher=('test',))

