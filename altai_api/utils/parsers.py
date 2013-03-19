
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


"""Parsers and validators for external data"""


from datetime import datetime


_OS_TIMESTAMP_FORMATS = (
    # NOTE(imelnikov): git grep strftime enlightens
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.000Z"
)


def timestamp_from_openstack(date):
    """Parse date from a string OpenStack gave us.

    OpenStack API may give us strings in several formats.

    """
    if not isinstance(date, basestring):
        raise TypeError('%r is not a date value' % date)
    for fmt in _OS_TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            pass
    raise ValueError('Invalid timestamp: %r' % date)


def _raise(value, on_error):
    if callable(on_error):
        on_error(value)
    else:
        raise ValueError('%s: %r' % (on_error or 'Invalid value', value))


def int_from_user(value, min_val=0, max_val=None, on_error=None):
    """Check that value is good int"""
    try:
        assert isinstance(value, int) or isinstance(value, long)
        assert value >= min_val
        if max_val is not None:
            assert value <= max_val
        return value
    except AssertionError:
        _raise(value, on_error)


def int_from_string(value, min_val=0, max_val=None,
                    on_error=None, allow_none=False):
    """Convert a string to an int, with strong checks."""
    try:
        if value is None and allow_none:
            return None
        assert isinstance(value, basestring)
        assert value == '0' or not value.startswith('0')
        return int_from_user(int(value), min_val, max_val)
    except (ValueError, AssertionError):
        _raise(value, on_error)


def _parse_ipv4(value):
    assert isinstance(value, basestring)
    str_octets = value.split('.')
    assert len(str_octets) == 4
    return [int_from_string(x, 0, 255) for x in str_octets]


def ipv4_from_user(value, on_error=None):
    """Check that string represents IPv4

    Returns value in canonical form.

    """
    try:
        int_octets = _parse_ipv4(value)
        return '.'.join((str(x) for x in int_octets))
    except (ValueError, AssertionError):
        _raise(value, on_error)


def _octets_obey_mask(octets, mask):
    """Check that address has zeroes in lower bits as specified by mask

    Address should be represented as iterable over octets, higher
    octets first. Mask should be represented as integer.

    """
    bin_addr = 0
    for octet in octets:
        bin_addr = (bin_addr << 8) | octet
    lower_bits = (1 << 32 - mask) - 1
    return (bin_addr & lower_bits) == 0


def cidr_from_user(value, on_error=None):
    """Check that string represents IPv4 CIDR

    Returns value in canonical form

    """
    try:
        assert isinstance(value, basestring)
        addr, net = value.split('/')
        octets = _parse_ipv4(addr)
        ret_addr = '.'.join((str(x) for x in octets))
        ret_net = int_from_string(net, min_val=0, max_val=32)
        assert _octets_obey_mask(octets, ret_net)
        return '%s/%s' % (ret_addr, ret_net)
    except (AssertionError, ValueError):
        _raise(value, on_error)


_BOOLEAN_STRINGS = {
    'True': True,
    'true': True,
    'False': False,
    'false': False
}


def boolean_from_string(value, on_error=None):
    """Parse boolean value"""
    try:
        return _BOOLEAN_STRINGS[value]
    except KeyError:
        _raise(value, on_error)


def split_with_escape(value, split, esc='\\'):
    if len(esc) != 1:
        raise ValueError('Bad value for escape string: %r' % esc)
    if len(split) != 1:
        raise ValueError('Bad value for split: %r' % split)

    cur = []
    escape = False

    for char in value:
        if escape:
            if char in (split, esc):
                cur.append(char)
                escape = False
            else:
                raise ValueError('Unknown escape sequence: \\%s' % char)
        else:
            if char == esc:
                escape = True
            elif char == split:
                yield ''.join(cur)
                cur = []
            else:
                cur.append(char)
    if escape:
        raise ValueError('Escape char at the end of the line')
    yield ''.join(cur)

