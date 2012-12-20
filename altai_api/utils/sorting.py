
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

"""Collection sorting"""


from flask import request, g
from altai_api import exceptions as exc


def _get_nested(data, keys):
    for k in keys:
        data = data.get(k)
        if data is None:
            return None
    return data


def _parse_one_sortby_item(item, allowed_names):
    """Convert one item of sortby list to internal represintation."""
    elems = item.rsplit(':', 1)

    name = elems[0]
    if name not in allowed_names:
        raise exc.InvalidRequest(
            'Could not sort: bad parameter: %r' % elems[0])

    if len(elems) == 1 or elems[1] == 'asc':
        is_asc = True
    elif elems[1] == 'desc':
        is_asc = False
    else:
        raise exc.InvalidRequest('Invalid sorting direction: %r' % elems[1])

    keys = name.split('.')
    if len(keys) == 1:
        keyfun = lambda x: x.get(name)
    else:
        keyfun = lambda x: _get_nested(x, keys)
    return name, is_asc, keyfun


def parse_sortby(param, allowed_names):
    """Parse sortby query parameter.

    Performs some checking and returns special data structure
    that can be passed to _apply_sortby function (see below).
    """
    if param is None:
        return None
    return [_parse_one_sortby_item(x, allowed_names)
            for x in param.split(',')]


def setup_sorting(allowed_names):
    """Parses sortby parameter and saves it to flask.g fr farther use"""
    param = request.args.get('sortby')
    g.sortby = parse_sortby(param, set(allowed_names))


def apply_sortby(how, result):
    """Apply sorting to target.

    Takes result of parse_sortby and a list and sorts list as
    specified.
    """
    if how is None:
        return result

    def compare(val1, val2):
        for _, is_asc, keyfun in how:
            res = cmp(keyfun(val1), keyfun(val2))
            if res != 0:
                return res if is_asc else -res
        return 0
    return sorted(list(result), compare)

