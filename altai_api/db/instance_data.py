
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

from altai_api.db import DB


class InstanceData(DB.Model):
    """Model for Altai-API specific extra instance data"""
    __tablename__ = 'instance_data'

    instance_id = DB.Column(DB.String(64), primary_key=True)
    expires_at = DB.Column(DB.DateTime)
    remind_at = DB.Column(DB.DateTime)


class InstanceDataDAO(object):

    @staticmethod
    def create(instance_id, expires_at, remind_at):
        DB.session.add(InstanceData(instance_id=instance_id,
                              expires_at=expires_at,
                              remind_at=remind_at))
        DB.session.commit()

    @staticmethod
    def get(instance_id):
        return InstanceData.query.get(instance_id)

    @staticmethod
    def update(instance_id, **kwargs):
        instancedata = InstanceData(instance_id=instance_id)
        if 'expires_at' in kwargs:
            instancedata.expires_at = kwargs['expires_at']
        if 'remind_at' in kwargs:
            instancedata.remind_at = kwargs['remind_at']
        DB.session.merge(instancedata)
        DB.session.commit()

    @staticmethod
    def list_all():
        return InstanceData.query

    @staticmethod
    def expired_list(now):
        return InstanceData.query.filter(InstanceData.expires_at <= now)

    @staticmethod
    def remind_list(now):
        return InstanceData.query.filter(InstanceData.remind_at <= now)

    @staticmethod
    def delete(instance_id):
        """Delete data for machine with id instance_id

        Returns True if any records were deleted, False otherwise.

        """
        num = InstanceData.query\
                .filter(InstanceData.instance_id == instance_id)\
                .delete()
        DB.session.commit()
        return num > 0

