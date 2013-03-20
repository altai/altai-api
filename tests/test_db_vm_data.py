
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

from datetime import datetime, timedelta

from tests.db import ContextWrappedDBTestCase
from altai_api.db.instance_data import InstanceDataDAO


class InstanceDataDAOTestCase(ContextWrappedDBTestCase):

    def setUp(self):
        super(InstanceDataDAOTestCase, self).setUp()
        self.instance_id = 'VMID'
        self.expires_at = datetime(2012, 10, 11, 12, 13, 14)
        self.remind_at = datetime(2012, 10, 11, 9, 8, 7)
        InstanceDataDAO.create(self.instance_id,
                               self.expires_at, self.remind_at)

    def test_get(self):
        instancedata = InstanceDataDAO.get(self.instance_id)
        self.assertEquals(self.instance_id, instancedata.instance_id)
        self.assertEquals(self.expires_at, instancedata.expires_at)
        self.assertEquals(self.remind_at, instancedata.remind_at)

    def test_get_none(self):
        instancedata = InstanceDataDAO.get('non-existing id')
        self.assertEquals(instancedata, None)

    def test_update_expires_at(self):
        new_expires_at = self.expires_at + timedelta(days=30)
        InstanceDataDAO.update(self.instance_id, expires_at=new_expires_at)
        self.assertEquals(new_expires_at,
                          InstanceDataDAO.get(self.instance_id).expires_at)

    def test_update_expires_not_found(self):
        instance_id = 'OTHER_TEST_VMID'
        InstanceDataDAO.update(instance_id, expires_at=self.expires_at)
        self.assertEquals(self.expires_at,
                          InstanceDataDAO.get(instance_id).expires_at)

    def test_update_expires_at_to_none(self):
        InstanceDataDAO.update(self.instance_id, expires_at=None)
        self.assertEquals(None,
                          InstanceDataDAO.get(self.instance_id).expires_at)

    def test_update_remind_at(self):
        new_remind_at = self.remind_at + timedelta(days=30)
        InstanceDataDAO.update(self.instance_id, remind_at=new_remind_at)
        self.assertEquals(new_remind_at,
                          InstanceDataDAO.get(self.instance_id).remind_at)

    def test_update_remind_at_to_none(self):
        InstanceDataDAO.update(self.instance_id, remind_at=None)
        self.assertEquals(None,
                          InstanceDataDAO.get(self.instance_id).remind_at)

    def test_list_all(self):
        l = list(InstanceDataDAO.list_all())
        self.assertEquals(l, [InstanceDataDAO.get(self.instance_id)])

    def test_expired_list(self):
        l = list(InstanceDataDAO.expired_list(self.expires_at))
        self.assertEquals(l, [InstanceDataDAO.get(self.instance_id)])

    def test_expired_list_empty(self):
        one_day_before = self.expires_at - timedelta(days=1)
        l = list(InstanceDataDAO.expired_list(one_day_before))
        self.assertEquals(l, [])

    def test_remind_list(self):
        l = list(InstanceDataDAO.remind_list(self.remind_at))
        self.assertEquals(l, [InstanceDataDAO.get(self.instance_id)])

    def test_remind_list_empty(self):
        one_day_before = self.remind_at - timedelta(days=1)
        l = list(InstanceDataDAO.remind_list(one_day_before))
        self.assertEquals(l, [])

    def test_delete_deletes(self):
        self.assertTrue(InstanceDataDAO.delete(self.instance_id))
        self.assertEquals(None, InstanceDataDAO.get(self.instance_id))

