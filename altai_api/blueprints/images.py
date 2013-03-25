
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

from flask import url_for, g, Blueprint, abort, request
from flask.exceptions import HTTPException

from altai_api import auth
from altai_api.utils import *
from altai_api.utils import collection

from altai_api.utils.decorators import (data_handler, root_endpoint,
                                        user_endpoint)

from altai_api.schema import Schema
from altai_api.schema import types as st

from altai_api.utils.parsers import timestamp_from_openstack
from altai_api import exceptions as exc
from openstackclient_base import exceptions as osc_exc

from altai_api.blueprints.projects import link_for_project


BP = Blueprint('images', __name__)


def _fetch_image(image_id, to_modify):
    try:
        image = auth.admin_client_set().image.images.get(image_id)
    except osc_exc.NotFound:
        abort(404)
    # NOTE(imelnikov): yes, glance may return False as string
    if image.deleted and image.deleted != 'False':
        abort(404)
    if image.owner == auth.default_tenant_id():
        if to_modify:
            auth.assert_admin()
    else:
        auth.assert_admin_or_project_user(image.owner)
    return image


def link_for_image(image_id, image_name=None):
    if image_name is None:
        try:
            image_name = _fetch_image(image_id, to_modify=False).name
        except HTTPException:
            image_name = None
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
        u'size': image.size
    })
    if image.owner == auth.default_tenant_id():
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
        actions = result.setdefault('actions', {})
        actions['upload'] = url_for('images.upload_image_data',
                                    image_id=image.id)
    return result


def list_all_images(client):
    """Get list of all images from all tenants"""
    # NOTE(imelnikov): When is_public is True (the default), images
    # available for current tenant are returned (public images and
    # images from current tenant). When is_public is set to None
    # explicitly, current tenant is ignored.
    return client.list(filters={'is_public': None})


_SCHEMA = Schema((
    st.String('id'),
    st.String('name'),
    st.String('status'),
    st.String('disk-format'),
    st.String('container-format'),
    st.String('md5sum'),
    st.Int('size'),
    st.Timestamp('created'),
    st.Boolean('global'),
    st.LinkObject('project', add_search_matchers={
        'for': st.not_implemented_matcher
    }),
    st.LinkObject('kernel'),
    st.LinkObject('ramdisk')),

    create_required=('name', 'container-format', 'disk-format'),
    create_allowed=('project', 'global', 'kernel', 'ramdisk'),
    updatable=('name')
)


def _images_for_tenant(tenant_id, is_public):
    try:
        tenant = auth.admin_client_set().identity_admin \
                .tenants.get(tenant_id)
    except osc_exc.NotFound:
        return []  # consistent with project:eq

    client = auth.client_set_for_tenant(tenant_id,
                                        fallback_to_api=g.is_admin)
    image_list = client.image.images.list(
            filters={'is_public': is_public})
    return [_image_from_nova(image, tenant) for image in image_list]


def _images_for_all_tenants():
    if g.my_projects:
        tenants = g.client_set.identity_public.tenants.list()
    else:
        tenants = g.client_set.identity_admin.tenants.list()

    tenant_dict = dict(((tenant.id, tenant) for tenant in tenants))
    tenant_dict[auth.default_tenant_id()] = None

    return [_image_from_nova(image, tenant_dict.get(image.owner))
            for image in list_all_images(auth.admin_client_set().image.images)
            if not g.my_projects or image.owner in tenant_dict]


def _project_argument():
    tenant_id = collection.get_matcher_argument('project', 'eq')
    if tenant_id is not None:
        return tenant_id, False
    tenants = collection.get_matcher_argument('project', 'in')
    if tenants and len(tenants) == 1:
        return tenants[0], False
    tenant_id = collection.get_matcher_argument('project', 'for',
                                                delete_if_found=True)
    if tenant_id is not None:
        return tenant_id, None
    return None, None


@BP.route('/', methods=('GET',))
@root_endpoint('images')
@user_endpoint
def list_images():
    parse_collection_request(_SCHEMA)

    tenant_id, is_public = _project_argument()
    if tenant_id is not None:
        result = _images_for_tenant(tenant_id, is_public)
    else:
        result = _images_for_all_tenants()

    return make_collection_response(u'images', result)


@BP.route('/<image_id>', methods=('GET',))
@user_endpoint
def get_image(image_id):
    image = _fetch_image(image_id, to_modify=False)
    return make_json_response(_image_from_nova(image))


@BP.route('/<image_id>', methods=('PUT',))
@user_endpoint
def update_image(image_id):
    data = parse_request_data(_SCHEMA.updatable)
    set_audit_resource_id(image_id)
    fields_to_update = {}
    image = _fetch_image(image_id, to_modify=True)

    if 'name' in data:
        fields_to_update['name'] = data['name']
    if fields_to_update:
        image.update(**fields_to_update)
        image = _fetch_image(image_id, to_modify=False)

    return make_json_response(_image_from_nova(image))


def _assert_param_absent(name, data, which):
    if name in data:
        reason = '%s should not be specified for %s images' % (name, which)
        raise exc.UnknownElement(name, reason)


@BP.route('/', methods=('POST',))
@user_endpoint
def create_image():
    data = parse_request_data(_SCHEMA.create_allowed, _SCHEMA.create_required)

    is_public = data.get('global', 'project' not in data)
    if is_public:
        _assert_param_absent('project', data, 'public')
        auth.assert_admin()
        client_set = g.client_set
    else:
        if 'project' not in data:
            raise exc.MissingElement('project')
        client_set = auth.client_set_for_tenant(data['project'])

    props = {}
    if data['disk-format'] == 'ami':
        # TODO(imelnikov): check that images have correct types
        if 'kernel' in data:
            props['kernel_id'] = data['kernel']
        if 'ramdisk' in data:
            props['ramdisk_id'] = data['ramdisk']
    else:
        _assert_param_absent('kernel', data, data['disk-format'])
        _assert_param_absent('ramdisk', data, data['disk-format'])

    image = client_set.image.images.create(
        name=data['name'],
        disk_format=data['disk-format'],
        container_format=data['container-format'],
        is_public=is_public,
        properties=props)
    set_audit_resource_id(image)
    return make_json_response(_image_from_nova(image))


@BP.route('/<image_id>', methods=('DELETE',))
@user_endpoint
def remove_image(image_id):
    set_audit_resource_id(image_id)
    image = _fetch_image(image_id, to_modify=True)  # also, checks permissions
    image.delete()
    return make_json_response(None, status_code=204)


@BP.route('/<image_id>/data', methods=('PUT',))
@data_handler
@user_endpoint
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

    image = _fetch_image(image_id, to_modify=True)  # also, checks permissions
    if image.status != 'queued':
        abort(405)  # Method not allowed

    image.update(data=request.stream,
                 size=request.content_length)
    return make_json_response(None, status_code=204)

