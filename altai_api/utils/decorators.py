
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


def root_endpoint(name):
    """A decorator that marks an endpoint as root endpoint

    All endpoints marked this way will appear in API version entry
    point.

    """
    def decorator(func):
        func.altai_api_root_endpoint = name
        return func
    return decorator


def data_handler(func):
    """A decorator that marks functions as data handler

    Data handlers are endpoints that expect octet-stream as input,
    not JSON.

    """
    func.altai_api_is_data_handler = True
    return func

