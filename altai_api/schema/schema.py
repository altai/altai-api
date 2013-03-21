
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

# A bit of rationale:
#
# * schema is constructed from a list -- we want to remember order
#   e.g. for printing;
# * element types know element name -- for diagnostics (exception
#   messages);
# * element types are classes -- common operations...


class Schema(object):

    def __init__(self, info, **kwargs):
        self.info = info
        self.__dict = dict(((t.name, t) for t in info))
        self.sortby_names = set()
        for t in info:
            self.sortby_names.update(t.sortby_names)

        for key, val in kwargs.iteritems():
            if hasattr(self, key):
                raise ValueError('Bad schema subset name: %r' % key)
            sub_schema = Schema(tuple((t for t in info if t.name in val)))
            setattr(self, key, sub_schema)

    def from_request(self, name, value):
        return self.__dict[name].from_request(value)

    def argument_matcher(self, name, match_type):
        return self.__dict[name].get_search_matcher(match_type)

    def parse_argument(self, name, match_type, value):
        element = self.__dict[name]
        # ensure this filter type is supported:
        element.get_search_matcher(match_type)
        return element.parse_search_argument(match_type, value)

