
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

from tests.db import ContextWrappedDBTestCase
from altai_api.db.config import ConfigDAO


class ConfigDAOTestCase(ContextWrappedDBTestCase):

    def setUp(self):
        super(ConfigDAOTestCase, self).setUp()
        self.group = 'group'
        self.name = 'test'
        self.value = 42
        ConfigDAO.set_to(self.group, self.name, self.value)

    def test_get(self):
        self.assertEquals(self.value, ConfigDAO.get(self.group, self.name))

    def test_get_none(self):
        self.assertEquals(None, ConfigDAO.get(self.group, 'non-existing var'))

    def test_list_all(self):
        l = list(ConfigDAO.list_all())
        self.assertEquals(l, [(self.group, self.name, self.value)])

    def test_list_group(self):
        ConfigDAO.set_to('te', 'st', {'5': 0})
        ConfigDAO.set_to('te', 'st2', 'a string')
        l = list(sorted(ConfigDAO.list_group('te')))
        self.assertEquals(l, [('te', 'st', {'5': 0}),
                              ('te', 'st2', 'a string')])

    def test_set(self):
        new_value = {'new': 'value'}
        ConfigDAO.set_to(self.group, self.name, new_value)
        self.assertEquals(new_value, ConfigDAO.get(self.group, self.name))

