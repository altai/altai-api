
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

from altai_api.db import DB


class VmData(DB.Model):
    """Model for Altai-API specific extra VM data"""
    __tablename__ = 'vm_data'

    vm_id = DB.Column(DB.String(64), primary_key=True)
    expires_at = DB.Column(DB.DateTime)
    remind_at = DB.Column(DB.DateTime)


class VmDataDAO(object):

    @staticmethod
    def create(vm_id, expires_at, remind_at):
        DB.session.add(VmData(vm_id=vm_id,
                              expires_at=expires_at,
                              remind_at=remind_at))
        DB.session.commit()

    @staticmethod
    def get(vm_id):
        return VmData.query.get(vm_id)

    @staticmethod
    def update(vm_id, **kwargs):
        vmdata = VmData(vm_id=vm_id)
        if 'expires_at' in kwargs:
            vmdata.expires_at = kwargs['expires_at']
        if 'remind_at' in kwargs:
            vmdata.remind_at = kwargs['remind_at']
        DB.session.merge(vmdata)
        DB.session.commit()

    @staticmethod
    def list_all():
        return VmData.query

    @staticmethod
    def expired_list(now):
        return VmData.query.filter(VmData.expires_at <= now)

    @staticmethod
    def remind_list(now):
        return VmData.query.filter(VmData.remind_at <= now)

    @staticmethod
    def delete(vm_id):
        """Delete data for machine with id vm_id

        Returns True if any records were deleted, False otherwise.

        """
        num = VmData.query.filter(VmData.vm_id == vm_id).delete()
        DB.session.commit()
        return num > 0


