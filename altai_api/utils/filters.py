
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

"""Response filtering for collections"""


from altai_api import exceptions as exc


def parse_filters(param_pairs, schema):
    """Parse response filters.

    Returns dictionary of dictionaries name -> filter type -> value.
    """
    result = {}

    for argname, value in param_pairs:
        # filters are parameters with colons in name
        if ':' in argname:
            name, match_type = argname.split(':', 1)
            namefilts = result.setdefault(name, {})
            if match_type in namefilts:
                raise exc.InvalidRequest('Duplicated filters: %s' % argname)
            try:
                namefilts[match_type] = schema.parse_argument(
                        name, match_type, value)
            except KeyError:
                raise exc.UnknownArgument(argname)
    return result


def apply_filters(result, parsed_filters, schema):
    """Apply previously parsed filters to query results"""
    compiled_filters = [
        (name, value, schema.argument_matcher(name, match_type))
        for name, filters in parsed_filters.iteritems()
        for match_type, value in filters.iteritems()]
    return [resource
            for resource in result
            if all((matches(resource[name], value)
                    for name, value, matches in compiled_filters))]

