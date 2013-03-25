
# vim: tabstop=8 shiftwidth=4 softtabstop=4 expandtab smarttab autoindent

# Altai API Service
# Copyright (C) 2013 Grid Dynamics Consulting Services, Inc
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


import flask
import sys
import traceback

from altai_api import auth
from altai_api import exceptions as exc

from altai_api.utils import make_json_response
from altai_api.utils import audit, communication
from altai_api.utils.http_names import http_code_name, http_code_message

from altai_api.db.config import ConfigDAO


def _traceback_to_json(error):
    _, exc_value, tb = sys.exc_info()
    if exc_value is error and tb is not None:
        # system exception info is still about our error; let's report it
        return [{'filename': filename,
                 'line': line,
                 'function': function}
                for filename, line, function, _ in traceback.extract_tb(tb)]


class ApiApp(flask.Flask):

    def __init__(self, name):
        flask.Flask.__init__(self, name, static_folder=None)

    @staticmethod
    def _handle_altai_api_exception(error):
        return error.get_response_object(), error.status_code, None

    @staticmethod
    def _handle_http_exception(error):
        """Handler for flask.exceptions.HTTPException"""
        error_headers = error.get_response(flask.request.environ).headers
        add_headers = [header for header in error_headers
                       if header[0].lower() not in ('content-type',
                                                    'content-length')]
        response = { 'message': http_code_message(error.code) }
        name = http_code_name(error.code)
        if name:
            response['error-type'] = name
        if error.code == 401:
            add_headers.append(('WWW-Authenticate', 'Basic realm="Altai"'))
        return response, error.code, add_headers

    @staticmethod
    def _handle_other_exception(error):
        """Default handler

        To ease debugging and error reporting we include traceback
        in machine-readable form to error 500 response entity.
        """
        lines = traceback.format_exception_only(type(error), error)
        response = {
            'message': '\n'.join(lines).strip(),
            'error-type': 'UnknownError'
        }
        return response, 500, None

    def _handle_any_exception(self, error):
        if isinstance(error, exc.AltaiApiException):
            return self._handle_altai_api_exception(error)
        if isinstance(error, flask.exceptions.HTTPException):
            return self._handle_http_exception(error)
        return self._handle_other_exception(error)

    def _exception_response(self, error, response, code, add_headers):
        if not isinstance(response, dict):  # pragma: nocover
            response = { 'message': str(response) }
        response['path'] = flask.request.path
        response['method'] = flask.request.method

        tb_mode = self.config['TRACEBACK_IN_RESPONSE']
        if tb_mode == 'always' or (tb_mode == 'auth_500' and code == 500
                                   and auth.is_authenticated()):
            tb = _traceback_to_json(error)
            if tb:
                response['traceback'] = tb
        return make_json_response(response, code, add_headers)

    def handle_user_exception(self, error):
        return self._exception_response(
                    error, *self._handle_any_exception(error))

    def preprocess_request(self):
        """Add our auth, checks and setup before request processing"""
        flask.g.config = ConfigDAO.get
        audit.setup_audit()
        auth.require_auth()
        communication.check_request_headers()
        communication.setup_args_handling()
        communication.parse_my_projects_arg()
        return flask.Flask.preprocess_request(self)

    def handle_exception(self, error):
        # TODO(imelnikov): log exception
        return self._exception_response(
                error, *self._handle_other_exception(error))

