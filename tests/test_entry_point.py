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

"""Tests for API entry point
"""

from tests import TestCase

class EntryPointTestCase(TestCase):
    def test_get_entry_point(self):
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


    def test_post_retuns_405(self):
        rv = self.client.post('/')
        self.check_and_parse_response(rv, status_code=405)


    def test_get_v1_entry_point(self):
        rv = self.client.get('/v1/')
        data = self.check_and_parse_response(rv)
        self.assertEqual(data['major'], 1)
        self.assertEqual(data['minor'], 0)
        self.assertEqual(data['href'], '/v1/')
        self.assertTrue('links' in data)
        # TODO(imelnikov): check hrefs in links

