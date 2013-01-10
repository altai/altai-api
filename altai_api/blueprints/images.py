
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

from flask import url_for, g, Blueprint, abort, request

from altai_api.utils import make_json_response
from altai_api.utils import make_collection_response
from altai_api.utils import parse_collection_request

from altai_api.utils.decorators import data_handler, root_endpoint

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils.parsers import timestamp_from_openstack
from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.blueprints.projects import link_for_project
from altai_api.authentication import client_set_for_tenant, default_tenant_id


images = Blueprint('images', __name__)


def _fetch_image(image_id):
    try:
        image = g.client_set.image.images.get(image_id)
    except osc_exc.NotFound:
        abort(404)
    # NOTE(imelnikov): yes, nova may return False as string
    if image.deleted and image.deleted != 'False':
        abort(404)
    return image


def link_for_image(image_id, image_name=None):
    if image_name is None:
        image_name = g.client_set.image.images.get(image_id).name
    return {
        u'id': image_id,
        u'href': url_for('images.get_image', image_id=image_id),
        u'name': image_name
    }


def _image_from_nova(image, tenant=None):
    result = link_for_image(image.id, image.name)
    result.update({
        u'status': image.status,
        u'disk-format': image.disk_format,
        u'container-format': image.container_format,
        u'created': timestamp_from_openstack(image.created_at),
        u'md5sum': image.checksum,
        u'size': image.size,
        u'tags': [],
        u'actions': {
            u'add-tags': url_for('images.add_image_tags', image_id=image.id),
            u'remove-tags': url_for('images.remove_image_tags',
                                    image_id=image.id)
        }
    })
    if image.owner == default_tenant_id():
        result[u'global'] = True
    else:
        result[u'global'] = False
        result[u'project'] = link_for_project(image.owner,
                                              tenant.name if tenant else None)

    if 'kernel_id' in image.properties:
        result['kernel'] = link_for_image(image.properties['kernel_id'])
    if 'ramdisk_id' in image.properties:
        result['ramdisk'] = link_for_image(image.properties['ramdisk_id'])

    if image.status == 'queued':
        result['actions']['upload'] = url_for('images.upload_image_data',
                                              image_id=image.id)
    return result


def list_all_images():
    """Get list of all images from all tenants"""
    # NOTE(imelnikov): When is_public is True (the default), images
    # available for current tenant are returned (public images and
    # images from current tenant). When is_public is set to None
    # explicitly, current tenant is ignored.
    return g.client_set.image.images.list(filters={'is_public': None})


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('format'),
    st.Timestamp('created'),
    st.Boolean('global'),
    st.LinkObject('project')
))


@images.route('/', methods=('GET',))
@root_endpoint('images')
def list_images():
    parse_collection_request(_SCHEMA)

    tenants = g.client_set.identity_admin.tenants.list()
    tenant_dict = dict(((tenant.id, tenant) for tenant in tenants))

    result = [_image_from_nova(image,
                               tenant_dict[image.owner])
              for image in list_all_images()]
    return make_collection_response(u'images', result)


@images.route('/<image_id>', methods=('GET',))
def get_image(image_id):
    image = _fetch_image(image_id)
    return make_json_response(_image_from_nova(image))


@images.route('/<image_id>', methods=('PUT',))
def update_image(image_id):
    data = request.json
    fields_to_update = {}
    image = _fetch_image(image_id)

    if 'name' in data:
        fields_to_update['name'] = data['name']
    if fields_to_update:
        image.update(**fields_to_update)
        image = _fetch_image(image_id)

    return make_json_response(_image_from_nova(image))


def _assert_param_absent(name, data):
    if name in data:
        raise exc.UnknownElement(name)


@images.route('/', methods=('POST',))
def create_image():
    data = request.json

    is_public = data.get('global', 'project' not in data)
    if is_public:
        _assert_param_absent('project', data)
        image_mgr = g.client_set.image.images
    else:
        if 'project' not in data:
            raise exc.MissingElement('project')
        # TODO(imelnikov): check project existance
        image_mgr = client_set_for_tenant(data['project']).image.images

    props = {}
    if data['disk-format'] == 'ami':
        # TODO(imelnikov): check that images have correct types
        if 'kernel' in data:
            props['kernel_id'] = data['kernel']
        if 'ramdisk' in data:
            props['ramdisk_id'] = data['ramdisk']
    else:
        _assert_param_absent('kernel', data)
        _assert_param_absent('ramdisk', data)

    image = image_mgr.create(
        name=data['name'],
        disk_format=data['disk-format'],
        container_format=data['container-format'],
        is_public=is_public,
        properties=props)

    return make_json_response(_image_from_nova(image))


@images.route('/<image_id>', methods=('DELETE',))
def remove_image(image_id):
    image = _fetch_image(image_id)
    #TODO(imelnikov): permissions check
    image.delete()
    return make_json_response(None, status_code=204)


@images.route('/<image_id>/data', methods=('PUT',))
@data_handler
def upload_image_data(image_id):
    # first, we have to validate request
    if request.content_type != 'application/octet-stream':
        raise exc.InvalidRequest('Unsupported content type: %s'
                                 % request.content_type)
    if request.content_length is None:
        abort(411)  # Length required
    expect = request.headers.get('Expect', '')[:4]
    if expect not in ('', '100-', '200-', '204-'):
        abort(417)  # Expectations failed

    image = _fetch_image(image_id)
    if image.status != 'queued':
        abort(405)  # Method not allowed

    image.update(data=request.stream,
                 size=request.content_length)
    return make_json_response(None, status_code=204)


@images.route('/<image_id>/add-tags', methods=('POST',))
def add_image_tags(image_id):
    raise NotImplemented('Image tags are not implemented yet')


@images.route('/<image_id>/remove-tags', methods=('POST',))
def remove_image_tags(image_id):
    raise NotImplemented('Image tags are not implemented yet')

