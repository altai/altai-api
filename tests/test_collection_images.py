
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
import mox

from datetime import datetime
from tests import doubles
from tests.mocked import MockedTestCase, mock_client_set

from openstackclient_base import exceptions as osc_exc
from altai_api.collection import images


class StreamWithData(mox.Comparator):
    """Verify that a parameter is stream with given data"""

    def __init__(self, data):
        self.data = data

    def equals(self, rhs):
        real_data = rhs.read()
        return self.data == real_data


class ImageFromNovaWorks(MockedTestCase):
    maxDiff = None

    def test_image_from_nova_works(self):
        tenant = doubles.make(self.mox, doubles.Tenant,
                              id=u'TENANT', name=u'TestTenant')
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', name=u'TestImage', size=123456,
                             owner=tenant.id, created_at='2012-10-15T01:43:00',
                             disk_format=u'raw', container_format=u'bare',
                             checksum='831a05f7bdeadbabe5l1k3133715e7ea',
                             status='active')
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'name': u'TestImage',
            u'global': False,
            u'project': {
                u'id': u'TENANT',
                u'name': u'TestTenant',
                u'href': '/v1/projects/TENANT'
            },
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'raw',
            u'container-format': u'bare',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'active',
            u'tags': [],
            u'actions': {
                u'add-tags': '/v1/images/IMAGE/add-tags',
                u'remove-tags': '/v1/images/IMAGE/remove-tags',
            }
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            data = images._image_from_nova(image, tenant)
        self.assertEquals(data, expected)

    def test_global_image_from_nova(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', name=u'TestImage', size=123456,
                             owner=None, created_at='2012-10-15T01:43:00',
                             disk_format=u'raw', container_format=u'bare',
                             checksum='831a05f7bdeadbabe5l1k3133715e7ea',
                             status=u'active')
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'name': u'TestImage',
            u'global': True,
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'raw',
            u'container-format': u'bare',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'active',
            u'tags': [],
            u'actions': {
                u'add-tags': '/v1/images/IMAGE/add-tags',
                u'remove-tags': '/v1/images/IMAGE/remove-tags',
            }
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            image.owner = images.default_tenant_id()
            data = images._image_from_nova(image)
        self.assertEquals(data, expected)


    def test_queued_image_from_nova(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', name=u'TestImage', size=123456,
                             owner=None, created_at='2012-10-15T01:43:00',
                             disk_format=u'raw', container_format=u'bare',
                             checksum='831a05f7bdeadbabe5l1k3133715e7ea',
                             status=u'queued')
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'name': u'TestImage',
            u'global': True,
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'raw',
            u'container-format': u'bare',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'queued',
            u'tags': [],
            u'actions': {
                u'add-tags': '/v1/images/IMAGE/add-tags',
                u'remove-tags': '/v1/images/IMAGE/remove-tags',
                u'upload': '/v1/images/IMAGE/data',
            }
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            image.owner = images.default_tenant_id()
            data = images._image_from_nova(image)
        self.assertEquals(data, expected)


    def test_global_ami_image_from_nova(self):
        image_properties = {
            u'image_location': u'local',
            u'kernel_id': u'KERNEL',
            u'ramdisk_id': u'RAMDISK',
            u'architecture': u'x86_64',
        }
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', name=u'TestImage', size=123456,
                             owner=None, created_at='2012-10-15T01:43:00',
                             disk_format=u'ami', container_format=u'ami',
                             checksum='831a05f7bdeadbabe5l1k3133715e7ea',
                             status=u'active', properties=image_properties)
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'name': u'TestImage',
            u'global': True,
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'ami',
            u'container-format': u'ami',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'active',
            u'tags': [],
            u'actions': {
                u'add-tags': '/v1/images/IMAGE/add-tags',
                u'remove-tags': '/v1/images/IMAGE/remove-tags',
            },
            u'kernel': u'KERNEL',
            u'ramdisk': u'RAMDISK'
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            image.owner = images.default_tenant_id()
            data = images._image_from_nova(image)
        self.assertEquals(data, expected)


