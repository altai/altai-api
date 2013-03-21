#!/usr/bin/env python

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

"""Run service or config command locally for test purposes"""

import sys
from os.path import dirname


if __name__ == '__main__':
    sys.path.insert(0, dirname(dirname(__file__)))
    if len(sys.argv) == 1 or sys.argv[1] == 'service':
        import altai_api.main
        altai_api.main.main()
    else:
        import altai_api.command
        altai_api.command.main()

