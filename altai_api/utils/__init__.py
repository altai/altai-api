
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

"""Altai API miscellaneous utilities"""

__all__ = [
    'make_json_response',
    'parse_request_data',
    'make_collection_response',
    'parse_collection_request',
    'set_audit_resource_id'
]


from altai_api.utils.communication import (make_json_response,
                                           parse_request_data)
from altai_api.utils.collection import (make_collection_response,
                                        parse_collection_request)
from altai_api.utils.audit import set_audit_resource_id

