
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


from altai_api import exceptions as exc
from altai_api.utils.parsers import (int_from_string,
                                     cidr_from_user,
                                     ipv4_from_user)
from datetime import datetime


_BASIC_MATCHERS = dict((
    ('eq', lambda a, b: a == b),
    # TODO: parser for 'in' matcher
    # ('in', lambda a, lst: a in lst)
))

_ORDERED_MATCHERS = _BASIC_MATCHERS.copy()
_ORDERED_MATCHERS.update((
    ('gt', lambda a, b: a > b),
    ('ge', lambda a, b: a >= b),
    ('le', lambda a, b: a <= b),
    ('lt', lambda a, b: a < b)
))


class ElementType(object):
    """Resource element type descriptor"""

    def __init__(self, name, typename,
                 search_matchers=None):
        self.name = name
        self.typename = typename
        if search_matchers is not None:
            self._search_matchers = search_matchers
        else:
            self._search_matchers = _BASIC_MATCHERS
        self.sortby_names = (name,)

    def _raise(self, value):
        raise exc.IllegalValue(self.name, self.typename, value)

    def from_string(self, value):
        """Parse string to this type internal representation"""
        self._raise(value)

    def get_search_matcher(self, filter_type):
        """Get search matcher by name.

        Matcher should take a value from result object (in internal
        representation, as returned by from_string) and a value from
        match string, and return True or False.

        """
        try:
            return self._search_matchers[filter_type]
        except KeyError:
            raise exc.InvalidRequest('No search filter %r defined '
                                     'for element %r of type %r' %
                                     (filter_type, self.name, self.typename))


class String(ElementType):
    """'string' element type"""

    def __init__(self, name, add_search_matchers=None):
        matchers = _BASIC_MATCHERS.copy()
        matchers['startswith'] = lambda a, b: a.startswith(b)
        if add_search_matchers is not None:
            matchers.update(add_search_matchers)
        super(String, self).__init__(name=name,
                                     typename='string',
                                     search_matchers=matchers)

    def from_string(self, string):
        return string


class Boolean(ElementType):
    """'boolean' element type"""

    _STRINGS = {
        'True': True,
        'true': True,
        'False': False,
        'false': False
    }

    def __init__(self, name):
        super(Boolean, self).__init__(name=name, typename='boolean')

    def from_string(self, value):
        try:
            return self._STRINGS[value]
        except KeyError:
            self._raise(value)


class Int(ElementType):
    """'uint' element type"""

    def __init__(self, name, min_val=0, max_val=None):
        super(Int, self).__init__(name=name, typename='uint',
                                   search_matchers=_ORDERED_MATCHERS)
        self.min_val = min_val
        self.max_val = max_val

    def from_string(self, value):
        return int_from_string(value, self.min_val, self.max_val,
                               on_error=self._raise)


class LinkObject(ElementType):
    """'link object' element type"""

    def __init__(self, name):
        matchers = {
            'eq': lambda a, b: a['id'] == b,
            # 'in': lambda a, lst: a['id'] in lst,
        }
        super(LinkObject, self).__init__(name=name, typename='link object',
                                         search_matchers=matchers)
        self.sortby_names = (name + '.id', name + '.name')

    def from_string(self, value):
        return value


class Timestamp(ElementType):
    """'timestamp' element type"""

    def __init__(self, name):
        super(Timestamp, self).__init__(name=name, typename='timestamp',
                                        search_matchers=_ORDERED_MATCHERS)

    def from_string(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            self._raise(value)


class Ipv4(ElementType):
    """'ipv4' element type"""

    def __init__(self, name):
        super(Ipv4, self).__init__(name=name, typename='ipv4')

    def from_string(self, value):
        return ipv4_from_user(value, on_error=self._raise)


class Cidr(ElementType):
    """'cidr' element type"""

    def __init__(self, name):
        super(Cidr, self).__init__(name=name, typename='cidr')

    def from_string(self, value):
        return cidr_from_user(value, on_error=self._raise)

