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

"""Application entry point"""

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


def _mount_collections(iterable):
    """Import collection blueprints and register them"""
    for name, path in iterable:
        module = __import__('altai_api.collection.%s' % name,
                            level=0, fromlist=[name])
        blueprint = getattr(module, name)
        app.register_blueprint(blueprint, url_prefix=path)


_mount_collections((
    ('networks', '/v1/networks'),
    ('instance_types', '/v1/instance-types'),
    ('projects', '/v1/projects'),
    ('project_users', '/v1/projects/<project_id>/users'),
    ('fw_rule_sets', '/v1/fw-rule-sets'),
    ('fw_rules', '/v1/fw-rule-sets/<fw_rule_set_id>/rules'),
    ('users', '/v1/users'),
    ('vms', '/v1/vms'),
    ('vm_fw_rule_sets', '/v1/vms/<vm_id>/fw-rule-sets')
))


def main():
    app.run(debug=app.config['DEBUG'],
            host=app.config['HOST'],
            port=app.config['PORT'])

