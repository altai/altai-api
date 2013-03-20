
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

from flask import url_for, current_app
from datetime import datetime
from openstackclient_base import exceptions as osc_exc

from altai_api.auth import admin_client_set
from altai_api.db.instance_data import InstanceDataDAO
from altai_api.db.audit import AuditDAO
from altai_api.utils.mail import send_instance_reminder
from altai_api.utils.periodic_job import PeriodicAdministrativeJob


def rip_expired_instances():
    """Run periodically to remove expired instances"""
    server_mgr = admin_client_set().compute.servers
    for instance_data in InstanceDataDAO.expired_list(datetime.utcnow()):
        try:
            server_mgr.delete(instance_data.instance_id)
            AuditDAO.create_record(dict(
                resource=url_for('instances.delete_instance',
                                 instance_id=instance_data.instance_id),
                method='DELETE',
                response_status=200,
                message='Automatically deleted expired instance',
            ))
        except osc_exc.NotFound:
            InstanceDataDAO.delete(instance_data.instance_id)
        except Exception:
            current_app.logger.exception('Failed to delete expired instance %r'
                                         % instance_data.instance_id)


def remind_about_instances():
    """Run periodically to send reminding emails"""
    cs = admin_client_set()
    server_mgr = cs.compute.servers
    user_mgr = cs.identity_admin.users
    for instance_data in InstanceDataDAO.remind_list(datetime.utcnow()):
        try:
            try:
                server = server_mgr.get(instance_data.instance_id)
            except osc_exc.NotFound:
                InstanceDataDAO.delete(instance_data.instance_id)
                continue

            try:
                user = user_mgr.get(server.user_id)
            except osc_exc.NotFound:
                pass
            else:
                send_instance_reminder(user.email, server.name,
                                 server.id, instance_data.expires_at,
                                 greeting=getattr(user, 'fullname', ''))
            InstanceDataDAO.update(instance_data.instance_id, remind_at=None)
        except Exception:
            current_app.logger.exception(
                'Failed to send reminder email about instance %r'
                % instance_data.instance_id)


def instance_data_gc():
    """Remove instance data for already deleted servers"""
    server_mgr = admin_client_set().compute.servers
    for instance_data in InstanceDataDAO.list_all():
        try:
            server_mgr.get(instance_data.instance_id)
        except osc_exc.NotFound:
            InstanceDataDAO.delete(instance_data.instance_id)
        except Exception:
            current_app.logger.exception('Failed to delete data '
                                         'for non-existing instance %r'
                                         % instance_data.instance_id)


def jobs_factory(app):
    result = []
    for job, interval_param in (
            (rip_expired_instances, 'RIP_EXPIRED_INSTANCES_TASK_INTERVAL'),
            (remind_about_instances, 'INSTANCES_REMINDER_TASK_INTERVAL'),
            (instance_data_gc, 'INSTANCE_DATA_GC_TASK_INTERVAL')):
        result.append(PeriodicAdministrativeJob(
            app, app.config[interval_param], job))
    return result

