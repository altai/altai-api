
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

from openstackclient_base.nova.networks import Network

from keystoneclient.v2_0.roles import Role
from keystoneclient.v2_0.tenants import Tenant
from keystoneclient.v2_0.users import User

from novaclient.v1_1.flavors import Flavor
from novaclient.v1_1.hosts import Host
from novaclient.v1_1.keypairs import Keypair
from novaclient.v1_1.quotas import QuotaSet
from novaclient.v1_1.security_group_rules import SecurityGroupRule
from novaclient.v1_1.security_groups import SecurityGroup
from novaclient.v1_1.servers import Server

from glanceclient.v1.images import Image

from tests.mocked import mock_with_attributes


# INFO remembers data from several real-life objects

INFO = {
    Network: {
        u'bridge': u'br22',
        u'bridge_interface': u'eth0',
        u'broadcast': u'10.5.2.255',
        u'cidr': u'10.5.2.0/24',
        u'cidr_v6': None,
        u'created_at': u'2012-11-26 12:26:03',
        u'deleted': False,
        u'deleted_at': None,
        u'dhcp_start': u'10.5.2.3',
        u'dns1': None,
        u'dns2': None,
        u'gateway': u'10.5.2.1',
        u'gateway_v6': None,
        u'host': None,
        u'injected': False,
        u'multi_host': False,
        u'netmask': u'255.255.255.0',
        u'netmask_v6': None,
        u'priority': None,
        u'project_id': u'c4fc65e395e8408b97f6c1a27da95c43',
        u'rxtx_base': None,
        u'updated_at': u'2012-11-26 12:26:10',
        u'vlan': 22,
        u'vpn_private_address': u'10.5.2.2',
        u'vpn_public_address': None,
        u'vpn_public_port': 1000,
    },
    Tenant: {
        u'id': u'c4fc65e395e8408b97f6c1a27da95c43',
        u'name': 'Default test tenant',
        u'enabled': True,
        u'description': u'Rather long description.'
    },
    QuotaSet: dict(cores=33, floating_ips=10, gigabytes=1000,
                   injected_file_content_bytes=10240, injected_files=5,
                   instances=10, metadata_items=128, ram=51200,
                   security_group_rules=20, security_groups=10, volumes=10),
    Image: {
        u'checksum': u'fde755f8655a70dd2623067a4a74b689',
        u'container_format': u'bare',
        u'created_at': u'2012-12-03T08:59:02',
        u'deleted_at': None,
        u'deleted': False,
        u'disk_format': u'raw',
        u'id': u'9c943146-dfa1-4585-93ac-086739ac271c',
        u'is_public': True,
        u'min_disk': 0,
        u'min_ram': 0,
        u'name': u'test image',
        u'owner': u'6cd68209bf4846c9ad82538b602af120',
        u'properties': {
            u'image_location': u'local',
            u'image_state': u'available',
            u'project_id': u'6cd68209bf4846c9ad82538b602af120',
            u'architecture': u'x86_64'
        },
        u'protected': False,
        u'size': 20971520,
        u'status': u'active',
        u'updated_at': u'2012-12-03T08:59:03'
    },
    Server: {
        #u'OS-DCF:diskConfig': u'MANUAL',
        #u'OS-EXT-SRV-ATTR:host': u'test',
        #u'OS-EXT-SRV-ATTR:hypervisor_hostname': None,
        #u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000002',
        #u'OS-EXT-STS:power_state': 1,
        #u'OS-EXT-STS:task_state': None,
        #u'OS-EXT-STS:vm_state': u'active',
        u'accessIPv4': u'',
        u'accessIPv6': u'',
        u'addresses': {
            u'net4': [
                {
                    u'version': 4,
                    u'addr': u'10.5.4.3'
                }]},
        u'config_drive': u'',
        u'created': u'2012-12-03T08:59:42Z',
        u'flavor': {
            u'id': u'1',
            u'links': [
                {
                    u'href': u'http://localhost:8774/'
                            '6cd68209bf4846c9ad82538b602af120/flavors/1',
                    u'rel': u'bookmark'
                }]},
        u'hostId': u'3a360c741b76e0e337c80f88c1bdec28e25821b4810b29f76dad2af2',
        u'id': u'586b3c69-ba81-493e-b8cc-1f5abde3d486',
        u'image': {
            u'id': u'9c943146-dfa1-4585-93ac-086739ac271c',
            u'links': [
                {
                    u'href': u'http://localhost:8774/'
                            '6cd68209bf4846c9ad82538b602af120/images/'
                            '9c943146-dfa1-4585-93ac-086739ac271c',
                    u'rel': u'bookmark'
                }]},
        u'key_name': u'',
        u'links': [
            {
                u'href': u'http://localhost:8774/v2/'
                            '6cd68209bf4846c9ad82538b602af120/servers/'
                            '586b3c69-ba81-493e-b8cc-1f5abde3d486',
                u'rel': u'self'
            },
            {
                u'href': u'http://localhost:8774/'
                            '6cd68209bf4846c9ad82538b602af120/servers/'
                            '586b3c69-ba81-493e-b8cc-1f5abde3d486',
                u'rel': u'bookmark'
            }
        ],
        u'metadata': {},
        u'name': u'test2',
        u'networks': {
            u'net4': [ u'10.5.4.3' ]
        },
        u'progress': 0,
        u'status': u'ACTIVE',
        u'tenant_id': u'9beaae574e49496da7dd2c65d116db3c',
        u'updated': u'2012-12-03T09:01:51Z',
        u'user_id': u'adbf4849f0554bddbfa9e08923f1f79b',
    },
    Flavor: {
        u'disk': 4,
        u'ephemeral': 8,
        u'id': u'1',
        u'links': [
            {
                u'href': u'http://localhost:8774/v2/'
                            '6cd68209bf4846c9ad82538b602af120/flavors/1',
                u'rel': u'self'
            },
            {
                u'href': u'http://localhost:8774/'
                            '6cd68209bf4846c9ad82538b602af120/flavors/1',
                u'rel': u'bookmark'
            }
        ],
        u'name': u'test flavor',
        u'ram': 512,
        u'rxtx_factor': 1.0,
        u'swap': u'',
        u'vcpus': 1
    },
    SecurityGroup: {
        u'rules': [],
        u'tenant_id': u'6cd68209bf4846c9ad82538b602af120',
        u'description': u'test sg description',
        u'id': 3,
        u'name': u'test sg'
    },
    SecurityGroupRule: {
        u'from_port': 90,
        u'group': {},
        u'ip_protocol': u'tcp',
        u'to_port': 92,
        u'parent_group_id': 5,
        u'ip_range': { u'cidr': u'10.20.30.0/24' },
        u'id': 3
    },
    User: {
        u'id': u'42',
        u'tenantId': u'6cd68209bf4846c9ad82538b602af120',
        u'enabled': False,
        u'name': u'user',
        u'email': u'user@example.com'
    },
    Role: {
        u'role': {
            u'id': u'7cbae24a4c1b46849ae51784387f4257',
            u'name': u'admin'
        },
        u'tenant': {
            u'id': u'6cd68209bf4846c9ad82538b602af120',
            u'name': u'TENANT'
        }
    },
    Server: {
        #u'OS-EXT-STS:vm_state': u'building',
        #u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000001',
        #u'OS-EXT-STS:task_state': u'spawning',
        #u'OS-DCF:diskConfig': u'MANUAL',
        #u'OS-EXT-STS:power_state': 0,
        #u'OS-EXT-SRV-ATTR:host': u'test',
        #u'OS-EXT-SRV-ATTR:hypervisor_hostname': None,
        u'id': u'7ce6269b-76fb-488f-ab23-bd72e2289161',
        u'name': u't1',
        u'user_id': u'adbf4849f0554bddbfa9e08923f1f79b',
        u'tenant_id': u'3148e35190904805b26ee128fb856b69',
        u'addresses': {
            u'net42': [
                {
                    u'version': 4,
                    u'addr': u'10.5.1.3'
                }
            ]
        },
        u'accessIPv4': u'',
        u'accessIPv6': u'',
        u'links': [
            {
                u'rel': u'self',
                u'href': u'http://172.18.66.112:8774/v2/'
                        '6cd68209bf4846c9ad82538b602af120/servers/'
                        '7ce6269b-76fb-488f-ab23-bd72e2289161'
            },
            {
                u'href': u'http://172.18.66.112:8774/'
                        '6cd68209bf4846c9ad82538b602af120/servers/'
                        '7ce6269b-76fb-488f-ab23-bd72e2289161',
                u'rel': u'bookmark'
            }
        ],
        u'image': {
            u'id': u'27307cfa-7c2b-4b3d-ab8e-f0d462426faa',
            u'links': [
                {
                    u'href': u'http://172.18.66.112:8774/'
                            '6cd68209bf4846c9ad82538b602af120/images/'
                            '27307cfa-7c2b-4b3d-ab8e-f0d462426faa',
                    u'rel': u'bookmark'
                }
            ]
        },
        u'flavor': {
            u'id': u'1',
            u'links': [
                {
                    u'href': u'http://172.18.66.112:8774/'
                            '6cd68209bf4846c9ad82538b602af120/flavors/1',
                    u'rel': u'bookmark'
                }
            ]
        },
        u'progress': 0,
        u'config_drive': u'',
        u'status': u'BUILD',
        u'updated': u'2012-12-12T06:20:37Z',
        u'hostId': u'6186525952c6568e1f6f5ae666c64baac9a595c5c3da17e869faa3ea',
        u'key_name': u'',
        u'created': u'2012-12-12T06:20:27Z',
        u'metadata': {}
    },
    Keypair: {
        u'public_key': u'ssh-rsa BLABLABLA nova@test\n',
        u'name': u'kptest',
        u'fingerprint': u'00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF'
    },
    Host: {
        u'project': u'TEST_PID',
        u'memory_mb': 512,
        u'host': u'test',
        u'cpu': 4,
        u'disk_gb': 10
    }
}


def make(mox, object_type, **add_attrs):
    attrs = INFO.get(object_type, {}).copy()
    attrs.update(add_attrs)
    return mock_with_attributes(mox, object_type, **attrs)

