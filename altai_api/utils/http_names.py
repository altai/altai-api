
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

"""Names and text descriptions for HTTP status codes >= 300"""

_HTTP_NAMES = {
    300: 'MultipleChoices',
    301: 'MovedPermanently',
    302: 'Found',
    303: 'SeeOther',
    304: 'NotModified',
    305: 'UseProxy',
    306: 'SwitchProxy',
    307: 'TemporaryRedirect',
    308: 'PermanentRedirect',
    400: 'BadRequest',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'NotFound',
    405: 'MethodNotAllowed',
    406: 'NotAcceptable',
    408: 'RequestTimeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'LengthRequired',
    412: 'PreconditionFailed',
    413: 'RequestEntityTooLarge',
    414: 'RequestURITooLong',
    415: 'UnsupportedMediaType',
    416: 'RequestedRangeNotSatisfiable',
    417: 'ExpectationFailed',
    418: 'IAmATeapot',
    500: 'InternalServerError',
    501: 'NotImplemented',
    502: 'BadGateway',
    503: 'ServiceUnavailable',
}

# loosely based on exception descriptions from werkzeug

_HTTP_MESSAGES = {
    300: 'Multiple options for the resource that the client follow.',
    301: 'This and all future requests should be directed to the given URI.',
    302: 'This request should be repeated with another URI',
    303: 'This request should be repeated with another URI',
    304: 'Resource has not been modified since the version specified.',
    305: 'The requested resource is only available through a proxy.',
    306: 'Subsequent requests should use the specified proxy.',
    307: 'This request should be repeated with another URI',
    308: 'The request, and all future requests should be repeated '
         'using another URI.',
    400: 'The browser (or proxy) sent a request '
         'that this server could not understand.',
    401: 'You have to login with proper credentials.',
    403: "You don't have the permission to access the requested resource.",
    404: 'The requested URL was not found on the server. '
         'If you entered the URL manually please check your spelling '
         'and try again.',
    405: 'Method not allowed for requested URL.',
    406: 'The resource identified by the request is only capable of '
         'generating response entities which have content characteristics '
         'not acceptable according to the accept headers sent in the request.',
    408: "The server closed the network connection because the browser didn't "
         "finish the request within the specified time.",
    409: 'A conflict happened while processing the request. The resource '
         'might have been modified while the request was being processed.',
    410: 'The requested URL is no longer available on this server and there '
         'is no forwarding address. If you followed a link from a foreign '
         'page, please contact the author of that page.',
    411: 'A request with this method requires a valid Content-Length header.',
    412: 'The precondition on the request for the URL '
         'failed positive evaluation.',
    413: 'The data value transmitted exceeds the capacity limit.',
    414: 'The length of the requested URL exceeds the capacity limit '
         'for this server.  The request cannot be processed.',
    415: 'The server does not support the media type '
         'transmitted in the request.',
    416: 'The server cannot provide the requested range.',
    417: 'The server could not meet the requirements of the Expect header',
    418: 'This server is a teapot, not a coffee machine',
    500: 'The server encountered an internal error and was unable '
         'to complete your request. Either the server is overloaded '
         'or there is an error in the application.',
    501: 'The server does not support the action requested by the browser.',
    502: 'The proxy server received an invalid response from '
         'an upstream server.',
    503: 'The server is temporarily unable to service your request '
         'due to maintenance downtime or capacity problems. '
         'Please try again later.'
}


def http_code_name(code):
    return _HTTP_NAMES.get(code)


def http_code_message(code):
    try:
        return _HTTP_MESSAGES[code]
    except KeyError:
        return 'HTTP response %s' % code

