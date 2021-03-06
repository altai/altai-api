
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

"""Miscellaneous utility functions"""

from flask import json, request, abort, g, after_this_request, current_app
from datetime import datetime

import altai_api

from altai_api.auth import is_authenticated
from altai_api import exceptions as exc
from altai_api.utils.parsers import boolean_from_string


# Content type for JSON
_JSON = 'application/json'
_IMPLEMENTATION = 'Altai API service v%s' % altai_api.__version__

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _json_default(obj):
    """A function that we use as default= parameter for json.dumps

    Now it just adds serialization of datetime.datetime

    """
    if isinstance(obj, datetime):
        return obj.strftime(_TIMESTAMP_FORMAT)
    raise TypeError('%r is not JSON serializable' % obj)


def make_json_response(data, status_code=200, add_headers=None):
    """Make json response from response data.
    """
    if data is not None:
        if current_app.config['AUDIT_VERBOSITY'] > 0:
            if status_code >= 400 and 'message' in data:
                g.audit_data['message'] = data['message']

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

    if add_headers:
        for header, value in add_headers:
            response.headers[header] = value

    response.headers['Content-Type'] = _JSON
    if is_authenticated():
        response.headers['X-GD-Altai-Implementation'] = _IMPLEMENTATION
    return response


def make_stream_response(stream, content_length, status_code=200):
    """Make binary response from stream"""
    return current_app.response_class(stream, status=status_code, headers={
        'X-GD-Altai-Implementation': _IMPLEMENTATION,
        'Content-Length': content_length,
        'Content-Type': 'application/octet-stream'
    })


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
    if request.url_rule is None:
        return False
    return getattr(current_app.view_functions[request.url_rule.endpoint],
                   'altai_api_is_data_handler', False)


def _check_request_content():
    """Validates request content type and data

    If request has a body, it must be a JSON object.

    """
    if not request.content_type and not request.data:
        return
    if request.content_type:
        if request.content_type != _JSON:
            raise exc.InvalidRequest('Unsupported content type: %r'
                                     % request.content_type)


def _check_request_expectations():
    expect = request.headers.get('Expect', '')[:4]
    if expect and expect != '200-' and not (
            expect == '204-' and request.method == 'DELETE'):
        abort(417)


def _check_value(value, key, max_val_len):
    if isinstance(value, basestring):
        if len(value) > max_val_len:
            raise exc.InvalidRequest('Length of request element "%s" '
                                     'must not exceed %s'
                                     % (key, max_val_len))
    elif isinstance(value, list):
        for v in value:
            _check_value(v, key, max_val_len)


def _json_object_hook(data):
    max_key_len = current_app.config['MAX_ELEMENT_NAME_LENGTH']
    max_val_len = current_app.config['MAX_PARAMETER_LENGTH']
    for key, value in data.iteritems():
        if isinstance(key, basestring) and len(key) > max_key_len:
            raise exc.InvalidRequest('Bad element name: %r' % key)
        _check_value(value, key, max_val_len)
    return data


def parse_request_data(allowed=None, required=None):
    """Parse request body and check satisfies schema

    This function gets request data from request.json and checks that
    all elements from required schema are present, and all other
    elements are from allowed schema.

    """
    # NOTE(imelnikov): we don't use request.json because we want
    # to raise our custom exception and add our custom validation
    try:
        data = json.loads(request.data, object_hook=_json_object_hook,
                          encoding=request.mimetype_params.get('charset'))
    except ValueError, e:
        raise exc.InvalidRequest('JSON decoding error: %s' % e)

    if not isinstance(data, dict):
        raise exc.InvalidRequest('Bad %s request: JSON object expected'
                                 % request.method)

    result = {}

    if required is not None:
        for t in required.info:
            if t.name not in data:
                raise exc.MissingElement(t.name)
            result[t.name] = t.from_request(data[t.name])

    if allowed is not None:
        for t in allowed.info:
            if t.name in data:
                result[t.name] = t.from_request(data[t.name])

    for name in data:
        if name not in result:
            raise exc.UnknownElement(name=name)

    return result


def parse_my_projects_arg():
    """Parse my-projects request argument and save result to g.my_projects"""
    try:
        g.my_projects = boolean_from_string(request.args['my-projects'])
        g.unused_args.discard('my-projects')
    except KeyError:
        g.my_projects = not g.is_admin
    except ValueError:
        raise exc.InvalidArgumentValue('my-projects', 'boolean',
                                       request.args.get('my-projects'))
    if not g.my_projects and not g.is_admin:
        raise exc.InvalidArgumentValue('my-projects', 'boolean', False,
                               'Only administrators are allowed '
                               'to set my-projects to false')


def setup_args_handling():
    """Set up request arguments handling.

    It creates g.unused_args set, with names of unused parameters.  It
    is expected that as parameters get used, they will be removed from
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
    return current_app.handle_user_exception(
        exc.UnknownArgument(g.unused_args.pop()))

