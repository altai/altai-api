
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

import json

from tests import doubles
from tests.mocked import MockedTestCase

from openstackclient_base import exceptions as osc_exc
from altai_api.collection import project_users


class ListProjectUsersTestCase(MockedTestCase):

    def setUp(self):
        super(ListProjectUsersTestCase, self).setUp()
        self.mox.StubOutWithMock(project_users, 'link_for_user')

    def test_list_works(self):
        project_id = u'PID'
        tenant = doubles.make(self.mox, doubles.Tenant, id=project_id)
        client = self.fake_client_set

        client.identity_admin.tenants.get(project_id).AndReturn(tenant)
        tenant.list_users().AndReturn(['U1', 'U2'])
        project_users.link_for_user('U1').AndReturn(u'D1')
        project_users.link_for_user('U2').AndReturn(u'D2')

        expected = {
            u'collection': {
                u'name': u'users',
                u'parent-href': u'/v1/projects/%s' % project_id,
                u'size': 2
            },
            u'users': [ u'D1', u'D2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/projects/%s/users/' % project_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_list_no_project(self):
        project_id = u'PID'
        self.fake_client_set.identity_admin.tenants.get(project_id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/projects/%s/users/' % project_id)
        self.check_and_parse_response(rv, status_code=404)


class GetProjectUserTestCase(MockedTestCase):

    def test_get_works(self):
        project_id = u'PID'
        tenant = doubles.make(self.mox, doubles.Tenant, id=project_id)
        users = [doubles.make(self.mox, doubles.User,
                              id=uid, name=(uid + ' name'))
                 for uid in (u'U1', u'U2', u'U3')]
        client = self.fake_client_set

        client.identity_admin.tenants.get(project_id).AndReturn(tenant)
        tenant.list_users().AndReturn(users)

        expected = {
            u'id': u'U2',
            u'name': u'U2 name',
            u'href': u'/v1/users/U2'
        }

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/projects/%s/users/U2' % project_id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_no_project(self):
        project_id = u'PID'
        self.fake_client_set.identity_admin.tenants.get(project_id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/projects/%s/users/U2' % project_id)
        self.check_and_parse_response(rv, status_code=404)

    def test_get_no_user(self):
        project_id = u'PID'
        tenant = doubles.make(self.mox, doubles.Tenant, id=project_id)
        users = [doubles.make(self.mox, doubles.User,
                              id=uid, name=(uid + ' name'))
                 for uid in (u'U1', u'U2', u'U3')]
        client = self.fake_client_set

        client.identity_admin.tenants.get(project_id).AndReturn(tenant)
        tenant.list_users().AndReturn(users)

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/projects/%s/users/OTHER' % project_id)
        self.check_and_parse_response(rv, status_code=404)


class AddAndRemoveProjectUserTestCase(MockedTestCase):

    def setUp(self):
        super(AddAndRemoveProjectUserTestCase, self).setUp()
        self.project_id = u'PID'
        self.user_id = u'UID'
        self.tenant = doubles.make(self.mox, doubles.Tenant,
                                   id=self.project_id)
        self.user = doubles.make(self.mox, doubles.User,
                                 id=self.user_id, name='username')

    def test_add_works(self):
        ia = self.fake_client_set.identity_admin

        ia.tenants.get(self.project_id).AndReturn(self.tenant)
        ia.users.get(self.user_id).AndReturn(self.user)
        ia.roles.list().AndReturn([
            doubles.make(self.mox, doubles.Role, id=u'AR', name=u'admin'),
            doubles.make(self.mox, doubles.Role, id=u'MR', name=u'member')
        ])
        self.tenant.add_user(self.user_id, u'MR')
        expected = {
            u'id': u'UID',
            u'name': u'username',
            u'href': u'/v1/users/UID'
        }

        self.mox.ReplayAll()
        params = {'id': self.user_id}
        rv = self.client.post('/v1/projects/%s/users/' % self.project_id,
                              content_type='application/json',
                              data=json.dumps(params))
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_add_without_role(self):
        ia = self.fake_client_set.identity_admin

        ia.tenants.get(self.project_id).AndReturn(self.tenant)
        ia.users.get(self.user_id).AndReturn(self.user)
        ia.roles.list().AndReturn([])

        self.mox.ReplayAll()
        params = {'id': self.user_id}
        rv = self.client.post('/v1/projects/%s/users/' % self.project_id,
                              content_type='application/json',
                              data=json.dumps(params))
        data = self.check_and_parse_response(rv, status_code=500)
        self.assertTrue('role not found' in data.get('message').lower())

    def test_remove_works(self):
        ia = self.fake_client_set.identity_admin

        ia.tenants.get(self.project_id).AndReturn(self.tenant)
        ia.users.get(self.user_id).AndReturn(self.user)
        self.user.list_roles(self.tenant).AndReturn([
            doubles.make(self.mox, doubles.Role, id=u'AR', name=u'admin'),
            doubles.make(self.mox, doubles.Role, id=u'MR', name=u'member')
        ])
        self.tenant.remove_user(u'UID', u'AR')
        self.tenant.remove_user(u'UID', u'MR')

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/projects/%s/users/%s'
                                % (self.project_id, self.user_id))
        self.check_and_parse_response(rv, status_code=204)

