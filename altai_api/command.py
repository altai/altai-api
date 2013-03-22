
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


"""Altai API script"""

import sys
from flask import json

from altai_api.main import make_app
from altai_api.db import DB
from altai_api.db.config import ConfigDAO
from altai_api.blueprints.config import SCHEMAS


def die(message, *args):
    sys.stderr.write(message % args)
    sys.stderr.write('\n')
    sys.exit(1)


_USAGE_TEMPLATE = """Usage:
    %(progname)s list
        List all known configuration variables, with values
    %(progname)s set <varname> <value>
        Set variable <varname> to value <value
    %(progname)s get <varname>
        Print value of variable <varname>
    %(progname)s init-db
        Create database for Altai API (database should not exist)
    %(progname)s help
    %(progname)s --help
        Show this message
"""


def show_help(argv):
    die(_USAGE_TEMPLATE % dict(progname=argv[0]))


def _set_value(group, name, value):
    try:
        value = SCHEMAS[group].from_request(name, value)
    except KeyError:
        die('Unknown configuration variable: %s.%s', group, name)
    ConfigDAO.set_to(group, name, value)


_DEFAULT_CONFIG = [
    ('general', 'installation-name', 'Altai Private Cloud for Developers'),
    ('mail', 'sender-name', 'Altai MailBot'),
    ('mail', 'sender-mail', 'altai-maibot@example.com'),
    ('mail', 'footer', '--\nWith best regards,\nAltai MailBot\n'),
    ('invitations', 'enabled', True),
    ('invitations', 'domains-allowed', []),
    ('password-reset', 'enabled', True)
]


def init_db(argv):
    if len(argv) != 2:
        show_help(argv)
    DB.create_all()
    for group, name, value in _DEFAULT_CONFIG:
        _set_value(group, name, value)


def list_vars(argv):
    if len(argv) != 2:
        show_help(argv)
    for group, name, value in ConfigDAO.list_all():
        data = json.dumps(value, indent=4, sort_keys=True)
        print '%s.%s = %s' % (group, name, data)


def set_var(argv):
    if len(argv) != 4:
        show_help(argv)
    try:
        data = json.loads(argv[3])
    except Exception:
        data = argv[3]
    try:
        group, name = argv[2].split('.', 1)
    except ValueError:
        die('Invalid parameter name: %s', argv[2])
    _set_value(group, name, data)


def get_var(argv):
    if len(argv) != 3:
        show_help(argv)
    group, name = argv[2].split('.', 1)
    value = ConfigDAO.get(group, name)
    if value is not None:
        print json.dumps(value, indent=4, sort_keys=True)


_COMMANDS = {
    'init-db': init_db,
    'list': list_vars,
    'set': set_var,
    'get': get_var,
}


def main(argv=None):
    try:
        argv = argv if argv is not None else sys.argv
        try:
            command = _COMMANDS.get(argv[1])
        except (KeyError, IndexError):
            show_help(argv)
        with make_app().test_request_context():
            command(argv)
    except Exception, e:
        die('Failed: %s', e)

