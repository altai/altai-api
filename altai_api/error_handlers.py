
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

"""Error response handlers

For most error responses we put machine-readable error information into
the response entities.
"""

import sys
import traceback

from flask import request, url_for
from altai_api import exceptions as exc

from altai_api.main import app
from altai_api.utils import make_json_response
from altai_api.auth import is_authenticated


@app.errorhandler(401)
def authentication_needed_handler(error):
    response = make_json_response(
        { 'message': 'You have to login with proper credentials' },
        status_code=401)

    entry_point = url_for('get_versions', _external=True)
    response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % (
        entry_point.split('//', 1)[1].strip('/')
    )
    return response


@app.errorhandler(exc.AltaiApiException)
def altai_api_exception_handler(error):
    return make_json_response(error.get_response_object(),
                              status_code=error.status_code)


@app.errorhandler(500)
def exception_handler(error):
    """Internal error handler

    To ease debugging and error reporting we include traceback
    in machine-readable form to error 500 response entity.
    """
    _, exc_value, tb = sys.exc_info()

    lines = traceback.format_exception_only(type(error), error)
    response = {
        'message': '\n'.join(lines),
        'path': request.path,
        'method': request.method,
    }

    if is_authenticated() and exc_value is error and tb is not None:
        # system exception info is still about our error; let's report it
        response['traceback'] = [
                {
                    'filename': filename,
                    'line': line,
                    'function': function
                }
                for filename, line, function, _ in traceback.extract_tb(tb)
            ]
    return make_json_response(response, status_code=500)


def multy_error_handler(messages):
    def make_error_handler(func, message):
        return lambda error: func(error, message)

    def decorator(func):
        for code, message in messages.iteritems():
            app.errorhandler(code)(make_error_handler(func, message))
        return func
    return decorator


@multy_error_handler({
    403: 'Unauthorized.',
    404: 'Resource not found.',
    405: 'Method not allowed for resource.',
    411: 'Content-Length required for this request.',
    417: 'Unsupported client expectations.'
})
def common_error_handler(error, message):
    response = {
        'path': request.path,
        'method': request.method,
        'message': message
    }
    return make_json_response(response, status_code=error.code)


@app.errorhandler(301)
def redirect_handler(error):
    response = {
        'path': request.path,
        'message': 'Resource is located elsewhere.',
        'new-url': error.new_url
    }
    return make_json_response(response,
                              status_code=error.code,
                              location=error.new_url)