class ListImagesTestCase(MockedTestCase):

    def setUp(self):
        super(ListImagesTestCase, self).setUp()
        self.mox.StubOutWithMock(images, 'client_set_for_tenant')
        self.mox.StubOutWithMock(images, '_image_from_nova')
        self.tenants = [
            doubles.make(self.mox, doubles.Tenant, id=u'SYS', name=u'systenant'),
            doubles.make(self.mox, doubles.Tenant, id=u'PID', name=u'ptest'),
        ]
        self.images = [
            doubles.make(self.mox, doubles.Image, id=u'IMAGE1', owner=u'SYS'),
            doubles.make(self.mox, doubles.Image, id=u'IMAGE2', owner=u'PID'),
            doubles.make(self.mox, doubles.Image, id=u'IMAGE3', owner=u'PID'),
        ]


    def test_list_works(self):
        client = self.fake_client_set
        tcs1 = mock_client_set(self.mox)
        tcs2 = mock_client_set(self.mox)

        client.identity_admin.tenants.list().AndReturn(self.tenants)
        images.client_set_for_tenant(tenant_id=u'SYS').AndReturn(tcs1)
        tcs1.image.images.list().AndReturn([self.images[0]])
        images._image_from_nova(self.images[0], self.tenants[0]).AndReturn('I1')

        images.client_set_for_tenant(tenant_id=u'PID').AndReturn(tcs2)
        tcs2.image.images.list().AndReturn([self.images[1], self.images[2]])
        images._image_from_nova(self.images[1], self.tenants[1]).AndReturn('I2')
        images._image_from_nova(self.images[2], self.tenants[1]).AndReturn('I3')

        expected = {
            u'collection': {
                u'name': u'images',
                u'size': 3
            },
            u'images': [ 'I1', 'I2', 'I3' ]
        }


        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/')
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_image_works(self):
        client = self.fake_client_set
        image = self.images[-1]

        client.image.images.get(image.id).AndReturn(image)
        images._image_from_nova(image).AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/%s' % image.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_image_not_found(self):
        client = self.fake_client_set
        image_id = u'IID'

        client.image.images.get(image_id)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/%s' % image_id)
        self.check_and_parse_response(rv, status_code=404)

    def test_image_deleted(self):
        client = self.fake_client_set
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', owner=u'PID', deleted=True)

        client.image.images.get(image.id).AndReturn(image)

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/%s' % image.id)
        self.check_and_parse_response(rv, status_code=404)


