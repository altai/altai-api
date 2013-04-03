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

"""Tests for API entry point"""

from tests import TestCase
from tests.mocked import MockedTestCase


class EntryPointTestCase(TestCase):
    FAKE_AUTH = False
    maxDiff = None

    def test_get_entry_point(self):
        rv = self.client.get('/')
        data = self.check_and_parse_response(rv, authenticated=False)
        self.assertEquals(data, {
            "versions": [
                {
                    "major": 1,
                    "minor": 0,
                    "href": "/v1/"
                }
            ]
        })

    def test_get_v1_entry_point(self):
        rv = self.client.get('/v1/')
        data = self.check_and_parse_response(rv, authenticated=False)
        self.assertEqual(data, {
            'major': 1,
            'minor': 0,
            'href': '/v1/',
            'resources': {
                'audit-log': '/v1/audit-log/',
                'config': '/v1/config/',
                'fw-rule-sets': '/v1/fw-rule-sets/',
                'nodes': '/v1/nodes/',
                'images': '/v1/images/',
                'instances': '/v1/instances/',
                'instance-types': '/v1/instance-types/',
                'invites': '/v1/invites/',
                'me': '/v1/me',
                'my-ssh-keys': '/v1/me/ssh-keys/',
                'networks': '/v1/networks/',
                'projects': '/v1/projects/',
                'reset-password': '/v1/me/reset-password',
                'stats': '/v1/stats',
                'users': '/v1/users/',
            }
        })


class AuthenticatedEntryPointTestCase(MockedTestCase):
    maxDiff = None

    def test_get_entry_point(self):
        self.mox.ReplayAll()
        rv = self.client.get('/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, {
            "versions": [
                {
                    "major": 1,
                    "minor": 0,
                    "href": "/v1/"
                }
            ]
        })

    def test_get_v1_entry_point(self):
        self.app.config['KEYSTONE_URI'] = 'test_keystone_uri'
        self.mox.ReplayAll()
        rv = self.client.get('/v1/')
        data = self.check_and_parse_response(rv)
        self.assertEqual(data, {
            'major': 1,
            'minor': 0,
            'href': '/v1/',
            'resources': {
                'audit-log': '/v1/audit-log/',
                'config': '/v1/config/',
                'fw-rule-sets': '/v1/fw-rule-sets/',
                'nodes': '/v1/nodes/',
                'images': '/v1/images/',
                'instances': '/v1/instances/',
                'instance-types': '/v1/instance-types/',
                'invites': '/v1/invites/',
                'me': '/v1/me',
                'my-ssh-keys': '/v1/me/ssh-keys/',
                'networks': '/v1/networks/',
                'projects': '/v1/projects/',
                'reset-password': '/v1/me/reset-password',
                'stats': '/v1/stats',
                'users': '/v1/users/',
            },
            'services': {
                'keystone': 'test_keystone_uri',
                # NOTE(imelnikov): see tests.mocked._TEST_SERVICE_CATALOG
                'nova-billing': 'http://altai.example.com:8787/v2'
            }
        })

