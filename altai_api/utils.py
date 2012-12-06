
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

from flask import json, request, abort, g, after_this_request

import altai_api

from altai_api.main import app
from altai_api.authentication import is_authenticated
from altai_api import exceptions as exc


# Content type for JSON
_JSON = 'application/json'
_IMPELEMENTATION = 'Altai API service v%s' % altai_api.__version__


def make_json_response(data, status_code=200, location=None):
    """Make json response from response data.
    """
    if data is not None:
        if app.config.get('PRETTY_PRINT_JSON'):
            data = json.dumps(data, indent=4, sort_keys=True)
        else:
            data = json.dumps(data, separators=(',',':'))
    else:
        data = ""
    response = app.make_response((data, status_code))
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
        name: _apply_pagination(elements)
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
    if request.content_type != _JSON and (
            request.content_type or request.data):
        raise exc.InvalidRequest('Unsupported content type: %r'
                                 % request.content_type)
    if any((key.lower().startswith('if-')
            for key in request.headers.iterkeys())):
        raise exc.InvalidRequest('Unsupported conditional header')
    expect = request.headers.get('Expect')
    if expect is not None:
        code = expect[:4]
        if code != '200-' and not (code == '204-'
                                   and request.method == 'DELETE'):
            abort(417)
    return None


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
    if not g.unused_args or response.status_code >= 400:
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


def _apply_pagination(result):
    """Apply previously parsed pagination to given request result."""
    g.unused_args.discard('limit')
    g.unused_args.discard('offset')
    if g.offset:
        result = result[g.offset:]
    if g.limit:
        result = result[:g.limit]
    return result


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