class UpdateImageTestCase(MockedTestCase):

    def setUp(self):
        super(UpdateImageTestCase, self).setUp()
        self.mox.StubOutWithMock(images, '_image_from_nova')
        self.mox.StubOutWithMock(images, '_fetch_image')

    def interact(self, iid, params, expected_status_code=200):
        rv = self.client.put('/v1/images/%s' % iid,
                             data=json.dumps(params),
                             content_type='application/json')
        return self.check_and_parse_response(
            rv, status_code=expected_status_code)


    def test_update_image_name(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', owner=u'PID')

        images._fetch_image(image.id).AndReturn(image)
        image.update(name='UPDATED')
        images._fetch_image(image.id).AndReturn('UPDATED IMAGE')
        images._image_from_nova('UPDATED IMAGE').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(image.id, {'name': 'UPDATED'})
        self.assertEquals(data, 'REPLY')


class CreateImageTestCase(MockedTestCase):
    def setUp(self):
        super(CreateImageTestCase, self).setUp()
        self.mox.StubOutWithMock(images, '_image_from_nova')
        self.mox.StubOutWithMock(images, 'client_set_for_tenant')

    def interact(self, params, expected_status_code=200):
        rv = self.client.post('/v1/images/',
                              data=json.dumps(params),
                              content_type='application/json')
        return self.check_and_parse_response(
                rv, status_code=expected_status_code)


    def test_create_global_image(self):
        params = {
            u'name': u'TestImage',
            u'global': True,
            u'disk-format': u'raw',
            u'container-format': u'bare',
        }

        self.fake_client_set.image.images.create(
            name=u'TestImage',
            disk_format=u'raw',
            container_format=u'bare',
            is_public=True,
            properties={}).AndReturn('QueuedImage')
        images._image_from_nova('QueuedImage').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')


    def test_create_local_requires_project(self):
        params = {
            u'name': u'TestImage',
            u'global': False,
            u'disk-format': u'raw',
            u'container-format': u'bare',
        }
        self.mox.ReplayAll()
        self.interact(params, expected_status_code=400)

    def test_create_global_in_project_fails(self):
        params = {
            u'name': u'TestImage',
            u'project': u'PROJECT_ID',
            u'global': True,
            u'disk-format': u'raw',
            u'container-format': u'bare',
        }
        self.mox.ReplayAll()
        self.interact(params, expected_status_code=400)

    def test_create_local_image(self):
        params = {
            u'name': u'TestImage',
            u'project': u'PROJECT_ID',
            u'disk-format': u'raw',
            u'container-format': u'bare',
        }
        tcs = mock_client_set(self.mox)

        images.client_set_for_tenant(u'PROJECT_ID').AndReturn(tcs)
        tcs.image.images.create(
            name=u'TestImage',
            disk_format=u'raw',
            container_format=u'bare',
            is_public=False,
            properties={}).AndReturn('QueuedImage')
        images._image_from_nova('QueuedImage').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_create_ami_image(self):
        params = {
            u'name': u'TestImage',
            u'global': True,
            u'disk-format': u'ami',
            u'container-format': u'ami',
            u'kernel': u'KERNEL_ID',
            u'ramdisk': u'RAMDISK_ID'
        }

        self.fake_client_set.image.images.create(
            name=u'TestImage',
            disk_format=u'ami',
            container_format=u'ami',
            is_public=True,
            properties={
                u'kernel_id': u'KERNEL_ID',
                u'ramdisk_id': u'RAMDISK_ID'
            }).AndReturn('QueuedImage')
        images._image_from_nova('QueuedImage').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(params)
        self.assertEquals(data, 'REPLY')

    def test_upload_image(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', status='queued',
                             deleted='False', name=u'TestImage')
        data = 'DATA DATA DATA DATA'

        self.fake_client_set.image.images.get(image.id).AndReturn(image)
        image.update(data=StreamWithData(data), size=len(data))

        self.mox.ReplayAll()
        rv = self.client.put('/v1/images/IMAGE/data',
                             data=data,
                             content_type='application/octet-stream')
        self.check_and_parse_response(rv, status_code=204)

    def test_upload_checks_content_type(self):
        self.mox.ReplayAll()
        rv = self.client.put('/v1/images/IMAGE/data',
                             data='{}',
                             content_type='application/json')
        self.check_and_parse_response(rv, status_code=400)

    def test_upload_checks_expectations(self):
        data = 'DATA DATA DATA DATA'
        self.mox.ReplayAll()
        rv = self.client.put('/v1/images/IMAGE/data',
                             data=data,
                             headers={'Expect': '202-accepted'},
                             content_type='application/octet-stream')
        self.check_and_parse_response(rv, status_code=417)

    def test_upload_checks_status(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', status='active',
                             deleted='False', name=u'TestImage')
        data = 'DATA DATA DATA DATA'

        self.fake_client_set.image.images.get(image.id).AndReturn(image)

        self.mox.ReplayAll()
        rv = self.client.put('/v1/images/IMAGE/data',
                             data=data,
                             content_type='application/octet-stream')
        self.check_and_parse_response(rv, status_code=405)


class RemoveImageTestCase(MockedTestCase):

    def test_remove_image_works(self):
        client = self.fake_client_set
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', owner=u'PID')

        client.image.images.get(image.id).AndReturn(image)
        image.delete()
        self.mox.ReplayAll()
        rv = self.client.delete(u'/v1/images/%s' % image.id)
        self.check_and_parse_response(rv, status_code=204)

    def test_remove_image_not_found(self):
        client = self.fake_client_set
        image_id = u'IID'

        client.image.images.get(image_id).AndRaise(osc_exc.NotFound('failure'))
        self.mox.ReplayAll()
        rv = self.client.delete(u'/v1/images/%s' % image_id)
        self.check_and_parse_response(rv, status_code=404)

