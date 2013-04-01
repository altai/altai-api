
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

import json
import mox

from datetime import datetime
from tests import doubles
from tests.mocked import MockedTestCase, mock_client_set

from openstackclient_base import exceptions as osc_exc
from altai_api.blueprints import images


class StreamWithData(mox.Comparator):
    """Verify that a parameter is stream with given data"""

    def __init__(self, data):
        self.data = data

    def equals(self, rhs):
        real_data = rhs.read()
        return self.data == real_data


class ImageFromNovaWorks(MockedTestCase):
    maxDiff = None

    def test_image_to_view_works(self):
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
            u'data-href': '/v1/images/IMAGE/data',
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
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            data = images._image_to_view(image, tenant)
        self.assertEquals(data, expected)

    def test_global_image_to_view(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', name=u'TestImage', size=123456,
                             owner=None, created_at='2012-10-15T01:43:00',
                             disk_format=u'raw', container_format=u'bare',
                             checksum='831a05f7bdeadbabe5l1k3133715e7ea',
                             status=u'active')
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'data-href': '/v1/images/IMAGE/data',
            u'name': u'TestImage',
            u'global': True,
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'raw',
            u'container-format': u'bare',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'active',
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            image.owner = images.auth.default_tenant_id()
            data = images._image_to_view(image)
        self.assertEquals(data, expected)

    def test_queued_image_to_view(self):
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', name=u'TestImage', size=123456,
                             owner=None, created_at='2012-10-15T01:43:00',
                             disk_format=u'raw', container_format=u'bare',
                             checksum='831a05f7bdeadbabe5l1k3133715e7ea',
                             status=u'queued')
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'data-href': '/v1/images/IMAGE/data',
            u'name': u'TestImage',
            u'global': True,
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'raw',
            u'container-format': u'bare',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'queued',
        }

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            image.owner = images.auth.default_tenant_id()
            data = images._image_to_view(image)
        self.assertEquals(data, expected)

    def test_global_ami_image_to_view(self):
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
        kernel = doubles.make(self.mox, doubles.Image,
                              id=u'KERNEL', name=u'TestKernel',
                              disk_format=u'aki', container_format=u'aki')
        ramdisk = doubles.make(self.mox, doubles.Image,
                               id=u'RAMDISK', name=u'TestRamdisk',
                               disk_format=u'ari', container_format=u'ari')
        expected = {
            u'id': u'IMAGE',
            u'href': '/v1/images/IMAGE',
            u'data-href': '/v1/images/IMAGE/data',
            u'name': u'TestImage',
            u'global': True,
            u'created': datetime(2012, 10, 15, 01, 43, 00),
            u'disk-format': u'ami',
            u'container-format': u'ami',
            u'md5sum': '831a05f7bdeadbabe5l1k3133715e7ea',
            u'size': 123456,
            u'status': u'active',
            u'kernel': {
                u'id': u'KERNEL',
                u'name': u'TestKernel',
                u'href': '/v1/images/KERNEL'
            },
            u'ramdisk': {
                u'id': u'RAMDISK',
                u'name': u'TestRamdisk',
                u'href': '/v1/images/RAMDISK'
            }
        }

        images_mgr = self.fake_client_set.image.images
        images_mgr.get(u'KERNEL').AndReturn(kernel)
        images_mgr.get(u'RAMDISK').AndReturn(ramdisk)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            image.owner = images.auth.default_tenant_id()
            data = images._image_to_view(image)
        self.assertEquals(data, expected)


