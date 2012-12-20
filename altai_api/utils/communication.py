
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

"""Miscellanious utility functions
"""

from flask import json, request, abort, g, after_this_request, current_app
from datetime import datetime

import altai_api

from altai_api.authentication import is_authenticated
from altai_api.utils.parsers import int_from_string
from altai_api.utils.sorting import apply_sortby
from altai_api import exceptions as exc


# Content type for JSON
_JSON = 'application/json'
_IMPELEMENTATION = 'Altai API service v%s' % altai_api.__version__

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _json_default(obj):
    """A function that we use as default= parameter for json.dumps

    Now it just adds serialization of datetime.datetime

    """
    if isinstance(obj, datetime):
        return obj.strftime(_TIMESTAMP_FORMAT)
    raise TypeError('%r is not JSON serializable' % obj)


def make_json_response(data, status_code=200, location=None):
    """Make json response from response data.
    """
    if data is not None:
        if current_app.config.get('PRETTY_PRINT_JSON'):
            data = json.dumps(data, indent=4, sort_keys=True,
                              default=_json_default)
            data += '\n'
        else:
            data = json.dumps(data, separators=(',', ':'),
                              default=_json_default)
    else:
        data = ""
    response = current_app.make_response((data, status_code))
    response.headers['Content-Type'] = _JSON
    if location is not None:
        response.headers['Location'] = location
    if is_authenticated():
        response.headers['X-GD-Altai-Implementation'] = _IMPELEMENTATION
    return response


def make_collection_response(name, elements, parent_href=None):
    """Return a collection to client"""
    result = {
        u'collection': {
            u'name': name,
            u'size': len(elements)
        },
        name: _apply_pagination_and_sorting(elements)
    }
    if parent_href is not None:
        result[u'collection'][u'parent-href'] = parent_href
    return make_json_response(result)


def check_request_headers():
    """Checks that request has all the correct headers"""
    if request.accept_mimetypes and _JSON not in request.accept_mimetypes:
        raise exc.InvalidRequest('Unsupported reply mime types: %s'
                                 % request.accept_mimetypes)
    if request.accept_charsets and 'utf-8' not in request.accept_charsets:
        raise exc.InvalidRequest('Unsupported reply charset: %s'
                                 % request.accept_charsets)
    if any((key.lower().startswith('if-')
            for key in request.headers.iterkeys())):
        raise exc.InvalidRequest('Unsupported conditional header')
    if not _is_data_request():
        # this two functions raise or abort on error:
        _check_request_content()
        _check_request_expectations()
    return None


def _is_data_request():
    """Whether current request is data request

    Data requests need special processing and their handlers check
    request content and headers themselves.

    """
    return all((request.method == 'PUT',
                request.content_type == 'application/octet-stream',
                request.path.endswith('/data')))


def _check_request_content():
    """Validates request content type and data

    If request has a body, it must be a JSON object.

    """
    if request.content_type != _JSON and (
            request.content_type or request.data):
        raise exc.InvalidRequest('Unsupported content type: %r'
                                 % request.content_type)
    if request.method in ('POST', 'PUT') and (
            not request.data or not isinstance(request.json, dict)):
        raise exc.InvalidRequest('Bad %s request: object expected'
                                 % request.method)


def _check_request_expectations():
    expect = request.headers.get('Expect', '')[:4]
    if expect and expect != '200-' and not (
            expect == '204-' and request.method == 'DELETE'):
        abort(417)


def setup_args_handling():
    """Set up request arguments handling.

    It creates g.unused_args set, with names of unused parameters.  It
    is expected that as parameters gets used, they will be removed from
    the set. After request is handled, _check_unused_args_empty verifies
    that all parameters were used, and returns 400 response if not.

    """
    g.unused_args = set(request.args.iterkeys())
    after_this_request(_check_unused_args_empty)


def _check_unused_args_empty(response):
    if not g.unused_args or response.status_code >= 300:
        return response
    # exception raised here will not be passed to handlers
    # so, to be consistent, we call handler directly
    return altai_api.error_handlers.unknown_param_handler(
        exc.UnknownArgument(g.unused_args.pop()))


def parse_common_args():
    try:
        g.limit = int_from_string(request.args.get('limit'),
                                  on_error='Invalid limit value',
                                  allow_none=True)
        g.offset = int_from_string(request.args.get('offset'),
                                   on_error='Invalid offset value',
                                   allow_none=True)
    except ValueError, e:
        raise exc.InvalidRequest(str(e))


def _apply_pagination_and_sorting(result):
    """Apply previously parsed pagination to given request result."""
    g.unused_args.discard('limit')
    g.unused_args.discard('offset')
    if g.offset:
        result = result[g.offset:]
    if g.limit:
        result = result[:g.limit]
    if 'sortby' in g.unused_args:
        g.unused_args.discard('sortby')
        result = apply_sortby(g.sortby, result)
    return result
