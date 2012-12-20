
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


"""Parsers and validators for external data"""


from datetime import datetime


_OS_TIMESTAMP_FORMATS = (
    # NOTE(imelnikov): git grep strftime enlightenes
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


def ipv4_from_user(value, on_error=None):
    """Check that string represents IPv4

    Returns value in canonical form.

    """
    try:
        assert isinstance(value, basestring)
        str_octets = value.split('.')
        assert len(str_octets) == 4
        int_octets = [int_from_string(x, 0, 255)
                      for x in str_octets]
        return '.'.join((str(x) for x in int_octets))
    except (ValueError, AssertionError):
        _raise(value, on_error)


def cidr_from_user(value, on_error=None):
    """Check that string represents IPv4 CIDR

    Returns value in canonical form

    """
    try:
        assert isinstance(value, basestring)
        addr, net = value.split('/')
        ret_addr = ipv4_from_user(addr)
        ret_net = int_from_string(net, min_val=0, max_val=32)
        return '%s/%s' % (ret_addr, ret_net)
    except (AssertionError, ValueError):
        _raise(value, on_error)

