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

"""Application entry point"""

import os
import sys
import flask
import logging.handlers
import altai_api

from openstackclient_base.base import monkey_patch
monkey_patch()


__all__ = [ 'app' ]

app = flask.Flask(__name__, static_folder=None)
app.config.from_object('altai_api.default_settings')


from altai_api.db import DB
DB.init_app(app)

from altai_api import entry_points
from altai_api import stats
from altai_api import error_handlers
from altai_api import auth

from altai_api.utils import audit
from altai_api.utils import communication

from altai_api.jobs import instances as instances_jobs

from altai_api.db.config import ConfigDAO


@app.before_request
def check_request():
    flask.g.config = ConfigDAO.get
    audit.setup_audit()
    auth.require_auth()
    communication.check_request_headers()
    communication.setup_args_handling()
    communication.parse_my_projects_arg()
    return None


def _mount_blueprints(iterable):
    """Import blueprints and register them"""
    for name, path in iterable:
        module = __import__('altai_api.blueprints.%s' % name,
                            level=0, fromlist=['BP'])
        app.register_blueprint(module.BP, url_prefix=path)


_mount_blueprints((
     ('networks', '/v1/networks'),
     ('instance_types', '/v1/instance-types'),
     ('projects', '/v1/projects'),
     ('project_users', '/v1/projects/<project_id>/users'),
     ('fw_rule_sets', '/v1/fw-rule-sets'),
     ('fw_rules', '/v1/fw-rule-sets/<fw_rule_set_id>/rules'),
     ('users', '/v1/users'),
     ('instances', '/v1/instances'),
     ('instance_fw_rule_sets', '/v1/instances/<instance_id>/fw-rule-sets'),
     ('images', '/v1/images'),
     ('invites', '/v1/invites'),
     ('config', '/v1/config'),
     ('audit_log', '/v1/audit-log'),
     ('me', '/v1/me'),
     ('users_ssh_keys', '/v1/users/<user_id>/ssh-keys'),
     ('my_ssh_keys', '/v1/me/ssh-keys')
))


CONFIG_ENV = 'ALTAI_API_SETTINGS'


def setup_logging(application):
    log_file_name = application.config['LOG_FILE_NAME']
    if log_file_name is not None:
        log_handler = logging.handlers.WatchedFileHandler(log_file_name)
    else:
        log_handler = logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter(
        application.config['LOG_FORMAT'],
        application.config['LOG_DATE_FORMAT']))
    application.logger.addHandler(log_handler)

    log_level = application.config['LOG_LEVEL']
    if log_level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        application.logger.setLevel(getattr(logging, log_level))
    else:
        application.logger.setLevel(logging.INFO)
        application.logger.critical('Invalid log level: %r', log_level)

    application.logger.info('Starting Altai API service v%s',
                            altai_api.__version__)


def check_connection():
    """Attempt to connect to identity service"""
    try:
        with app.test_request_context():
            auth.api_client_set()
        return True
    except Exception, e:
        app.logger.error('Configuration check failed (%s)', e)
    return False


def main():
    if CONFIG_ENV in os.environ:
        app.config.from_envvar(CONFIG_ENV)
    setup_logging(app)

    if not check_connection():
        sys.exit(1)

    periodic_jobs = []
    if not app.config['USE_RELOADER'] \
       or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        periodic_jobs.extend(instances_jobs.jobs_factory(app))
    try:
        app.run(use_reloader=app.config['USE_RELOADER'],
                host=app.config['HOST'],
                port=app.config['PORT'])
    finally:
        for job in periodic_jobs:
            try:
                job.cancel()
            except Exception:
                pass

