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

from openstackclient_base.base import monkey_patch
monkey_patch()


__all__ = [ 'app' ]

app = flask.Flask(__name__, static_folder=None)

# default config file
app.config.from_object('altai_api.default_settings')

# optional config file
CONFIG_ENV = 'ALTAI_API_SETTINGS'
if CONFIG_ENV in os.environ:
    app.config.from_envvar(CONFIG_ENV)

from altai_api import entry_points
from altai_api import error_handlers
from altai_api import authentication

# register blueprints
from altai_api.collection.networks import networks
app.register_blueprint(networks, url_prefix='/v1/networks')
from altai_api.collection.instance_types import instance_types
app.register_blueprint(instance_types, url_prefix='/v1/instance-types')
from altai_api.collection.projects import projects
app.register_blueprint(projects, url_prefix='/v1/projects')

def main():
    app.run(debug=app.config['DEBUG'],
            host=app.config['HOST'],
            port=app.config['PORT'])

