
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

from altai_api import auth


def root_endpoint(name):
    """A decorator that marks an endpoint as root endpoint

    All endpoints marked this way will appear in API version entry
    point.

    """
    def decorator(func):
        func.altai_api_root_endpoint = name
        return func
    return decorator


def no_auth_endpoint(func):
    """Mark endpoint as accessible without authentication

    This decorator should be used to mark endpoints that need to be
    accessible without authentication. For such endpoints authentication
    headers provided by users are ignored.

    """
    setattr(func, auth.ATTRIBUTE_NAME, auth.no_auth)
    return func


def user_endpoint(func):
    """Mark endpoint as accessible by non-administrators."""
    setattr(func, auth.ATTRIBUTE_NAME, auth.user_auth)
    return func


def admin_endpoint(func):
    """Mark endpoint as accessible by administrators only."""
    setattr(func, auth.ATTRIBUTE_NAME, auth.admin_auth)
    return func


def data_handler(func):
    """A decorator that marks functions as data handler

    Data handlers are endpoints that expect octet-stream as input,
    not JSON.

    """
    func.altai_api_is_data_handler = True
    return func

