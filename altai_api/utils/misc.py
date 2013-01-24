
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

"""Miscellaneous utility functions"""

_MB = 1024 * 1024
_GB = 1024 * 1024 * 1024


def _div_ceil(dividend, divisor):
    """Divide dividend to divisor with rounding up"""
    return int((dividend + divisor - 1) / divisor)


def to_mb(size):
    """Convert size from bytes to megabytes, rounding up"""
    return _div_ceil(size, _MB)


def from_mb(size):
    """Convert size from megabytes to bytes"""
    return size * _MB


def to_gb(size):
    """Convert size from bytes to gigabytes, rounding up"""
    return _div_ceil(size, _GB)


def from_gb(size):
    """Convert size from gigabytes to bytes"""
    return size * _GB


