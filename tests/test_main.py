
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


import os
import unittest
import logging.handlers
import mox
from tests.mocked import MockedTestCase

from altai_api import main
from altai_api.utils.periodic_job import PeriodicJob


class ConfigurationTestCase(unittest.TestCase):

    def test_settings_are_read(self):
        # we promise we will never redefine TEST_STRING
        self.assertEquals(main.app.config['TEST_STRING'], 'Test')


class MainTestCase(mox.MoxTestBase):
    config = {
        'USE_RELOADER': False,
        'HOST': '127.0.0.1',
        'PORT': 42
    }
    config_env = main.CONFIG_ENV

    def setUp(self):
        super(MainTestCase, self).setUp()
        self.mox.StubOutWithMock(main, 'app')
        self.mox.StubOutWithMock(main, 'setup_logging')
        self.mox.StubOutWithMock(main, 'check_connection')
        self.mox.StubOutWithMock(main.vms_jobs, 'jobs_factory')

    def tearDown(self):
        main.CONFIG_ENV = self.config_env
        super(MainTestCase, self).tearDown()

    def test_main_works(self):
        main.CONFIG_ENV = 'I_HOPE_THIS_WILL_NEVER_EVER_EXIST'
        main.app.config = self.config
        jobs = [self.mox.CreateMock(PeriodicJob),
                 self.mox.CreateMock(PeriodicJob)]

        main.setup_logging(main.app)
        main.check_connection().AndReturn(True)
        main.vms_jobs.jobs_factory(main.app).AndReturn(jobs)
        main.app.run(use_reloader=False,
                     host='127.0.0.1', port=42)
        jobs[0].cancel().AndRaise(RuntimeError('ignore me'))
        jobs[1].cancel()
        self.mox.ReplayAll()
        main.main()

    def test_main_check_failed(self):
        main.CONFIG_ENV = 'I_HOPE_THIS_WILL_NEVER_EVER_EXIST'
        main.app.config = self.config

        main.setup_logging(main.app)
        main.check_connection().AndReturn(False)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, main.main)

    def test_env_is_looked_at(self):
        main.CONFIG_ENV = os.environ.keys()[0]
        main.app.config = self.mox.CreateMockAnything()

        def side_effect(arg_):
            main.app.config = self.config

        main.app.config.from_envvar(main.CONFIG_ENV)\
                .WithSideEffects(side_effect)
        main.setup_logging(main.app)
        main.check_connection().AndReturn(True)
        main.vms_jobs.jobs_factory(main.app).AndReturn([])
        main.app.run(use_reloader=False,
                     host='127.0.0.1', port=42)
        self.mox.ReplayAll()
        main.main()


class SetupLoggingTestCase(mox.MoxTestBase):
    def setUp(self):
        super(SetupLoggingTestCase, self).setUp()
        self.app = self.mox.CreateMockAnything()
        self.app.config = {
            'LOG_FILE_NAME': None,
            'LOG_LEVEL': 'DEBUG',
            'LOG_FORMAT': '%(asctime)s %(levelname)8s: %(message)s',
            'LOG_DATE_FORMAT': '%Y-%m-%d %H:%M:%S'
        }
        self.logger = self.mox.CreateMockAnything()
        self.app.logger = self.logger

    def test_setup_logging_to_file(self):

        self.logger.addHandler(mox.IsA(
            logging.handlers.WatchedFileHandler))
        self.logger.setLevel(logging.DEBUG)
        self.logger.info('Starting Altai API service v%s', mox.IsA(str))

        self.mox.ReplayAll()
        self.app.config['LOG_FILE_NAME'] = '/dev/null'
        main.setup_logging(self.app)

    def test_setup_logging_to_stderr(self):
        self.logger.addHandler(mox.IsA(logging.StreamHandler))
        self.logger.setLevel(logging.ERROR)
        self.logger.info('Starting Altai API service v%s', mox.IsA(str))

        self.mox.ReplayAll()
        self.app.config['LOG_LEVEL'] = 'ERROR'
        main.setup_logging(self.app)

    def test_setup_logging_bad_level(self):
        self.logger.addHandler(mox.IsA(logging.StreamHandler))
        self.logger.setLevel(logging.INFO)
        self.logger.critical(mox.IsA(str), 'BAD LEVEL')
        self.logger.info('Starting Altai API service v%s', mox.IsA(str))

        self.mox.ReplayAll()
        self.app.config['LOG_LEVEL'] = 'BAD LEVEL'
        main.setup_logging(self.app)


class CheckConnectionTestCase(MockedTestCase):

    def test_check_connection_ok(self):
        self.mox.StubOutWithMock(main.auth, 'api_client_set')
        main.auth.api_client_set()
        self.mox.ReplayAll()
        self.assertEquals(True, main.check_connection())

    def test_check_connection_fail(self):
        self.mox.StubOutWithMock(main.auth, 'api_client_set')
        main.auth.api_client_set().AndRaise(RuntimeError('catch_me'))
        self.mox.ReplayAll()
        self.assertEquals(False, main.check_connection())

