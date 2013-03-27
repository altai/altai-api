
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2013 Grid Dynamics Consulting Services, Inc
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

from flask import json
from tests.mocked import MockedTestCase
from altai_api.blueprints import config


class ConfigTestCase(MockedTestCase):

    def setUp(self):
        super(ConfigTestCase, self).setUp()
        self.mox.StubOutWithMock(config, 'ConfigDAO')
        self.dao = config.ConfigDAO
        self.app.config['KEYSTONE_URI'] = 'test_keystone_uri'

    def test_list_works(self):
        self.dao.list_all().AndReturn([
            ('general', 'installation-name', 'Altai'),
            ('invitations', 'enabled', True),
            ('invitations', 'name', 42),
            ('unknown group', 'enabled', False)
        ])

        exp_collection = {
            'name': 'config',
            'size': 4
        }
        exp_invites = {
            'name': 'invitations',
            'enabled': True,
            'href': '/v1/config/invitations'
        }
        exp_names = ['general', 'invitations', 'mail', 'password-reset']

        self.mox.ReplayAll()
        rv = self.client.get('/v1/config/')
        data = self.check_and_parse_response(rv)

        self.assertEquals(exp_collection, data.get('collection'))
        names = [x['name'] for x in data.get('config', ())]
        self.assertEquals(exp_names, list(sorted(names)))
        invites = [x for x in data.get('config', ())
                   if x['name'] == 'invitations']
        self.assertEquals([exp_invites], invites)

    def test_get_general(self):
        self.dao.list_group('general').AndReturn([
            ('general', 'installation-name', 'Altai'),
            ('name', 'installation-name', 'cloud')  # cannot happen
        ])
        expected = {
            'name': 'general',
            'href': '/v1/config/general',
            'installation-name': 'Altai',
            'authorization-mode': 'NATIVE',
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/config/general')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_404(self):
        self.mox.ReplayAll()
        rv = self.client.get('/v1/config/general.name')
        self.check_and_parse_response(rv, 404)

    def update(self, group, data, expected_status_code=200):
        rv = self.client.put('/v1/config/%s' % group,
                             data=json.dumps(data),
                             content_type='application/json')
        return self.check_and_parse_response(
                rv, status_code=expected_status_code)

    def test_update_works(self):
        self.dao.set_to('mail', 'sender-name', 'R0B0T').InAnyOrder()
        self.dao.set_to('mail', 'sender-mail',
                        'no-reply@griddynamics.net').InAnyOrder()
        self.dao.list_group('mail').AndReturn(())

        self.mox.ReplayAll()
        data = self.update('mail', {
            'sender-name': 'R0B0T',
            'sender-mail': 'no-reply@griddynamics.net'
        })
        self.assertEquals('mail', data.get('name'))

    def test_update_bad_value(self):
        self.mox.ReplayAll()
        data = self.update('mail', { 'sender-name': 13 },
                           expected_status_code=400)
        self.assertEquals('sender-name', data.get('element-name'))

    def test_update_bad_group(self):
        self.mox.ReplayAll()
        self.update('non-existing-group', {}, expected_status_code=404)


class UserConfigTestCase(MockedTestCase):
    IS_ADMIN = False

    def setUp(self):
        super(UserConfigTestCase, self).setUp()
        self.mox.StubOutWithMock(config, 'ConfigDAO')
        self.dao = config.ConfigDAO
        self.app.config['KEYSTONE_URI'] = 'test_keystone_uri'

    def test_get_general_as_user(self):
        self.dao.list_group('general').AndReturn([
            ('general', 'installation-name', 'Altai'),
        ])
        expected = {
            'name': 'general',
            'href': '/v1/config/general',
            'installation-name': 'Altai',
            'authorization-mode': 'NATIVE',
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/config/general')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_mail_as_user(self):
        self.mox.ReplayAll()
        rv = self.client.get('/v1/config/mail')
        self.check_and_parse_response(rv, 404)

    def test_list_as_user(self):
        self.dao.list_all().AndReturn([
            ('general', 'installation-name', 'Altai'),
            ('invitations', 'enabled', True),
            ('invitations', 'name', 42),
            ('unknown group', 'enabled', False)
        ])

        exp_collection = {
            'name': 'config',
            'size': 1
        }
        exp_names = ['general']

        self.mox.ReplayAll()
        rv = self.client.get('/v1/config/')
        data = self.check_and_parse_response(rv)

        self.assertEquals(exp_collection, data.get('collection'))
        names = [x['name'] for x in data.get('config', ())]
        self.assertEquals(exp_names, list(sorted(names)))

