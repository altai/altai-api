
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

import mox

from datetime import datetime
from tests.mocked import MockedTestCase
from altai_api import exceptions as exc

from altai_api.utils import mail


class MailTestCase(MockedTestCase):
    def setUp(self):
        super(MailTestCase, self).setUp()
        self.mox.StubOutClassWithMocks(mail.mail, 'Mail')

    def test_send_invitation_works(self):
        class IsCorrectMail(mox.Comparator):
            def equals(inner_self, message):
                self.assertTrue(message.subject.startswith('Invitation'))
                self.assertTrue('Dear User Userovich' in message.body)
                self.assertTrue('https://localhost/invites?code=THE_CODE'
                                in message.body)
                return True

        mail.mail.Mail(mail.current_app).send(IsCorrectMail())

        self.mox.ReplayAll()
        with self.app.test_request_context():
            mail.send_invitation('uuserovich@example.com',
                                 'THE_CODE',
                                 'https://localhost/invites?code={{code}}',
                                 'User Userovich')

    def test_send_invitation_minimal(self):
        class IsCorrectMail(mox.Comparator):
            def equals(inner_self, message):
                self.assertTrue(message.subject.startswith('Invitation'))
                self.assertTrue('Dear ' not in message.body)
                self.assertTrue('follow the link' not in message.body)
                return True

        mail.mail.Mail(mail.current_app).send(IsCorrectMail())

        self.mox.ReplayAll()
        with self.app.test_request_context():
            mail.send_invitation('uuserovich@example.com',
                                 'THE_CODE')

    def test_send_invitation_ioerror(self):
        mail.mail.Mail(mail.current_app).send(mox.IsA(mail.mail.Message))\
                .AndRaise(IOError('HI'))

        self.mox.ReplayAll()
        with self.app.test_request_context():
            try:
                mail.send_invitation('uuserovich@example.com',
                                     'THE_CODE')
            except IOError, e:
                self.assertEquals('Failed to send e-mail', e.message)
            else:
                self.fail('Exception not raised')

    def test_send_invitation_bad_link(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.assertRaises(exc.IllegalValue,
                              mail.send_invitation,
                              'uuserovich@example.com',
                              'THE_CODE',
                              'https://{{host}}/invites?code={{code}}',
                              'User Userovich')

    def test_send_invitation_other_bad_link(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            self.assertRaises(exc.IllegalValue,
                              mail.send_invitation,
                              'uuserovich@example.com',
                              'THE_CODE',
                              'https://{% if foo %}/foo/{% endif %}/{{code}}',
                              'User Userovich')

    def test_send_reset_password_works(self):
        class IsCorrectMail(mox.Comparator):
            def equals(inner_self, message):
                self.assertTrue(
                        message.subject.startswith('Password reset for'))
                self.assertTrue('https://localhost/?code=THE_CODE'
                                in message.body)
                self.assertTrue('THE_USERNAME' in message.body)
                return True

        mail.mail.Mail(mail.current_app).send(IsCorrectMail())

        self.mox.ReplayAll()
        with self.app.test_request_context():
            mail.send_reset_password(
                'uuserovich@example.com', 'THE_CODE', 'THE_USERNAME',
                link_template='https://localhost/?code={{code}}',
                greeting='User Userowich')

    def test_send_vm_reminder_works(self):
        class IsCorrectMail(mox.Comparator):
            def equals(inner_self, message):
                self.assertEquals('Reminder about VM VM_NAME', message.subject)
                self.assertTrue('2013-01-18 17:16:15 UTC' in message.body)
                return True

        mail.mail.Mail(mail.current_app).send(IsCorrectMail())
        self.mox.ReplayAll()

        with self.app.test_request_context():
            mail.send_vm_reminder('uuserovich@example.com',
                                  'VM_NAME', 'VM_ID',
                                  datetime(2013, 1, 18, 17, 16, 15, 14))

    def test_send_vm_reminder_works_without_expires(self):
        class IsCorrectMail(mox.Comparator):
            def equals(inner_self, message):
                self.assertEquals('Reminder about VM VM_NAME', message.subject)
                self.assertTrue('DELETED' not in message.body)
                return True

        mail.mail.Mail(mail.current_app).send(IsCorrectMail())
        self.mox.ReplayAll()

        with self.app.test_request_context():
            mail.send_vm_reminder('uuserovich@example.com',
                                  'VM_NAME', 'VM_ID')

