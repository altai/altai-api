
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

from altai_api.db import DB
from tests import TestCase, ContextWrappedTestCase


class DBTestCase(TestCase):
    def setUp(self):
        super(DBTestCase, self).setUp()
        # use memory backend by default
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        with self.app.test_request_context():
            DB.create_all()

    def tearDown(self):
        with self.app.test_request_context():
            DB.drop_all()
        super(DBTestCase, self).tearDown()


# NOTE(imelnikov): order of inheritance matters, so we decided
# to provide base class that works
class ContextWrappedDBTestCase(DBTestCase, ContextWrappedTestCase):
    pass

