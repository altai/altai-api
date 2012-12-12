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
from altai_api import utils


@app.before_request
def check_request():
    authentication.require_auth()
    utils.check_request_headers()
    utils.setup_args_handling()
    utils.parse_common_args()
    return None


# register blueprints
from altai_api.collection.networks import networks
app.register_blueprint(networks, url_prefix='/v1/networks')
from altai_api.collection.instance_types import instance_types
app.register_blueprint(instance_types, url_prefix='/v1/instance-types')
from altai_api.collection.projects import projects
app.register_blueprint(projects, url_prefix='/v1/projects')
from altai_api.collection.project_users import project_users
app.register_blueprint(
    project_users, url_prefix='/v1/projects/<project_id>/users')
from altai_api.collection.fw_rule_sets import fw_rule_sets
app.register_blueprint(fw_rule_sets, url_prefix='/v1/fw-rule-sets')
from altai_api.collection.fw_rules import fw_rules
app.register_blueprint(
    fw_rules, url_prefix='/v1/fw-rule-sets/<fw_rule_set_id>/rules')
from altai_api.collection.users import users
app.register_blueprint(users, url_prefix='/v1/users')
from altai_api.collection.vms import vms
app.register_blueprint(vms, url_prefix='/v1/vms')



def main():
    app.run(debug=app.config['DEBUG'],
            host=app.config['HOST'],
            port=app.config['PORT'])

