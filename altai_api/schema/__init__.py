
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

"""Collection meta-information helpers

Generic code like searching, sorting and validation need collection
meta-information (like resource element types). This module provides
means to express it in a simple way:

_SCHEMA = Schema((
    st.String('id', regexp=ID_REGEXP),
    st.Link('href'),
    st.String('name', add_search_matchers={
        'contains': lambda a, b: b in a
    }),
    st.LinkObject('owner'),
    st.LinkObject('network'),
    st.String('description'),
    st.Link('stats-href'),
    st.Int('cpus-limit'),
    st.Int('ram-limit'),
    st.Int('storage-limit')
))

"""

# A bit of rationale:
#
# * schema is constructed from a list -- we want to remember order
#   e.g. for printing;
# * element types know element name -- for diagnostics (exception
#   messages);
# * element types are classes -- common operations...

from altai_api.utils.parsers import split_with_escape


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

    def argument_matcher(self, name, match_type):
        return self.__dict[name].get_search_matcher(match_type)

    def parse_argument(self, name, match_type, value):
        # ensure match_type is supported:
        self.argument_matcher(name, match_type)
        from_string = self.__dict[name].from_string
        if match_type == 'in':
            return [from_string(elem)
                    for elem in split_with_escape(value, '|', '\\')]
        else:
            return from_string(value)

