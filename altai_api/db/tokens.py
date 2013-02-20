
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

import os

from datetime import datetime
from base64 import urlsafe_b64encode

from altai_api.db import DB


class Token(DB.Model):
    __tablename__ = 'tokens'

    code = DB.Column(DB.String(32), primary_key=True)
    token_type = DB.Column(DB.String(32), nullable=False)
    email = DB.Column(DB.String(120), nullable=False)
    user_id = DB.Column(DB.String(64), nullable=False)
    complete = DB.Column(DB.Boolean, nullable=False, default=False)
    created_at = DB.Column(DB.DateTime, nullable=False,
                           default=datetime.utcnow)
    complete_at = DB.Column(DB.DateTime, nullable=True, default=None)


def _generate_random_token():
    """Generate a random string usable as token"""
    return urlsafe_b64encode(os.urandom(24))


class TokensDAO(object):

    def __init__(self, token_type):
        self.token_type = token_type

    def create(self, user_id, email):
        token = Token(code=_generate_random_token(),
                      token_type=self.token_type,
                      user_id=user_id, email=email)
        DB.session.add(token)
        DB.session.commit()
        return token

    def get(self, code):
        return Token.query.filter_by(token_type=self.token_type,
                                     code=code).first_or_404()

    def get_for_user(self, user_id):
        """Get invitation for current user

        Returns None if no incomplete token of needed type exists for
        given user id.

        """
        return Token.query\
                .filter_by(token_type=self.token_type,
                           complete=False,
                           user_id=user_id)\
                .order_by(Token.created_at)\
                .first()

    def complete(self, token):
        """Complete the token"""
        if token.token_type != self.token_type:
            raise ValueError('Invalid token type')
        token.complete = True
        token.complete_at = datetime.utcnow()
        DB.session.commit()

    def complete_for_user(self, user_id):
        """Complete all tokens for given user.

        Returns number of tokens affected.

        """
        affected = Token.query\
                .filter_by(token_type=self.token_type,
                           complete=False,
                           user_id=user_id)\
                .update(dict(complete=True,
                             complete_at=datetime.utcnow()))
        DB.session.commit()
        return affected

