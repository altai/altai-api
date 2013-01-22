
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2013 Grid Dynamics Consulting Services, Inc
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

import sys
import mox
from tests.mocked import MockedTestCase

from altai_api import exceptions as exc
from altai_api import command


class ShowTest(MockedTestCase):

    def test_die(self):
        self.mox.StubOutWithMock(sys, 'stderr')
        self.mox.StubOutWithMock(sys, 'exit')

        sys.stderr.write('Test message')
        sys.stderr.write('\n')
        sys.exit(1)

        self.mox.ReplayAll()
        command.die('%s %s', 'Test', 'message')

    def test_show_help(self):
        self.mox.StubOutWithMock(command, 'die')
        command.die(mox.IsA(basestring))

        self.mox.ReplayAll()
        command.show_help(['test'])


class CommandsTest(MockedTestCase):

    def setUp(self):
        super(CommandsTest, self).setUp()
        self.mox.StubOutWithMock(command, 'die')
        self.mox.StubOutWithMock(command, 'show_help')
        self.mox.StubOutWithMock(command, 'ConfigDAO')
        self.mox.StubOutWithMock(command, 'DB')
        self.mox.StubOutWithMock(sys, 'stdout')

    def test_init_db_wrong_args(self):
        command.show_help(['test']).AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.init_db, ['test'])

    def test_init_db_works(self):
        self.mox.StubOutWithMock(command, '_DEFAULT_CONFIG')
        test_default_config = (
            ('invitations', 'domains-allowed', []),
            ('general', 'installation-name', 'Test installation')
        )
        command.DB.create_all()
        iter(command._DEFAULT_CONFIG)\
                .AndReturn(iter(test_default_config))
        command.ConfigDAO.set_to('invitations', 'domains-allowed', [])
        command.ConfigDAO.set_to('general', 'installation-name',
                                 'Test installation')
        self.mox.ReplayAll()
        command.init_db(['test', 'init-db'])

    def test_list_vars_wrong_args(self):
        command.show_help(['test']).AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.list_vars, ['test'])

    def test_list_vars_works(self):
        command.ConfigDAO.list_all().AndReturn([('test', 'var1', 42),
                                                ('group', 'var2', 'string')])
        sys.stdout.write('test.var1 = 42')
        sys.stdout.write('\n')
        sys.stdout.write('group.var2 = "string"')
        sys.stdout.write('\n')

        self.mox.ReplayAll()
        command.list_vars(['test', 'list'])

    def test_set_var_wrong_args(self):
        command.show_help(['test']).AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.set_var, ['test'])

    def test_set_var_works(self):
        command.ConfigDAO.set_to('invitations', 'enabled', True)
        self.mox.ReplayAll()
        command.set_var(['test', 'set', 'invitations.enabled', 'true'])

    def test_set_var_bad_value(self):
        self.mox.ReplayAll()
        self.assertRaises(exc.IllegalValue, command.set_var,
                          ['test', 'set', 'invitations.enabled', '42'])

    def test_set_var_bad_name(self):
        command.die(mox.StrContains('parameter'), 'invitations') \
                .AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.set_var,
                          ['test', 'set', 'invitations', 'true'])

    def test_set_var_wrong_name(self):
        command.die(mox.IsA(basestring), 'invitations', 'disabled') \
                .AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.set_var,
                          ['test', 'set', 'invitations.disabled', 'false'])

    def test_set_var_quoted_string(self):
        command.ConfigDAO.set_to('mail', 'sender-name', 'robot')
        self.mox.ReplayAll()
        command.set_var(['test', 'set', 'mail.sender-name', '"robot"'])

    def test_set_var_string(self):
        command.ConfigDAO.set_to('mail', 'sender-name', 'robot')
        self.mox.ReplayAll()
        command.set_var(['test', 'set', 'mail.sender-name', 'robot'])

    def test_get_var_wrong_args(self):
        command.show_help(['test']).AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.get_var, ['test'])

    def test_get_works(self):
        command.ConfigDAO.get('test', 'var').AndReturn('REPLY')
        sys.stdout.write('"REPLY"')
        sys.stdout.write('\n')
        self.mox.ReplayAll()
        command.get_var(['test', 'get', 'test.var'])

    def test_get_none(self):
        command.ConfigDAO.get('test', 'var').AndReturn(None)
        self.mox.ReplayAll()
        command.get_var(['test', 'get', 'test.var'])

    def test_main_no_args(self):
        command.show_help(['test']).AndRaise(SystemExit)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, command.main, ['test'])

    def test_main_catches(self):
        command.show_help(['test']).AndRaise(RuntimeError('catch me'))
        command.die('Failed: %s', mox.IsA(RuntimeError))
        self.mox.ReplayAll()
        command.main(['test'])

    def test_main_works(self):
        ac = self.app.config

        def restore_config(arg_):
            self.app.config = ac

        self.app.config = self.mox.CreateMockAnything()
        self.app.config.from_envvar('ALTAI_API_SETTINGS') \
                .WithSideEffects(restore_config)
        command.ConfigDAO.get('test', 'var').AndReturn(None)
        self.mox.ReplayAll()
        command.main(['test', 'get', 'test.var'])

