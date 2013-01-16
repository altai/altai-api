
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

import sqlalchemy.types

from flask import json
from datetime import datetime

from altai_api.db import DB


class Json(sqlalchemy.types.TypeDecorator):
    impl = DB.Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


class AuditRecord(DB.Model):
    __tablename__ = 'audit_records'

    record_id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)

    resource = DB.Column(DB.String(1024), nullable=False)
    method = DB.Column(DB.String(16), nullable=False)
    response_status = DB.Column(DB.Integer, nullable=False)
    message = DB.Column(DB.String(16))

    user_id = DB.Column(DB.String(64))
    project_id = DB.Column(DB.String(64))
    remote_address = DB.Column(DB.String(255), nullable=False)

    timestamp = DB.Column(DB.DateTime, nullable=False,
                          default=datetime.utcnow)
    extra = DB.Column(Json(), nullable=False, default={})


class AuditDAO(object):

    @staticmethod
    def create_record(audit_data):
        record = AuditRecord(**audit_data)
        DB.session.add(record)
        DB.session.commit()
        return record

    @staticmethod
    def list_all():
        return AuditRecord.query

    @staticmethod
    def get(record_id):
        return AuditRecord.query.get_or_404(record_id)


