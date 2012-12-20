
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

from altai_api.schema import types as st
from altai_api import exceptions as exc

from altai_api.schema import Schema
from altai_api.utils.filters import parse_filters, apply_filters


class ParseFiltersTestCase(unittest.TestCase):

    def setUp(self):
        super(ParseFiltersTestCase, self).setUp()
        self.schema = Schema([
            st.String('name'),
            st.Int('size')
        ])

    def test_parses_empty(self):
        self.assertEquals({}, parse_filters({}, self.schema))

    def test_parses_several(self):
        params = {
            'name:eq': 'test',
            'size:gt': '28',
            'size:lt': '32'
        }
        expected = {
            'name': { 'eq': 'test' },
            'size': { 'gt': 28, 'lt': 32 }
        }
        real = parse_filters(params.iteritems(), self.schema)
        self.assertEquals(expected, real)

    def test_duplicate_raises(self):
        params = (('name:eq', 'a'), ('size:lt', '32'), ('name:eq', 'b'))
        self.assertRaises(exc.InvalidRequest,
                          parse_filters, params, self.schema)

    def test_unknown_name(self):
        self.assertRaises(exc.UnknownArgument,
                          parse_filters, [('u:eq', 'a')], self.schema)

    def test_unknown_ftype(self):
        self.assertRaises(exc.InvalidRequest,
                          parse_filters, [('name:gg', 'a')], self.schema)


class ApplyFiltersTestCase(unittest.TestCase):

    def setUp(self):
        super(ApplyFiltersTestCase, self).setUp()
        self.schema = Schema([
            st.String('name'),
            st.Int('size')
        ])
        self.filters = {
            'name': { 'eq': 'test' },
            'size': { 'gt': 28, 'lt': 32 }
        }

    def test_empty_result(self):
        self.assertEquals([], apply_filters([], self.filters, self.schema))

    def test_simple(self):
        param = [
            { 'name': 'test1', 'size': 30 },
            { 'name': 'test', 'size': 30 },
            { 'name': 'test', 'size': 33 },
            { 'name': 'test', 'size': 0 }
        ]
        expected = [
            { 'name': 'test', 'size': 30 },
        ]
        result = apply_filters(param, self.filters, self.schema)
        self.assertEquals(expected, result)

