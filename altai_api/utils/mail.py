
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

from flask import current_app, render_template
from flask.ext import mail

from altai_api import exceptions as exc

MAIL = mail.Mail()


def _render_link_template(template, code):
    link = template.replace('{{code}}', code)
    if '{{' in link or '{%' in link:
        # any other template construction are not allowed
        raise exc.IllegalValue('link-template', 'string', template)
    return link


def send_invitation(email, code, link_template=None, greeting=None):

    # TODO(imelnikov): read some of parameters from database
    installation_name = current_app.config['DEFAULT_INSTALLATION_NAME']
    args = {
        'greeting': greeting,
        'invitation_code': code,
        'installation_name': installation_name,
        'footer': current_app.config.get('DEFAULT_MAIL_FOOTER')
    }

    if link_template:
        args['invitation_link'] = _render_link_template(link_template, code)

    msg = mail.Message('Invitation to %s' % installation_name,
                       recipients=[email])
    msg.body = render_template('invite_mail', **args)
    try:
        MAIL.send(msg)
    except IOError, e:
        e.message = 'Failed to send e-mail'
        raise

