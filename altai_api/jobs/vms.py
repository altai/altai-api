
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

from flask import url_for, current_app
from datetime import datetime
from openstackclient_base import exceptions as osc_exc

from altai_api.auth import admin_client_set
from altai_api.db.vm_data import VmDataDAO
from altai_api.db.audit import AuditDAO
from altai_api.utils.mail import send_vm_reminder
from altai_api.utils.periodic_job import PeriodicAdministrativeJob


def rip_expired_vms():
    """Run periodically to remove expired vms"""
    server_mgr = admin_client_set().compute.servers
    for vmdata in VmDataDAO.expired_list(datetime.utcnow()):
        try:
            server_mgr.delete(vmdata.vm_id)
            AuditDAO.create_record(dict(
                resource=url_for('vms.delete_vm', vm_id=vmdata.vm_id),
                method='DELETE',
                response_status=200,
                message='Automatically deleted expired VM',
            ))
        except osc_exc.NotFound:
            VmDataDAO.delete(vmdata.vm_id)
        except Exception:
            current_app.logger.exception('Failed to delete expired vm %r'
                                         % vmdata.vm_id)


def remind_about_vms():
    """Run periodically to send reminding emails"""
    cs = admin_client_set()
    server_mgr = cs.compute.servers
    user_mgr = cs.identity_admin.users
    for vmdata in VmDataDAO.remind_list(datetime.utcnow()):
        try:
            try:
                server = server_mgr.get(vmdata.vm_id)
            except osc_exc.NotFound:
                VmDataDAO.delete(vmdata.vm_id)
                continue

            try:
                user = user_mgr.get(server.user_id)
            except osc_exc.NotFound:
                pass
            else:
                send_vm_reminder(user.email, server.name,
                                 server.id, vmdata.expires_at,
                                 greeting=getattr(user, 'fullname', ''))
            VmDataDAO.update(vmdata.vm_id, remind_at=None)
        except Exception:
            current_app.logger.exception('Failed to send reminder email '
                                         'about vm %r' % vmdata.vm_id)


def vm_data_gc():
    """Remove vm data for already deleted servers"""
    server_mgr = admin_client_set().compute.servers
    for vmdata in VmDataDAO.list_all():
        try:
            server_mgr.get(vmdata.vm_id)
        except osc_exc.NotFound:
            VmDataDAO.delete(vmdata.vm_id)
        except Exception:
            current_app.logger.exception('Failed to delete data '
                                         'for non-existing vm %r'
                                         % vmdata.vm_id)


def jobs_factory(app):
    result = []
    for job, interval_param in (
            (rip_expired_vms, 'RIP_EXPIRED_VMS_TASK_INTERVAL'),
            (remind_about_vms, 'VMS_REMINDER_TASK_INTERVAL'),
            (vm_data_gc, 'VM_DATA_GC_TASK_INTERVAL')):
        result.append(PeriodicAdministrativeJob(
            app, app.config[interval_param], job))
    return result

