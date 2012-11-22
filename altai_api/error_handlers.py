
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

"""Error response handlers

For most error responses we put machine-readable error information into
the response entities.
"""

import sys, traceback

from flask import request, g
from .main import app
from .utils import make_json_response

from openstackclient_base.exceptions import Unauthorized


@app.errorhandler(Unauthorized)
def authentication_failed_handler(error):
    # TODO(imelnikov): log error
    return '', 403


@app.errorhandler(500)
def exception_handler(error):
    """Internal error handler

    To ease debugging and error reporting we include traceback
    in machine_readble form to error 500 response entity.
    """
    _, exc_value, tb = sys.exc_info()
    message = '\n'.join(traceback.format_exception_only(type(error), error))
    authorized = hasattr(g, 'http_client')

    if not authorized:
        return message, 500

    response = { 'message': message }
    if exc_value is error and tb is not None:
        # system exception info is still about our error; let's report it
        response['traceback'] =  [
                {
                    'filename': filename,
                    'line': line,
                    'function': function
                }
                for filename, line, function, _ in traceback.extract_tb(tb)
            ]
    return make_json_response(response, status_code=500)


@app.errorhandler(404)
def not_found_handler(error):
    response = {
        'path': request.path,
        'message': 'Resource not found.'
    }
    return make_json_response(response, status_code=error.code)

@app.errorhandler(405)
def method_not_allowed_handler(error):
    response = {
        'path': request.path,
        'method': request.method,
        'message': 'Method not allowed for resource.'
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

