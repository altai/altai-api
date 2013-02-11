
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

import time
import unittest
import flask
from datetime import datetime, timedelta
from tests.mocked import MockedTestCase

from altai_api.utils import periodic_job


class PeriodicJobTestCase(unittest.TestCase):

    def check_times(self, when, started, deltas):
        self.assertEquals(len(when), len(deltas))
        for idx in xrange(len(deltas)):
            ref = started + timedelta(seconds=deltas[idx])
            diff = when[idx] - ref
            if abs(diff) > timedelta(seconds=0.1):
                self.fail('Times are too different: '
                          'expected %s, got %s (idx=%s)'
                          % (ref, when[idx], idx))

    def test_periodic_job_works(self):
        when = []
        started = datetime.utcnow()

        def append_now(lst):
            lst.append(datetime.utcnow())

        job = periodic_job.PeriodicJob(0.5, append_now, when)
        time.sleep(1.2)
        job.cancel()
        self.check_times(when, started, [0, 0.5, 1])
        time.sleep(0.4)
        self.assertEquals(len(when), 3, 'Job did not stop.')

    def test_long_job_ok(self):
        when = []
        started = datetime.utcnow()

        def append_now(lst):
            lst.append(datetime.utcnow())
            if len(lst) == 1:
                time.sleep(0.8)

        job = periodic_job.PeriodicJob(0.5, append_now, when)
        time.sleep(1.4)
        job.cancel()
        self.check_times(when, started, [0, 0.8, 1.3])

    def test_job_may_raise(self):
        when = []
        started = datetime.utcnow()

        def append_now(lst):
            lst.append(datetime.utcnow())
            if len(when) == 1:
                raise RuntimeError('ignore me')

        job = periodic_job.PeriodicJob(0.5, append_now, when)
        time.sleep(0.7)
        job.cancel()
        self.check_times(when, started, [0, 0.5])


class PeriodicAdministrativeJobTestCase(MockedTestCase):

    def test_job_works(self):
        evidence = []

        def test_fun(arg):
            self.install_fake_auth()
            evidence.extend((arg, flask.g.client_set))

        self.mox.ReplayAll()
        job = periodic_job.PeriodicAdministrativeJob(
            self.app, 0.5, test_fun, 'test')
        time.sleep(0.1)
        job.cancel()
        self.assertEquals(evidence, ['test', self.fake_client_set])

    def test_job_exception(self):
        self.mox.StubOutWithMock(self.app.logger, 'exception')
        self.app.logger.exception('Periodic job failed')
        self.mox.ReplayAll()

        def test_fun(_):
            raise RuntimeError('catch me')

        job = periodic_job.PeriodicAdministrativeJob(
            self.app, 0.5, test_fun, 'test')
        time.sleep(0.1)
        job.cancel()

