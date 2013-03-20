
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


import mox

from datetime import datetime
from openstackclient_base import exceptions as osc_exc

from tests import doubles
from tests.mocked import MockedTestCase

from altai_api.jobs import instances
from altai_api.db.instance_data import InstanceData


class InstancesJobsTestCase(MockedTestCase):
    FAKE_AUTH = False

    def setUp(self):
        super(InstancesJobsTestCase, self).setUp()
        self.mox.StubOutWithMock(instances, 'InstanceDataDAO')
        self.mox.StubOutWithMock(instances, 'AuditDAO')
        self.mox.StubOutWithMock(instances, 'admin_client_set')
        self.mox.StubOutWithMock(instances, 'datetime')
        self.mox.StubOutWithMock(instances, 'send_instance_reminder')
        self.mox.StubOutWithMock(self.app.logger, 'exception')
        self.fake_client_set = self._fake_client_set_factory()

    def test_instance_data_gc_works(self):
        server_mgr = self.fake_client_set.compute.servers

        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.InstanceDataDAO.list_all()\
                .AndReturn([InstanceData(instance_id='v1'),
                            InstanceData(instance_id='v2')])
        server_mgr.get('v1').AndRaise(osc_exc.NotFound('deleted'))
        instances.InstanceDataDAO.delete('v1')
        server_mgr.get('v2')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.instance_data_gc()

    def test_instance_data_gc_other_exception(self):
        server_mgr = self.fake_client_set.compute.servers

        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.InstanceDataDAO.list_all()\
                .AndReturn([InstanceData(instance_id='v1'),
                            InstanceData(instance_id='v2')])
        server_mgr.get('v1').AndRaise(RuntimeError('log me'))
        self.app.logger.exception(mox.IsA(basestring))
        server_mgr.get('v2')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.instance_data_gc()

    def test_rip_expired_instances(self):
        server_mgr = self.fake_client_set.compute.servers
        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.expired_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v1')])
        server_mgr.delete('v1')
        instances.AuditDAO.create_record({
            'resource': '/v1/instances/v1',
            'method': 'DELETE',
            'response_status': 200,
            'message': 'Automatically deleted expired instance'
        })

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.rip_expired_instances()

    def test_rip_expired_instances_not_found(self):
        server_mgr = self.fake_client_set.compute.servers
        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.expired_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v1'),
                            InstanceData(instance_id='v2')])
        server_mgr.delete('v1').AndRaise(osc_exc.NotFound('deleted'))
        instances.InstanceDataDAO.delete('v1')

        # check we continued to iterate after exception
        server_mgr.delete('v2')
        instances.AuditDAO.create_record(mox.IsA(dict))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.rip_expired_instances()

    def test_rip_expired_instances_other_exception(self):
        server_mgr = self.fake_client_set.compute.servers
        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.expired_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v1'),
                            InstanceData(instance_id='v2')])
        server_mgr.delete('v1').AndRaise(RuntimeError('log me'))
        self.app.logger.exception(mox.IsA(basestring))

        # check we continued to iterate after exception
        server_mgr.delete('v2')
        instances.AuditDAO.create_record(mox.IsA(dict))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.rip_expired_instances()

    def test_remind_reminds(self):
        server_mgr = self.fake_client_set.compute.servers
        instances.admin_client_set().AndReturn(self.fake_client_set)
        user_mgr = self.fake_client_set.identity_admin.users
        server = doubles.make(self.mox, doubles.Server,
                              id='v2', name='instance-2', user_id='UID')
        user = doubles.make(self.mox, doubles.User,
                            id='UID', name='user', email='user@example.com',
                            fullname='The Test User Fullname')
        expires = datetime(2013, 1, 19, 11, 12, 13)

        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.remind_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v2',
                                         expires_at=expires)])

        server_mgr.get('v2').AndReturn(server)
        user_mgr.get('UID').AndReturn(user)
        instances.send_instance_reminder(user.email, 'instance-2', 'v2',
                                         expires, greeting=user.fullname)
        instances.InstanceDataDAO.update('v2', remind_at=None)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.remind_about_instances()

    def test_remind_server_not_found(self):
        server_mgr = self.fake_client_set.compute.servers
        expires = datetime(2013, 1, 19, 11, 12, 13)

        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.remind_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v1',
                                         expires_at=expires)])
        server_mgr.get('v1').AndRaise(osc_exc.NotFound('deleted'))
        instances.InstanceDataDAO.delete('v1')

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.remind_about_instances()

    def test_remind_user_not_found(self):
        server_mgr = self.fake_client_set.compute.servers
        user_mgr = self.fake_client_set.identity_admin.users
        server = doubles.make(self.mox, doubles.Server,
                              id='v2', name='instance-2', user_id='UID')
        expires = datetime(2013, 1, 19, 11, 12, 13)

        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.remind_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v2',
                                         expires_at=expires)])

        server_mgr.get('v2').AndReturn(server)
        user_mgr.get('UID').AndRaise(osc_exc.NotFound('deleted'))
        instances.InstanceDataDAO.update('v2', remind_at=None)

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.remind_about_instances()

    def test_remind_other_exception(self):
        server_mgr = self.fake_client_set.compute.servers
        expires = datetime(2013, 1, 19, 11, 12, 13)

        instances.admin_client_set().AndReturn(self.fake_client_set)
        instances.datetime.utcnow().AndReturn('UTCNOW')
        instances.InstanceDataDAO.remind_list('UTCNOW')\
                .AndReturn([InstanceData(instance_id='v1',
                                         expires_at=expires)])
        server_mgr.get('v1').AndRaise(RuntimeError('log me'))
        self.app.logger.exception(mox.IsA(basestring))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            instances.remind_about_instances()


class TestFactoryTestCase(MockedTestCase):

    def test_factory_works(self):
        self.mox.StubOutWithMock(instances, 'PeriodicAdministrativeJob')

        instances.PeriodicAdministrativeJob(self.app, 10.0,
                                            instances.rip_expired_instances)\
                .AndReturn('T1')
        instances.PeriodicAdministrativeJob(self.app, 60.0,
                                            instances.remind_about_instances)\
                .AndReturn('T2')
        instances.PeriodicAdministrativeJob(self.app, 2400.0,
                                            instances.instance_data_gc)\
                .AndReturn('T3')

        self.mox.ReplayAll()
        result = instances.jobs_factory(self.app)
        self.assertEquals(result, ['T1', 'T2', 'T3'])

