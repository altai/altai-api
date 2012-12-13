
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

"""Mocked stuff like client set and helpers"""


import datetime

from tests import TestCase
from mox import MoxTestBase

from openstackclient_base.client import HttpClient

from openstackclient_base.keystone.client import IdentityAdminClient
from openstackclient_base.keystone.client import IdentityPublicClient
from openstackclient_base.nova.client import ComputeClient
from openstackclient_base.nova.client import VolumeClient
from openstackclient_base.glance.v1.client import ImageClient

from keystoneclient.v2_0 import endpoints
from keystoneclient.v2_0 import roles
from keystoneclient.v2_0 import services
from keystoneclient.v2_0 import tenants
from keystoneclient.v2_0 import tokens
from keystoneclient.v2_0 import users

from novaclient.v1_1 import certs
from novaclient.v1_1 import cloudpipe
from novaclient.v1_1 import aggregates
from novaclient.v1_1 import flavors
from novaclient.v1_1 import floating_ip_dns
from novaclient.v1_1 import floating_ips
from novaclient.v1_1 import floating_ip_pools
from novaclient.v1_1 import hosts
from novaclient.v1_1 import images
from novaclient.v1_1 import keypairs
from novaclient.v1_1 import limits
from novaclient.v1_1 import quota_classes
from novaclient.v1_1 import quotas
from novaclient.v1_1 import security_group_rules
from novaclient.v1_1 import security_groups
from novaclient.v1_1 import servers
from novaclient.v1_1 import usage
from novaclient.v1_1 import virtual_interfaces
from novaclient.v1_1 import volumes
from novaclient.v1_1 import volume_snapshots
from novaclient.v1_1 import volume_types

from openstackclient_base.nova import networks
from openstackclient_base.nova import fping

from glanceclient.v1 import images
from glanceclient.v1 import image_members


def _tomorrow():
    return (datetime.datetime.now()
            + datetime.timedelta(days=1)).isoformat()


def mock_with_attributes(mox, object_type, **kwargs):
    """Create mock from object_type and set some attributes"""

    m = mox.CreateMock(object_type)
    for k, v in kwargs.iteritems():
        setattr(m, k, v)
    return m


def mock_client_set(mox, aliases=False):
    """Create mocked ClientSet with mocked clients and managers"""

    access = {
        u'token': {
            u'expires': _tomorrow(),
            u'id': u'ACCESS_TOKEN_ID',
            u'tenant': {
                u'description': None,
                u'enabled': True,
                u'id': u'SYSTENANT_ID',
                u'name': u'systenant'
            }
        },
        u'serviceCatalog': [], # it's contents is irrelevant
        u'user': {
            u'username': u'admin',
            u'roles_links': [],
            u'id': u'ADMIN_USER_ID',
            u'roles': [
                {
                    u'id': u'ADMIN_ROLE_ID',
                    u'name': u'admin'
                }
            ],
            u'name': u'admin'
        }
    }

    cs = mox.CreateMockAnything()

    cs.http_client = mock_with_attributes(
        mox, HttpClient,
        USER_AGENT='python-openstackclient-base',
        auth_uri='172.18.66.112:5000/v2.0',
        callback=None,
        connect_kwargs={},
        endpoint=None,
        password='topsecret',
        region_name=None,
        tenant_id=None,
        tenant_name='systenant',
        token=None,
        use_ssl=False,
        username='admin',
        access=access)

    cs.identity_admin = mock_with_attributes(
        mox, IdentityAdminClient,
        endpoints = mox.CreateMock(endpoints.EndpointManager),
        roles = mox.CreateMock(roles.RoleManager),
        services = mox.CreateMock(services.ServiceManager),
        tenants = mox.CreateMock(tenants.TenantManager),
        tokens = mox.CreateMock(tokens.TokenManager),
        users = mox.CreateMock(users.UserManager))

    cs.identity_public = mock_with_attributes(
        mox, IdentityPublicClient,
        tenants = mox.CreateMock(tenants.TenantManager))

    cs.compute = mock_with_attributes(
        mox, ComputeClient,
        flavors = mox.CreateMock(flavors.FlavorManager),
        images = mox.CreateMock(images.ImageManager),
        limits = mox.CreateMock(limits.LimitsManager),
        servers = mox.CreateMock(servers.ServerManager),

        dns_domains = mox.CreateMock(floating_ip_dns.FloatingIPDNSDomainManager),
        dns_entries = mox.CreateMock(floating_ip_dns.FloatingIPDNSEntryManager),
        cloudpipe = mox.CreateMock(cloudpipe.CloudpipeManager),
        certs = mox.CreateMock(certs.CertificateManager),
        floating_ips = mox.CreateMock(floating_ips.FloatingIPManager),
        floating_ip_pools = mox.CreateMock(floating_ip_pools.FloatingIPPoolManager),
        keypairs = mox.CreateMock(keypairs.KeypairManager),
        quota_classes = mox.CreateMock(quota_classes.QuotaClassSetManager),
        quotas = mox.CreateMock(quotas.QuotaSetManager),
        security_groups = mox.CreateMock(security_groups.SecurityGroupManager),
        security_group_rules = mox.CreateMock(security_group_rules.SecurityGroupRuleManager),
        usage = mox.CreateMock(usage.UsageManager),
        virtual_interfaces = mox.CreateMock(virtual_interfaces.VirtualInterfaceManager),
        aggregates = mox.CreateMock(aggregates.AggregateManager),
        hosts = mox.CreateMock(hosts.HostManager),

        networks = mox.CreateMock(networks.NetworkManager),
        fping = mox.CreateMock(fping.FpingManager))

    cs.volume = mock_with_attributes(
        mox, VolumeClient,
        volumes = mox.CreateMock(volumes.VolumeManager),
        volume_snapshots = mox.CreateMock(volume_snapshots.SnapshotManager),
        volume_types = mox.CreateMock(volume_types.VolumeTypeManager))

    cs.image = mock_with_attributes(
        mox, ImageClient,
        images = mox.CreateMock(images.ImageManager),
        image_members = mox.CreateMock(image_members.ImageMemberManager))

    if aliases:
        # we discourage their use, so we don't add them by default
        cs.keystone = cs.identity_admin
        cs.nova = cs.compute
        cs.glance = cs.image

    return cs


class MockedTestCase(TestCase, MoxTestBase):
    def setUp(self):
        super(MockedTestCase, self).setUp()
        self.fake_client_set = mock_client_set(self.mox)

