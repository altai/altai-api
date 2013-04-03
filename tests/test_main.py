
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


import os
import flask
import logging.handlers
import mox
from tests.mocked import MockedTestCase

from altai_api import main
from altai_api.app import ApiApp
from altai_api.utils.periodic_job import PeriodicJob


class MakeAppTestCase(mox.MoxTestBase):

    def test_settings_are_read(self):
        self.mox.ReplayAll()
        # we promise we will never redefine TEST_STRING
        self.assertEquals(main.make_app(None).config['TEST_STRING'], 'Test')

    def test_make_app_generally_works(self):
        self.mox.StubOutClassWithMocks(main, 'ApiApp')
        self.mox.StubOutWithMock(main.DB, 'init_app')
        self.mox.StubOutWithMock(main, 'register_entry_points')
        os.environ[main.CONFIG_ENV] = 'TEST'

        app = main.ApiApp('altai_api.main')
        app.config = self.mox.CreateMockAnything()

        app.config.from_object('altai_api.default_settings')
        app.config.from_envvar(main.CONFIG_ENV)
        main.DB.init_app(app)
        for _ in xrange(18):
            app.register_blueprint(mox.IsA(flask.Blueprint),
                                   url_prefix=mox.IsA(basestring))
        main.register_entry_points(app)

        self.mox.ReplayAll()
        self.assertEquals(app, main.make_app())


class MainTestCase(mox.MoxTestBase):
    config = {
        'USE_RELOADER': False,
        'HOST': '127.0.0.1',
        'PORT': 42
    }

    def setUp(self):
        super(MainTestCase, self).setUp()
        self.mox.StubOutWithMock(main, 'make_app')
        self.mox.StubOutWithMock(main, 'setup_logging')
        self.mox.StubOutWithMock(main, 'check_connection')
        self.mox.StubOutWithMock(main.instances_jobs, 'jobs_factory')
        self.fake_app = self.mox.CreateMock(ApiApp)
        self.fake_app.config = self.config

    def test_main_works(self):
        main.make_app().AndReturn(self.fake_app)
        jobs = [self.mox.CreateMock(PeriodicJob),
                 self.mox.CreateMock(PeriodicJob)]

        main.setup_logging(self.fake_app)
        main.check_connection(self.fake_app).AndReturn(True)
        main.instances_jobs.jobs_factory(self.fake_app).AndReturn(jobs)
        self.fake_app.run(use_reloader=False,
                          host='127.0.0.1', port=42)
        jobs[0].cancel().AndRaise(RuntimeError('ignore me'))
        jobs[1].cancel()
        self.mox.ReplayAll()
        main.main()

    def test_main_check_failed(self):
        main.make_app().AndReturn(self.fake_app)
        main.setup_logging(self.fake_app)
        main.check_connection(self.fake_app).AndReturn(False)
        self.mox.ReplayAll()
        self.assertRaises(SystemExit, main.main)


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
        self.assertEquals(True, main.check_connection(self.app))

    def test_check_connection_fail(self):
        self.mox.StubOutWithMock(main.auth, 'api_client_set')
        main.auth.api_client_set().AndRaise(RuntimeError('catch_me'))
        self.mox.ReplayAll()
        self.assertEquals(False, main.check_connection(self.app))

