
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

import flask
import traceback


class AltaiApiException(Exception):
    def __init__(self, message, status_code, reason=None):
        super(AltaiApiException, self).__init__(message)
        self.status_code = status_code
        self.reason = reason

    def get_response_object(self):
        lines = traceback.format_exception_only(type(self), self)
        result = {
            'message': '\n'.join(lines),
            'path': flask.request.path,
            'method': flask.request.method,
            'error-type': self.__class__.__name__
        }
        if self.reason:
            result['reason'] = self.reason
        return result


class InvalidRequest(AltaiApiException):
    """Exception raised on invalid requests"""

    def __init__(self, message):
        super(InvalidRequest, self).__init__(message, 400)


class InvalidElement(InvalidRequest):

    def __init__(self, message, name):
        super(InvalidElement, self).__init__(message)
        self.name = name

    def get_response_object(self):
        rv = super(InvalidElement, self).get_response_object()
        rv['element-name'] = self.name
        return rv


class UnknownElement(InvalidElement):
    """Exception raised when unknown elements are present in response"""

    def __init__(self, name):
        super(UnknownElement, self).__init__(
            'Unknown resource element: %r' % name, name)


class MissingElement(InvalidElement):
    """Exception raised when required request elements are missing"""

    def __init__(self, name):
        super(MissingElement, self).__init__(
            'Required element is missing: %r' % name, name)


class InvalidElementValue(InvalidElement):
    """Exception raised when request element has illegal value"""

    def __init__(self, name, typename, value, reason=None):
        msg = 'Invalid value for element %s of type %s: %r' \
                % (name, typename, value)
        if reason:
            msg = '%s (%s)' % (msg, reason)

        super(InvalidElementValue, self).__init__(msg, name)
        self.typename = typename
        self.value = value
        self.reason = reason

    def get_response_object(self):
        rv = super(InvalidElementValue, self).get_response_object()
        rv['element-value'] = self.value
        rv['element-type'] = self.typename
        return rv


class InvalidArgument(InvalidRequest):
    """Exception raised when invalid argument is supplied for request"""

    def __init__(self, message, name):
        super(InvalidArgument, self).__init__(message)
        self.name = name

    def get_response_object(self):
        rv = super(InvalidArgument, self).get_response_object()
        rv['argument-name'] = self.name
        return rv


class UnknownArgument(InvalidArgument):
    """Exception raised when unknown arguments are present in request"""

    def __init__(self, name):
        super(UnknownArgument, self).__init__(
            'Unknown request argument: %r' % name, name)


class InvalidArgumentValue(InvalidArgument):
    """Exception raised when some client input has illegal value"""

    def __init__(self, name, typename, value, reason=None):
        msg = 'Invalid value for argument %s of type %s: %r' \
                % (name, typename, value)
        if reason:
            msg = '%s (%s)' % (msg, reason)

        super(InvalidArgumentValue, self).__init__(msg, name)
        self.typename = typename
        self.value = value
        self.reason = reason

    def get_response_object(self):
        rv = super(InvalidArgumentValue, self).get_response_object()
        rv['argument-value'] = self.value
        rv['argument-type'] = self.typename
        return rv

