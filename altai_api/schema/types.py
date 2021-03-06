
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

from functools import wraps

from altai_api import exceptions as exc
from altai_api.utils.parsers import (int_from_string,
                                     int_from_user,
                                     boolean_from_string,
                                     cidr_from_user,
                                     ipv4_from_user,
                                     timestamp_from_user,
                                     split_with_escape)


def matcher(func, none_matches=False):
    """Make matcher out of function

    The primary goal is to handle None as value correctly.
    This function may also be used as decorator.

    """
    if getattr(func, 'altai_api_is_matcher', False):
        # don't wrap twice
        return func

    @wraps(func)
    def _matcher(value, pattern):
        if value is None:
            return none_matches
        return func(value, pattern)

    # tag matcher as such
    _matcher.altai_api_is_matcher = True
    return _matcher


@matcher
def not_implemented_matcher(value_, pattern_):
    raise NotImplementedError('Match is not implemented')


def exists_matcher(value, pattern):
    return (value is not None) == pattern

exists_matcher.altai_api_is_matcher = True


def _matchers_plus(dst, matchers):
    """Add matchers to dict

    Never modifies it's args, returns a copy if matchers is not empty.

    """
    if not matchers:  # None, () and {} are OK
        return dst
    result = dst.copy()
    if isinstance(matchers, dict):
        matchers = matchers.iteritems()
    result.update(((name, matcher(value))
                   for name, value in matchers))
    return result


_BASIC_MATCHERS = _matchers_plus({}, (
    ('eq', lambda value, pattern: value == pattern),
    ('in', lambda value, lst: value in lst),
    ('exists', exists_matcher)
))

_ORDERED_MATCHERS = _matchers_plus(_BASIC_MATCHERS, (
    # We make None smaller than any value
    ('gt', matcher(lambda value, pattern: value > pattern)),
    ('ge', matcher(lambda value, pattern: value >= pattern)),
    ('le', matcher(lambda value, pattern: value <= pattern,
                   none_matches=True)),
    ('lt', matcher(lambda value, pattern: value < pattern,
                   none_matches=True))
))


class ElementType(object):
    """Resource element type descriptor"""

    def __init__(self, name, typename,
                 basic_search_matchers,
                 add_search_matchers=None,
                 sortby_names=None,
                 is_nullable=False):
        self.name = name
        self.typename = typename
        self._is_nullable = is_nullable

        self._search_matchers = _matchers_plus(
            basic_search_matchers, add_search_matchers)

        if sortby_names is not None:
            self.sortby_names = sortby_names
        else:
            self.sortby_names = (name,)

    def _illegal_element(self, value, reason=None):
        raise exc.InvalidElementValue(self.name, self.typename, value, reason)

    def _illegal_argument(self, value, reason=None):
        raise exc.InvalidArgumentValue(self.name, self.typename, value, reason)

    def from_argument(self, value):
        """Parse string to this type internal representation"""
        self._illegal_argument(value)

    def from_request(self, value):
        """Check that value from request is correct for this type"""
        if self._is_nullable and value is None:
            return None
        return self._from_request_impl(value)

    def _from_request_impl(self, value):
        self._illegal_element(value)

    def get_search_matcher(self, filter_type):
        """Get search matcher by name.

        Matcher should take a value from result object (in internal
        representation, as returned by from_argument) and a value from
        match string, and return True or False.

        """
        try:
            return self._search_matchers[filter_type]
        except KeyError:
            raise exc.InvalidRequest('No search filter %r defined '
                                     'for element %r of type %r' %
                                     (filter_type, self.name, self.typename))

    def parse_search_argument(self, filter_type, value):
        """Parse search argument of type filter_type"""
        if filter_type == 'in':
            try:
                return [self.from_argument(elem)
                        for elem in split_with_escape(value, '|', '\\')]
            except ValueError, e:
                self._illegal_argument(value, str(e))
        elif filter_type == 'exists':
            return boolean_from_string(value, self._illegal_argument)
        else:
            return self.from_argument(value)


class String(ElementType):
    """'string' element type"""

    def __init__(self, name, **kwargs):
        matchers = _matchers_plus(_BASIC_MATCHERS, {
            'startswith': lambda value, pattern: value.startswith(pattern)
        })
        self.allow_empty = kwargs.pop('allow_empty', False)
        super(String, self).__init__(name=name,
                                     typename='string',
                                     basic_search_matchers=matchers,
                                     **kwargs)

    def from_argument(self, value):
        if not (self.allow_empty or value):
            self._illegal_argument(value, 'This argument cannot be empty')
        return value

    def _from_request_impl(self, value):
        if not isinstance(value, basestring):
            self._illegal_element(value)
        if not (self.allow_empty or value):
            self._illegal_element(value, 'This element cannot be empty')
        return value


