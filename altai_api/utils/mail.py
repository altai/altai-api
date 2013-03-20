
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

from flask import g, current_app, render_template, request
from flask.ext import mail
from altai_api import exceptions as exc


def _render_link_template(template, code):
    link = template.replace('{{code}}', code)
    if '{{' in link or '{%' in link:
        # any other template construction are not allowed
        raise exc.IllegalValue('link-template', 'string', template)
    return link


def _send_mail(email, link_template, subject, template, args):
    args = args.copy()
    args['installation_name'] = g.config('general', 'installation-name')
    args['footer'] = g.config('mail', 'footer')
    if link_template:
        args['link'] = _render_link_template(link_template, args['code'])
    if not args['greeting']:
        # empty string and None should mean 'no greeting'
        del args['greeting']

    msg = mail.Message(subject % args, recipients=[email],
                       sender=(g.config('mail', 'sender-name'),
                               g.config('mail', 'sender-mail')),
                       body=render_template(template, **args))
    try:
        mail.Mail(current_app).send(msg)
    except IOError, e:
        e.message = 'Failed to send e-mail'
        raise


def send_invitation(email, code, link_template=None, greeting=None):
    args = {'greeting': greeting, 'code': code}
    return _send_mail(email, link_template,
                      'Invitation to %(installation_name)s',
                      'invite_mail', args)


def send_reset_password(email, code, login,
                        link_template=None, greeting=None):
    args = {
        'greeting': greeting,
        'code': code,
        'login': login,
        'remote_addr': request.remote_addr
    }
    return _send_mail(email, link_template,
                      'Password reset for %(installation_name)s',
                      'password_reset_mail', args)


def send_instance_reminder(email, name, instance_id,
                           expires_at=None, greeting=None):
    args = {
        'greeting': greeting,
        'name': name,
        'id': instance_id
    }
    if expires_at is not None:
        args['expires'] = expires_at.strftime('%F %T UTC')
    return _send_mail(email, None,
                      'Reminder about instance %s' % name,
                      'instance_reminder_mail', args)

