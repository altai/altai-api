
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


class InvalidRequest(Exception):
    """Exception raised on invalid requests"""

    def __init__(self, message):
        super(InvalidRequest, self).__init__(message)


class UnknownElement(InvalidRequest):
    """Exception raised when required request elements are missing"""

    def __init__(self, name):
        super(UnknownElement, self).__init__(
            'Unknown resource element: %r' % name)
        self.name = name


class MissingElement(InvalidRequest):
    """Exception raised when required request elements are missing"""

    def __init__(self, name):
        super(MissingElement, self).__init__(
            'Required element is missing: %s' % name)
        self.name = name


class IllegalValue(InvalidRequest):
    """Exception raised when resource element has illegal value"""

    def __init__(self, name, typename, value):
        super(IllegalValue, self).__init__(
            'Illegal value for element %s of type %s: %r'
                % (name, typename, value))
        self.name = name
        self.typename = typename
        self.value = value


class UnknownArgument(InvalidRequest):
    """Exception raised when required request elements are missing"""

    def __init__(self, name):
        super(UnknownArgument, self).__init__(
            'Unknown request argument: %s' % name)
        self.name = name

