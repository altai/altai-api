
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
from altai_api.db.vm_data import VmDataDAO


class VmDataDAOTestCase(ContextWrappedDBTestCase):

    def setUp(self):
        super(VmDataDAOTestCase, self).setUp()
        self.vm_id = 'VMID'
        self.expires_at = datetime(2012, 10, 11, 12, 13, 14)
        self.remind_at = datetime(2012, 10, 11, 9, 8, 7)
        VmDataDAO.create(self.vm_id, self.expires_at, self.remind_at)

    def test_get(self):
        vmdata = VmDataDAO.get(self.vm_id)
        self.assertEquals(self.vm_id, vmdata.vm_id)
        self.assertEquals(self.expires_at, vmdata.expires_at)
        self.assertEquals(self.remind_at, vmdata.remind_at)

    def test_get_none(self):
        vmdata = VmDataDAO.get('non-existing id')
        self.assertEquals(vmdata, None)

    def test_update_expires_at(self):
        new_expires_at = self.expires_at + timedelta(days=30)
        VmDataDAO.update(self.vm_id, expires_at=new_expires_at)
        self.assertEquals(new_expires_at,
                          VmDataDAO.get(self.vm_id).expires_at)

    def test_update_expires_not_found(self):
        vm_id = 'OTHER_TEST_VMID'
        VmDataDAO.update(vm_id, expires_at=self.expires_at)
        self.assertEquals(self.expires_at,
                          VmDataDAO.get(vm_id).expires_at)

    def test_update_expires_at_to_none(self):
        VmDataDAO.update(self.vm_id, expires_at=None)
        self.assertEquals(None,
                          VmDataDAO.get(self.vm_id).expires_at)

    def test_update_remind_at(self):
        new_remind_at = self.remind_at + timedelta(days=30)
        VmDataDAO.update(self.vm_id, remind_at=new_remind_at)
        self.assertEquals(new_remind_at,
                          VmDataDAO.get(self.vm_id).remind_at)

    def test_update_remind_at_to_none(self):
        VmDataDAO.update(self.vm_id, remind_at=None)
        self.assertEquals(None,
                          VmDataDAO.get(self.vm_id).remind_at)

    def test_list_all(self):
        l = list(VmDataDAO.list_all())
        self.assertEquals(l, [VmDataDAO.get(self.vm_id)])

    def test_expired_list(self):
        l = list(VmDataDAO.expired_list(self.expires_at))
        self.assertEquals(l, [VmDataDAO.get(self.vm_id)])

    def test_expired_list_empty(self):
        one_day_before = self.expires_at - timedelta(days=1)
        l = list(VmDataDAO.expired_list(one_day_before))
        self.assertEquals(l, [])

    def test_remind_list(self):
        l = list(VmDataDAO.remind_list(self.remind_at))
        self.assertEquals(l, [VmDataDAO.get(self.vm_id)])

    def test_remind_list_empty(self):
        one_day_before = self.remind_at - timedelta(days=1)
        l = list(VmDataDAO.remind_list(one_day_before))
        self.assertEquals(l, [])

    def test_delete_deletes(self):
        self.assertTrue(VmDataDAO.delete(self.vm_id))
        self.assertEquals(None, VmDataDAO.get(self.vm_id))

