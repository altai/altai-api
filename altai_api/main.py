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

"""Application entry point
"""

import os
import flask
__all__ = [ 'app', 'make_json_response', 'version_string', 'request' ]

app = flask.Flask(__name__, static_folder=None)

# default config file
app.config.from_object('altai_api.default_settings')

# optional config file
CONFIG_ENV = 'ALTAI_API_SETTINGS'
if CONFIG_ENV in os.environ:
    app.config.from_envvar(CONFIG_ENV)

from . import entry_points
from . import error_handlers
from . import authentication

# register blueprints
from .vm_types import vm_types
app.register_blueprint(vm_types, url_prefix='/v1/vm-types')

def main():
    app.run()

