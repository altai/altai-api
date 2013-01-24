
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

import uuid
from flask import json

import openstackclient_base.exceptions as osc_exc

from tests import doubles
from tests.mocked import MockedTestCase

from altai_api.blueprints import instance_types


# for multiplying
_GB = 1024 * 1024 * 1024


class InstanceTypesToNovaTestCase(MockedTestCase):

    def test_from_nova(self):
        flavor = doubles.make(self.mox, doubles.Flavor,
                              id=u'42',
                              name=u'my test',
                              vcpus=4,
                              ram=8192,
                              disk=10,
                              ephemeral=80)
        expected = {
            u'id': u'42',
            u'href': u'/v1/instance-types/42',
            u'name': u'my test',
            u'cpus': 4,
            u'ram': 8 * _GB,
            u'root-size': 10 * _GB,
            u'ephemeral-size': 80 * _GB
        }
        with self.app.test_request_context():
            res = instance_types._instance_type_from_nova(flavor)
        self.assertEquals(expected, res)

    def test_for_nova_works(self):
        data = {
            u'name': u'my test',
            u'cpus': 4,
            u'ram': 8 * _GB,
            u'root-size': 10 * _GB,
            u'ephemeral-size': 80 * _GB
        }
        expected = {
            u'name': u'my test',
            u'vcpus': 4,
            u'ram': 8192,
            u'disk': 10,
            u'ephemeral': 80
        }
        converted = instance_types._instance_type_for_nova(data)
        self.assertEquals(converted, expected)


class InstanceTypesListTestCase(MockedTestCase):

    def setUp(self):
        super(InstanceTypesListTestCase, self).setUp()
        self.mox.StubOutWithMock(instance_types, '_instance_type_from_nova')

    def test_no_flavors(self):
        expected = {
            'collection': {
                'name': 'instance-types',
                'size': 0
            },
            'instance-types': []
        }

        self.fake_client_set.compute.flavors.list().AndReturn([])
        self.mox.ReplayAll()
        rv = self.client.get('/v1/instance-types/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(expected, data)

    def test_two_flavors(self):
        reply = [
            { u'name': u'fake1' },
            { u'name': u'fake2' }
        ]
        expected = {
            u'collection': {
                u'name': u'instance-types',
                u'size': 2,
            },
            u'instance-types': reply
        }

        self.fake_client_set.compute.flavors.list().AndReturn(['F1', 'F2'])
        instance_types._instance_type_from_nova('F1').AndReturn(reply[0])
        instance_types._instance_type_from_nova('F2').AndReturn(reply[1])

        self.mox.ReplayAll()

        rv = self.client.get('/v1/instance-types/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(expected, data)

    def test_get_one(self):
        flavors = [
            doubles.make(self.mox, doubles.Flavor, id="42111"),
            doubles.make(self.mox, doubles.Flavor, id="42"),
            doubles.make(self.mox, doubles.Flavor, id="421"),
        ]
        self.fake_client_set.compute.flavors.list().AndReturn(flavors)
        instance_types._instance_type_from_nova(flavors[1]).AndReturn('REPLY')

        self.mox.ReplayAll()

        rv = self.client.get('/v1/instance-types/42')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_flavor_not_found(self):
        self.fake_client_set.compute.flavors.list().AndReturn([])

        self.mox.ReplayAll()
        rv = self.client.get('/v1/instance-types/42')
        self.check_and_parse_response(rv, status_code=404)


class InstanceTypesCreateTestCase(MockedTestCase):

    def setUp(self):
        super(InstanceTypesCreateTestCase, self).setUp()
        self.mox.StubOutWithMock(instance_types, '_instance_type_for_nova')
        self.mox.StubOutWithMock(instance_types, '_instance_type_from_nova')
        self.mox.StubOutWithMock(uuid, 'uuid4')

        self.fake_params = {
            u'name': 'fake',
            u'cpus': 42,
            u'ram': 4 * _GB,
            u'root-size': 7 * _GB,
            u'ephemeral-size': 11 * _GB,
        }

    def interact(self, data, expected_status_code=200):
        rv = self.client.post('/v1/instance-types/',
                              content_type='application/json',
                              data=json.dumps(data))
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)

    def test_create_instance_type(self):
        flavorid = uuid.UUID('1beeece5-e4e6-4f50-898d-15c3ab393abf')
        for_nova = {
            u'name': u'my test',
            u'vcpus': 4,
            u'ram': 8192,
            u'disk': 10,
            u'ephemeral': 80
        }

        instance_types._instance_type_for_nova(self.fake_params)\
                .AndReturn(for_nova)
        uuid.uuid4().AndReturn(flavorid)
        for_nova['flavorid'] = flavorid.int
        self.fake_client_set.compute.flavors.create(**for_nova)\
                .AndReturn('FLAVOR42')
        instance_types._instance_type_from_nova('FLAVOR42').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(self.fake_params)
        self.assertEquals(data, 'REPLY')

    def test_create_rejects_id(self):
        data = {
            u'id': u'42',
            u'name': u'my test',
            u'cpus': 4,
            u'ram': 8 * _GB,
            u'root-size': 10 * _GB,
            u'ephemeral-size': 80 * _GB
        }
        self.mox.ReplayAll()
        self.interact(data, expected_status_code=400)

    def test_instance_type_exists(self):
        flavorid = uuid.UUID('1beeece5-e4e6-4f50-898d-15c3ab393abf')
        for_nova = {
            u'name': u'my test',
            u'vcpus': 4,
            u'ram': 8192,
            u'disk': 10,
            u'ephemeral': 80
        }

        instance_types._instance_type_for_nova(self.fake_params)\
                .AndReturn(for_nova)
        uuid.uuid4().AndReturn(flavorid)
        for_nova['flavorid'] = flavorid.int
        self.fake_client_set.compute.flavors.create(**for_nova)\
                .AndRaise(osc_exc.HttpException(409, 'failure'))

        self.mox.ReplayAll()
        self.interact(self.fake_params, expected_status_code=400)


class InstanceTypeDeleteTestCase(MockedTestCase):

    def test_delete_instance_type_works(self):
        self.fake_client_set.compute.flavors.delete(u'42')
        self.mox.ReplayAll()
        rv = self.client.delete('/v1/instance-types/42')
        self.check_and_parse_response(rv, status_code=204)

    def test_delete_instance_type_not_found(self):
        self.fake_client_set.compute.flavors.delete(u'42')\
                .AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        rv = self.client.delete('/v1/instance-types/42')
        self.check_and_parse_response(rv, status_code=404)