class Boolean(ElementType):
    """'boolean' element type"""

    def __init__(self, name, **kwargs):
        super(Boolean, self).__init__(name=name, typename='boolean',
                                      basic_search_matchers=_BASIC_MATCHERS,
                                      **kwargs)

    def from_argument(self, value):
        return boolean_from_string(value, self._illegal_argument)

    def _from_request_impl(self, value):
        if not isinstance(value, bool):
            self._illegal_element(value)
        return value


class Int(ElementType):
    """'uint' element type"""

    def __init__(self, name, min_val=0, max_val=None, **kwargs):
        super(Int, self).__init__(name=name, typename='uint',
                                  basic_search_matchers=_ORDERED_MATCHERS,
                                  **kwargs)
        self.min_val = min_val
        self.max_val = max_val

    def from_argument(self, value):
        return int_from_string(value, self.min_val, self.max_val,
                               on_error=self._illegal_argument)

    def _from_request_impl(self, value):
        return int_from_user(value, self.min_val, self.max_val,
                             on_error=self._illegal_element)


class LinkObject(ElementType):
    """'link object' element type"""

    def __init__(self, name, **kwargs):
        matchers = {
            'eq': matcher(lambda value, pattern: value['id'] == pattern),
            'in': matcher(lambda value, lst: value['id'] in lst),
            'exists': exists_matcher
        }
        super(LinkObject, self).__init__(
            name=name, typename='link object',
            basic_search_matchers=matchers,
            sortby_names=(name + '.id', name + '.name'),
            **kwargs)

    def from_argument(self, value):
        return value

    def _from_request_impl(self, value):
        if not isinstance(value, basestring):
            self._illegal_element(value)
        return value


class Timestamp(ElementType):
    """'timestamp' element type"""

    def __init__(self, name, **kwargs):
        super(Timestamp, self).__init__(
            name=name, typename='timestamp',
            basic_search_matchers=_ORDERED_MATCHERS,
            **kwargs)

    def from_argument(self, value):
        return timestamp_from_user(value, self._illegal_argument)

    def _from_request_impl(self, value):
        return timestamp_from_user(value, self._illegal_element)


class Ipv4(ElementType):
    """'ipv4' element type"""

    def __init__(self, name, **kwargs):
        super(Ipv4, self).__init__(name=name, typename='ipv4',
                                   basic_search_matchers=_BASIC_MATCHERS,
                                   **kwargs)

    def from_argument(self, value):
        return ipv4_from_user(value, on_error=self._illegal_argument)

    def _from_request_impl(self, value):
        return ipv4_from_user(value, on_error=self._illegal_element)


class Cidr(ElementType):
    """'cidr' element type"""

    def __init__(self, name, **kwargs):
        super(Cidr, self).__init__(name=name, typename='cidr',
                                   basic_search_matchers=_BASIC_MATCHERS,
                                   **kwargs)

    def from_argument(self, value):
        return cidr_from_user(value, on_error=self._illegal_argument)

    def _from_request_impl(self, value):
        return cidr_from_user(value, on_error=self._illegal_element)


class List(ElementType):
    def __init__(self, subtype, **kwargs):
        try:
            eq = subtype.get_search_matcher('eq')
            has = lambda value, element: any((eq(v, element) for v in value))

            @matcher
            def match_any(value, pattern):
                return any((has(value, element) for element in pattern))

            @matcher
            def match_all(value, pattern):
                return all((has(value, element) for element in pattern))

            matchers = {
                'any': match_any,
                'all': match_all
            }
        except exc.InvalidRequest:  # no 'eq' matcher
            matchers = {}

        super(List, self).__init__(name=subtype.name,
                                   typename='list<%s>' % subtype.typename,
                                   basic_search_matchers=matchers,
                                   sortby_names=(),
                                   **kwargs)
        self.subtype = subtype

    def _from_request_impl(self, value):
        if not isinstance(value, list):
            self._illegal_element(value)
        return [self.subtype.from_request(v) for v in value]

    def parse_search_argument(self, filter_type, value):
        if filter_type in ('any', 'all'):
            try:
                return [self.subtype.from_argument(elem)
                        for elem in split_with_escape(value, '|', '\\')]
            except ValueError, e:
                self._illegal_argument(value, str(e))
        return super(List, self).parse_search_argument(filter_type, value)

