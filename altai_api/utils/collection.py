
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

from flask import g, request

from altai_api import exceptions as exc

from altai_api.utils.parsers import int_from_string
from altai_api.utils.communication import make_json_response

from altai_api.utils.sorting import parse_sortby, apply_sortby
from altai_api.utils.filters import parse_filters, apply_filters


def make_collection_response(name, elements, parent_href=None):
    """Return a collection to client"""
    size = len(elements)

    if getattr(g, 'filters', None):
        g.unused_args.difference_update(
            (arg for arg in request.args.iterkeys() if ':' in arg))
        elements = apply_filters(elements, g.filters,
                                 g.collection_schema)

    if 'sortby' in g.unused_args:
        g.unused_args.discard('sortby')
        elements = apply_sortby(g.sortby, elements)
    elements = _apply_pagination(elements)

    result = {
        u'collection': {
            u'name': name,
            u'size': size
        },
        name: elements
    }
    if parent_href is not None:
        result[u'collection'][u'parent-href'] = parent_href
    return make_json_response(result)


def _parse_pagination():
    try:
        g.limit = int_from_string(request.args.get('limit'),
                                  on_error='Invalid limit value',
                                  allow_none=True)
        g.offset = int_from_string(request.args.get('offset'),
                                   on_error='Invalid offset value',
                                   allow_none=True)
    except ValueError, e:
        raise exc.InvalidRequest(str(e))


def _apply_pagination(result):
    """Apply previously parsed pagination to given request result."""
    g.unused_args.discard('limit')
    g.unused_args.discard('offset')
    if g.offset:
        result = result[g.offset:]
    if g.limit:
        result = result[:g.limit]
    return result


def parse_collection_request(schema):
    """Parse request arguments and save them into flask.g for farther use"""
    _parse_pagination()
    g.collection_schema = schema
    g.sortby = parse_sortby(request.args.get('sortby'), schema.sortby_names)
    g.filters = parse_filters(request.args.iteritems(multi=True), schema)

