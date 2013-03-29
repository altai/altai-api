
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
))

"""

from altai_api.schema.schema import Schema

