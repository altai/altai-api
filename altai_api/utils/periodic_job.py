
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


from threading import Timer, Lock
from datetime import datetime

from altai_api.db import DB
from altai_api.auth import keystone_auth


class PeriodicJob(object):
    """Run a function as a periodic job

    Runs given function periodically with given interval. Interval is
    specified in seconds and may be float. If function is takes too long,
    next run is scheduled immediately (e.g. interval is maximal possible
    pause between function runs).

    """

    def __init__(self, interval, function, *args, **kwargs):
        self.interval = float(interval)
        self.function = function
        self.args = args
        self.kwargs = kwargs

        self._timer_lock = Lock()  # protects self.timer and self.is_running
        self._timer = None
        self._is_running = True
        self._start_timer(0)  # run first iteration ASAP

    def cancel(self):
        """Cancel the job

        After this method is called, no more runs of the job are scheduled.

        """
        with self._timer_lock:
            self._is_running = False
            self._timer.cancel()

    def _start_timer(self, interval):
        with self._timer_lock:
            if self._is_running:
                self._timer = Timer(interval, self._run)
                self._timer.start()

    def _run(self):
        started = datetime.utcnow()
        try:
            self.function(*self.args, **self.kwargs)
            # TODO(imelnikov): catch and log exceptions
        finally:
            # schedule next iteration
            self._start_timer(
                self._reduce_interval(datetime.utcnow() - started))

    def _reduce_interval(self, delta):
        # NOTE(imelnikov): timedelta.total_seconds only available since
        # python 2.7, so we calculate it manually:
        seconds = (delta.seconds
                   + delta.microseconds / 1.0e6
                   + delta.days * 86400)
        return max(0, self.interval - seconds)


def _wrap_with_context(app, function):
    def wrapper(*args, **kwargs):
        with app.test_request_context():
            try:
                if keystone_auth(app.config['KEYSTONE_ADMIN'],
                                 app.config['KEYSTONE_ADMIN_PASSWORD']):
                    return function(*args, **kwargs)
                else:
                    app.logger.error(
                        'Service misconfiguration: '
                        'failed to authenticate as API admin user')
            finally:
                DB.session.remove()
    return wrapper


class PeriodicAdministrativeJob(PeriodicJob):
    def __init__(self, app, interval, function, *args, **kwargs):
        PeriodicJob.__init__(self, interval,
                              _wrap_with_context(app, function),
                              *args, **kwargs)

