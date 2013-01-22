
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
from altai_api.db.helpers import Json


class ConfigVar(DB.Model):
    __tablename__ = 'configuration'

    group = DB.Column(DB.String(1024), primary_key=True)
    name = DB.Column(DB.String(1024), primary_key=True)
    value = DB.Column(Json, nullable=False, default=None)


class ConfigDAO(object):

    @staticmethod
    def set_to(group, name, value):
        DB.session.merge(ConfigVar(group=group, name=name, value=value))
        DB.session.commit()

    @staticmethod
    def get(group, name):
        var = ConfigVar.query.get((group, name))
        if var is None:
            return None
        return var.value

    @staticmethod
    def list_all():
        return ((var.group, var.name, var.value)
                for var in ConfigVar.query)

    @staticmethod
    def list_group(group):
        return ((var.group, var.name, var.value)
                for var in ConfigVar.query \
                    .filter(ConfigVar.group == group))