class ListImagesTestCase(MockedTestCase):

    def setUp(self):
        super(ListImagesTestCase, self).setUp()
        self.mox.StubOutWithMock(images.auth, 'client_set_for_tenant')
        self.mox.StubOutWithMock(images.auth, 'default_tenant_id')
        self.mox.StubOutWithMock(images.auth, 'assert_admin')
        self.mox.StubOutWithMock(images.auth, 'api_client_set')
        self.mox.StubOutWithMock(images, '_image_to_view')
        self.tenants = [
            doubles.make(self.mox, doubles.Tenant, id='SYS', name='systenant'),
            doubles.make(self.mox, doubles.Tenant, id='PID', name='ptest'),
        ]
        self.images = [
            doubles.make(self.mox, doubles.Image, id='IMAGE1', owner='SYS'),
            doubles.make(self.mox, doubles.Image, id='IMAGE2', owner='PID'),
            doubles.make(self.mox, doubles.Image, id='IMAGE3', owner='PID'),
        ]

    def test_list_works(self):
        client = self.fake_client_set

        client.identity_admin.tenants.list().AndReturn(self.tenants)
        images.auth.default_tenant_id().AndReturn('SYS')
        client.image.images.list(filters={'is_public': None})\
                .AndReturn(self.images)

        images._image_to_view(self.images[0], None).AndReturn('I1')
        images._image_to_view(self.images[1],
                                self.tenants[1]).AndReturn('I2')
        images._image_to_view(self.images[2],
                                self.tenants[1]).AndReturn('I3')

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

    def test_list_missing_project(self):
        client = self.fake_client_set

        images.auth.default_tenant_id().AndReturn('SYS')
        client.identity_admin.tenants.list().AndReturn([self.tenants[0]])
        client.image.images.list(filters={'is_public': None})\
                .AndReturn(self.images)

        images._image_to_view(self.images[0], None).AndReturn('I1')
        images._image_to_view(self.images[1], None).AndReturn('I2')
        images._image_to_view(self.images[2], None).AndReturn('I3')

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

    def test_list_for_project(self):
        tcs = mock_client_set(self.mox)
        tenant = self.tenants[1]

        self.fake_client_set.identity_admin.tenants.get(tenant.id)\
                .AndReturn(tenant)
        images.auth.client_set_for_tenant(tenant.id, fallback_to_api=True) \
                .AndReturn(tcs)
        tcs.image.images.list(filters={'is_public': None}) \
                .AndReturn(['ii1', 'ii2'])
        images._image_to_view('ii1', self.tenants[0]).AndReturn('I1')
        images._image_to_view('ii2', self.tenants[1]).AndReturn('I2')

        expected = {
            u'collection': {
                u'name': u'images',
                u'size': 2
            },
            u'images': [ 'I1', 'I2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/?project:for=%s' % tenant.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_list_for_non_existing_project(self):
        tenant = self.tenants[1]

        self.fake_client_set.identity_admin.tenants.get(tenant.id)\
                .AndRaise(osc_exc.NotFound('failure'))
        expected = {
            u'collection': {
                u'name': u'images',
                u'size': 0
            },
            u'images': [ ]
        }

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/?project:for=%s' % tenant.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_get_image_works(self):
        client = self.fake_client_set
        image = self.images[-1]

        client.image.images.get(image.id).AndReturn(image)
        images.auth.default_tenant_id().AndReturn('SYS')
        images._image_to_view(image).AndReturn('REPLY')

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


class ImagesAsUserTestCase(MockedTestCase):
    IS_ADMIN = False

    def setUp(self):
        super(ImagesAsUserTestCase, self).setUp()
        self.mox.StubOutWithMock(images.auth, 'client_set_for_tenant')
        self.mox.StubOutWithMock(images.auth, 'default_tenant_id')
        self.mox.StubOutWithMock(images.auth, 'current_user_project_ids')
        self.mox.StubOutWithMock(images, '_image_to_view')
        self.tenant = doubles.make(self.mox, doubles.Tenant,
                                   id='PID', name='ptest')
        self.images = [
            doubles.make(self.mox, doubles.Image, id='IMAGE1', owner='SYS'),
            doubles.make(self.mox, doubles.Image, id='IMAGE2', owner='PID'),
            doubles.make(self.mox, doubles.Image, id='IMAGE3', owner='PID'),
        ]

    def test_list_works(self):
        client = self.fake_client_set

        client.identity_public.tenants.list().AndReturn([self.tenant])
        images.auth.default_tenant_id().AndReturn('SYS')
        client.image.images.list(filters={'is_public': None})\
                .AndReturn(self.images)

        images._image_to_view(self.images[0], None).AndReturn('I1')
        images._image_to_view(self.images[1],
                                self.tenant).AndReturn('I2')
        images._image_to_view(self.images[2],
                                self.tenant).AndReturn('I3')

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

    def test_list_for_project(self):
        tcs = mock_client_set(self.mox)

        self.fake_client_set.identity_admin.tenants.get(self.tenant.id)\
                .AndReturn(self.tenant)
        images.auth.client_set_for_tenant(self.tenant.id,
                                          fallback_to_api=False) \
                .AndReturn(tcs)
        tcs.image.images.list(filters={'is_public': None}) \
                .AndReturn(['ii1'])
        images._image_to_view('ii1', self.tenant).AndReturn('I1')

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/?project:for=%s' % self.tenant.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data.get('images'), ['I1'])

    def test_list_eq_project(self):
        # differs with previous in request argument and list filters
        tcs = mock_client_set(self.mox)
        fake_image_dict = {
            'name': 'I1',
            'project': { 'id': self.tenant.id }
        }

        self.fake_client_set.identity_admin.tenants.get(self.tenant.id)\
                .AndReturn(self.tenant)
        images.auth.client_set_for_tenant(self.tenant.id,
                                          fallback_to_api=False) \
                .AndReturn(tcs)
        tcs.image.images.list(filters={'is_public': False}) \
                .AndReturn(['ii1'])
        images._image_to_view('ii1', self.tenant).AndReturn(fake_image_dict)

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/?project:eq=%s' % self.tenant.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data.get('images'), [fake_image_dict])

    def test_list_in_project(self):
        # differs with previous only in request argument
        tcs = mock_client_set(self.mox)
        fake_image_dict = {
            'name': 'I1',
            'project': { 'id': self.tenant.id }
        }

        self.fake_client_set.identity_admin.tenants.get(self.tenant.id)\
                .AndReturn(self.tenant)
        images.auth.client_set_for_tenant(self.tenant.id,
                                          fallback_to_api=False) \
                .AndReturn(tcs)
        tcs.image.images.list(filters={'is_public': False}) \
                .AndReturn(['ii1'])
        images._image_to_view('ii1', self.tenant).AndReturn(fake_image_dict)

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/?project:in=%s' % self.tenant.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data.get('images'), [fake_image_dict])

    def test_get_image_works(self):
        client = self.fake_client_set
        image = self.images[-1]

        client.image.images.get(image.id).AndReturn(image)
        images.auth.default_tenant_id().AndReturn('SYS')
        images.auth.current_user_project_ids().AndReturn(['PID'])
        images._image_to_view(image).AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/%s' % image.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_image_other_project(self):
        client = self.fake_client_set
        image = self.images[-1]

        client.image.images.get(image.id).AndReturn(image)
        images.auth.default_tenant_id().AndReturn('SYS')
        images.auth.current_user_project_ids().AndReturn(['PID2'])

        self.mox.ReplayAll()
        rv = self.client.get(u'/v1/images/%s' % image.id)
        self.check_and_parse_response(rv, status_code=403)

    def test_remove_image_works(self):
        client = self.fake_client_set
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', owner=u'PID')

        client.image.images.get(image.id).AndReturn(image)
        images.auth.default_tenant_id().AndReturn('SYS')
        images.auth.current_user_project_ids().AndReturn(['PID'])
        image.delete()

        self.mox.ReplayAll()
        rv = self.client.delete(u'/v1/images/%s' % image.id)
        self.check_and_parse_response(rv, status_code=204)

    def test_remove_image_other_project(self):
        client = self.fake_client_set
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', owner=u'PID')

        client.image.images.get(image.id).AndReturn(image)
        images.auth.default_tenant_id().AndReturn('SYS')
        images.auth.current_user_project_ids().AndReturn(['PID2'])

        self.mox.ReplayAll()
        rv = self.client.delete(u'/v1/images/%s' % image.id)
        self.check_and_parse_response(rv, status_code=403)

    def test_remove_global_image(self):
        client = self.fake_client_set
        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMAGE', owner=u'SYS')

        client.image.images.get(image.id).AndReturn(image)
        images.auth.default_tenant_id().AndReturn('SYS')

        self.mox.ReplayAll()
        rv = self.client.delete(u'/v1/images/%s' % image.id)
        self.check_and_parse_response(rv, status_code=403)


class UpdateImageTestCase(MockedTestCase):

    def setUp(self):
        super(UpdateImageTestCase, self).setUp()
        self.mox.StubOutWithMock(images, '_image_to_view')
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

        images._fetch_image(image.id, to_modify=True).AndReturn(image)
        image.update(name='UPDATED')
        images._fetch_image(image.id, to_modify=False)\
                .AndReturn('UPDATED IMAGE')
        images._image_to_view('UPDATED IMAGE').AndReturn('REPLY')

        self.mox.ReplayAll()
        data = self.interact(image.id, {'name': 'UPDATED'})
        self.assertEquals(data, 'REPLY')


class CreateImageTestCase(MockedTestCase):
    def setUp(self):
        super(CreateImageTestCase, self).setUp()
        self.mox.StubOutWithMock(images, '_image_to_view')
        self.mox.StubOutWithMock(images.auth, 'client_set_for_tenant')
        self.mox.StubOutWithMock(images.auth, 'assert_admin')
        self.mox.StubOutWithMock(images.auth, 'api_client_set')

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

        images.auth.assert_admin()
        self.fake_client_set.image.images.create(
            name=u'TestImage',
            disk_format=u'raw',
            container_format=u'bare',
            is_public=True,
            properties={}).AndReturn('QueuedImage')
        images._image_to_view('QueuedImage').AndReturn('REPLY')

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

        images.auth.client_set_for_tenant(u'PROJECT_ID').AndReturn(tcs)
        tcs.image.images.create(
            name=u'TestImage',
            disk_format=u'raw',
            container_format=u'bare',
            is_public=False,
            properties={}).AndReturn('QueuedImage')
        images._image_to_view('QueuedImage').AndReturn('REPLY')

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

        images.auth.assert_admin()
        self.fake_client_set.image.images.create(
            name=u'TestImage',
            disk_format=u'ami',
            container_format=u'ami',
            is_public=True,
            properties={
                u'kernel_id': u'KERNEL_ID',
                u'ramdisk_id': u'RAMDISK_ID'
            }).AndReturn('QueuedImage')
        images._image_to_view('QueuedImage').AndReturn('REPLY')

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

    def test_upload_checks_content_length(self):
        # NOTE(imelnikov): one cannot make normal request context without
        # content length, but if we really want, we can, using mox
        with self.app.test_request_context():
            self.mox.StubOutWithMock(images, 'request')
            images.request.content_type = 'application/octet-stream'
            images.request.content_length = None
            self.mox.ReplayAll()
            self.assertAborts(411, images.upload_image_data, '42')

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


class LinkForImageTestCase(MockedTestCase):
    def test_link_for_image(self):
        expected = {
            'id': 'IMG',
            'href': '/v1/images/IMG',
            'name': 'test image'
        }
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = images.link_for_image('IMG', 'test image')
        self.assertEquals(result, expected)

    def test_link_for_image_fetches(self):
        expected = {
            'id': 'IMG',
            'href': '/v1/images/IMG',
            'name': 'test image'
        }

        image = doubles.make(self.mox, doubles.Image,
                             id=u'IMG', owner=u'PID', name='test image')
        self.fake_client_set.image.images.get('IMG').AndReturn(image)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = images.link_for_image('IMG')
        self.assertEquals(result, expected)

    def test_link_for_image_not_found(self):
        expected = {
            'id': 'IMG',
            'href': '/v1/images/IMG',
            'name': None
        }

        self.fake_client_set.image.images.get('IMG') \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.install_fake_auth()
            result = images.link_for_image('IMG')
        self.assertEquals(result, expected)


class ImageDownloadTestCase(MockedTestCase):

    def setUp(self):
        super(ImageDownloadTestCase, self).setUp()
        self.mox.StubOutWithMock(images, '_fetch_image')
        self.image = doubles.make(self.mox, doubles.Image,
                                  id=u'IMG', owner=u'PID', name='test image',
                                  status='active', size=42)

    def test_get_image_data_works(self):
        data = 'a' * 42
        images._fetch_image('IMG', to_modify=False).AndReturn(self.image)
        self.image.data().AndReturn(data)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/images/IMG/data')
        self.assertEquals(rv.status_code, 200)
        self.assertTrue('X-GD-Altai-Implementation' in rv.headers)
        self.assertEquals(rv.content_length, 42)
        self.assertEquals(rv.content_type, 'application/octet-stream')
        self.assertEquals(rv.data, data)

    def test_get_image_data_late_404(self):
        images._fetch_image('IMG', to_modify=False).AndReturn(self.image)
        self.image.data().AndRaise(osc_exc.NotFound('gone'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/images/IMG/data')
        self.check_and_parse_response(rv, status_code=404)

    def test_get_image_data_too_eraly(self):
        self.image.status = 'queued'
        images._fetch_image('IMG', to_modify=False).AndReturn(self.image)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/images/IMG/data')
        self.check_and_parse_response(rv, status_code=405)

