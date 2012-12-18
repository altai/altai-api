
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


import subprocess
from tests import TestCase, scrpit_path
from altai_api.main import app


class ConfigTestCase(TestCase):
    def setUp(self):
        super(ConfigTestCase, self).setUp()

    def test_settings_are_read(self):
        # we promise we will never redefine TEST_STRING
        self.assertEquals(app.config['TEST_STRING'], 'Test')

    def test_environment_is_considered(self):
        subprocess.check_call(scrpit_path('env_considered_test'))

