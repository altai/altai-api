
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

from tests import TestCase
from altai_api.utils import make_json_response

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

    def test_pretty_response(self):
        self.app.config['PRETTY_PRINT_JSON'] = True

        resp = make_json_response({'one': 1})
        self.assertEquals(resp.data, '{\n    "one": 1\n}')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-type'),
                          'application/json')

