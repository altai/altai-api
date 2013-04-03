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


__all__ = [ 'make_app', 'main' ]


import os
import sys
import flask
import logging.handlers
import altai_api

from openstackclient_base.base import monkey_patch
monkey_patch()

from altai_api import auth

from altai_api.app import ApiApp
from altai_api.db import DB

from altai_api.entry_points import register_entry_points
from altai_api.jobs import instances as instances_jobs


CONFIG_ENV = 'ALTAI_API_SETTINGS'


def make_app(config_env=CONFIG_ENV):
    app = ApiApp(__name__)
    app.config.from_object('altai_api.default_settings')
    if config_env is not None and config_env in os.environ:
        app.config.from_envvar(config_env)

    DB.init_app(app)

    blueprints = (
         ('audit_log', '/v1/audit-log'),
         ('config', '/v1/config'),
         ('fw_rule_sets', '/v1/fw-rule-sets'),
         ('fw_rules', '/v1/fw-rule-sets/<fw_rule_set_id>/rules'),
         ('nodes', '/v1/nodes'),
         ('images', '/v1/images'),
         ('instance_fw_rule_sets', '/v1/instances/<instance_id>/fw-rule-sets'),
         ('instances', '/v1/instances'),
         ('instance_types', '/v1/instance-types'),
         ('invites', '/v1/invites'),
         ('me', '/v1/me'),
         ('my_ssh_keys', '/v1/me/ssh-keys'),
         ('networks', '/v1/networks'),
         ('projects', '/v1/projects'),
         ('project_users', '/v1/projects/<project_id>/users'),
         ('stats', '/v1/stats'),
         ('users_ssh_keys', '/v1/users/<user_id>/ssh-keys'),
         ('users', '/v1/users')
    )

    # Import blueprints and register them
    for name, path in blueprints:
        module = __import__('altai_api.blueprints.%s' % name,
                            level=0, fromlist=['BP'])
        app.register_blueprint(module.BP, url_prefix=path)

    # NOTE(imelnikov): should be done at the very last
    register_entry_points(app)

    return app


def setup_logging(app):
    log_file_name = app.config['LOG_FILE_NAME']
    if log_file_name is not None:
        log_handler = logging.handlers.WatchedFileHandler(log_file_name)
    else:
        log_handler = logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter(
        app.config['LOG_FORMAT'],
        app.config['LOG_DATE_FORMAT']))
    app.logger.addHandler(log_handler)

    log_level = app.config['LOG_LEVEL']
    if log_level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        app.logger.setLevel(getattr(logging, log_level))
    else:
        app.logger.setLevel(logging.INFO)
        app.logger.critical('Invalid log level: %r', log_level)

    app.logger.info('Starting Altai API service v%s',
                    altai_api.__version__)


def check_connection(app):
    """Attempt to connect to identity service"""
    try:
        with app.test_request_context():
            auth.api_client_set()
        return True
    except Exception, e:
        app.logger.error('Configuration check failed (%s)', e)
    return False


def main():
    app = make_app()
    setup_logging(app)

    if not check_connection(app):
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

