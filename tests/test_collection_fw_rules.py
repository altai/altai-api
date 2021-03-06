
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

import json

from tests import doubles
from tests.mocked import MockedTestCase

from openstackclient_base import exceptions as osc_exc
from altai_api.blueprints import fw_rules


class RuleConvertNovaTestCase(MockedTestCase):
    to_view = {
        u'id': 1,
        u'ip_protocol': u'tcp',
        u'from_port': 80,
        u'to_port': 88,
        u'parent_group_id': 42,
        u'ip_range': {
            u'cidr': u'10.0.0.0/8'
        },
        u'group': {}
    }
    expected = {
        u'id': u'1',
        u'href': u'/v1/fw-rule-sets/42/rules/1',
        u'protocol': u'TCP',
        u'port-range-first': 80,
        u'port-range-last': 88,
        u'source': u'10.0.0.0/8'
    }

    def test_rule_dict_to_view_works(self):
        self.mox.ReplayAll()
        with self.app.test_request_context():
            res = fw_rules._fw_rule_dict_to_view(self.to_view)
        self.assertEquals(res, self.expected)

    def test_rule_object_to_view_works(self):
        rule = doubles.make(self.mox, doubles.SecurityGroupRule,
                            **self.to_view)
        self.mox.ReplayAll()
        with self.app.test_request_context():
            res = fw_rules._fw_rule_object_to_view(rule)
        self.assertEquals(res, self.expected)


class FwRulesTestCase(MockedTestCase):

    def setUp(self):
        super(FwRulesTestCase, self).setUp()
        self.mox.StubOutWithMock(fw_rules, '_fw_rule_dict_to_view')
        self.mox.StubOutWithMock(fw_rules.auth, 'assert_admin_or_project_user')

    def test_list_works(self):
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'42', name='Test SG', tenant_id='TENANT',
                          rules=['RULE1', 'RULE2'])

        self.fake_client_set.compute.security_groups.get(sg.id).AndReturn(sg)
        fw_rules.auth.assert_admin_or_project_user('TENANT', eperm_status=404)
        fw_rules._fw_rule_dict_to_view('RULE1').AndReturn('REPLY1')
        fw_rules._fw_rule_dict_to_view('RULE2').AndReturn('REPLY2')

        expected = {
            'collection': {
                'name': 'rules',
                'size': 2,
                'parent-href': '/v1/fw-rule-sets/%s' % sg.id
            },
            'rules': [ 'REPLY1', 'REPLY2' ]
        }

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s/rules/' % sg.id)
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, expected)

    def test_list_not_found(self):
        sgid = u'42'
        self.fake_client_set.compute.security_groups.get(sgid) \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s/rules/' % sgid)
        self.check_and_parse_response(rv, 404)

    def test_get_works(self):
        ruleid = u'2'
        rules = [{ u'id': 1, u'FAKE': u'fst' },
                 { u'id': 2, u'FAKE': u'snd' },
                 { u'id': 4, u'FAKE': u'lst' } ]
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'42', name='Test SG',
                          rules=rules, tenant_id='PID')

        self.fake_client_set.compute.security_groups.get(sg.id).AndReturn(sg)
        fw_rules.auth.assert_admin_or_project_user('PID', eperm_status=404)

        fw_rules._fw_rule_dict_to_view(rules[1]).AndReturn('REPLY')

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s/rules/%s' % (sg.id, ruleid))
        data = self.check_and_parse_response(rv)
        self.assertEquals(data, 'REPLY')

    def test_get_set_not_found(self):
        sgid, ruleid = u'42', u'2'
        self.fake_client_set.compute.security_groups.get(sgid) \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s/rules/%s' % (sgid, ruleid))
        self.check_and_parse_response(rv, 404)

    def test_get_invalid_rule(self):
        sgid, ruleid = u'42', u'invalid'

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s/rules/%s' % (sgid, ruleid))
        self.check_and_parse_response(rv, 404)

    def test_get_rule_not_found(self):
        ruleid = u'2'
        rules = [  # no rule with id '2':
            { u'id': 1, u'FAKE': u'fst' },
            { u'id': 3, u'FAKE': u'snd' },
            { u'id': 4, u'FAKE': u'lst' } ]
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'42', name='Test SG',
                          rules=rules, tenant_id='PID')

        self.fake_client_set.compute.security_groups.get(sg.id).AndReturn(sg)
        fw_rules.auth.assert_admin_or_project_user('PID', eperm_status=404)

        self.mox.ReplayAll()
        rv = self.client.get('/v1/fw-rule-sets/%s/rules/%s' % (sg.id, ruleid))
        self.check_and_parse_response(rv, 404)

    def test_delete_works(self):
        ruleid = u'2'
        rules = [{ u'id': 1, u'FAKE': u'fst' },
                 { u'id': 2, u'FAKE': u'snd' },
                 { u'id': 4, u'FAKE': u'lst' }]
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'42', name='Test SG',
                          rules=rules, tenant_id='PID')

        self.fake_client_set.compute.security_groups.get(sg.id).AndReturn(sg)
        fw_rules.auth.assert_admin_or_project_user('PID', eperm_status=404)
        self.fake_client_set.compute.security_group_rules.delete(ruleid)

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/fw-rule-sets/%s/rules/%s'
                                % (sg.id, ruleid))
        self.check_and_parse_response(rv, 204)

    def test_delete_group_not_found(self):
        sgid, ruleid = u'42', u'2'
        self.fake_client_set.compute.security_groups.get(sgid) \
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/fw-rule-sets/%s/rules/%s'
                                % (sgid, ruleid))
        self.check_and_parse_response(rv, 404)

    def test_delete_rule_not_found(self):
        ruleid = u'2'
        rules = [  # no rule with id '2':
            { u'id': 1, u'FAKE': u'fst' },
            { u'id': 3, u'FAKE': u'snd' },
            { u'id': 4, u'FAKE': u'lst' } ]
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'42', name='Test SG',
                          rules=rules, tenant_id='PID')

        self.fake_client_set.compute.security_groups.get(sg.id).AndReturn(sg)
        fw_rules.auth.assert_admin_or_project_user('PID', eperm_status=404)

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/fw-rule-sets/%s/rules/%s'
                                % (sg.id, ruleid))
        self.check_and_parse_response(rv, 404)

    def test_delete_late_not_found(self):
        ruleid = u'2'
        rules = [{ u'id': 1, u'FAKE': u'fst' },
                 { u'id': 2, u'FAKE': u'snd' },
                 { u'id': 4, u'FAKE': u'lst' }]
        sg = doubles.make(self.mox, doubles.SecurityGroup,
                          id=u'42', name='Test SG',
                          rules=rules, tenant_id='PID')

        self.fake_client_set.compute.security_groups.get(sg.id).AndReturn(sg)
        fw_rules.auth.assert_admin_or_project_user('PID', eperm_status=404)
        self.fake_client_set.compute.security_group_rules.delete(ruleid)\
                .AndRaise(osc_exc.NotFound('failure'))

        self.mox.ReplayAll()
        rv = self.client.delete('/v1/fw-rule-sets/%s/rules/%s'
                                % (sg.id, ruleid))
        self.check_and_parse_response(rv, 204)


class CreateRuleTestCase(MockedTestCase):
    sgid = u'42'

    def setUp(self):
        super(CreateRuleTestCase, self).setUp()
        self.mox.StubOutWithMock(fw_rules, '_fw_rule_object_to_view')
        self.mox.StubOutWithMock(fw_rules, '_get_security_group')
        self.mox.StubOutWithMock(fw_rules.auth, 'client_set_for_tenant')
        self.sg = doubles.make(self.mox, doubles.SecurityGroup,
                               id=self.sgid, name='Test SG',
                               rules=[], tenant_id='PID')
        self.tcs = self._fake_client_set_factory()

    def interact(self, params, expected_status_code=200):
        rv = self.client.post('/v1/fw-rule-sets/%s/rules/' % self.sgid,
                              content_type='application/json',
                              data=json.dumps(params))
        return self.check_and_parse_response(rv, expected_status_code)

    def test_create_rule_no_ports(self):
        fw_rules._get_security_group(self.sgid).AndReturn(self.sg)
        fw_rules.auth.client_set_for_tenant('PID', fallback_to_api=True,
                                            eperm_status=404) \
                .AndReturn(self.tcs)
        self.tcs.compute.security_group_rules.create(
            parent_group_id=self.sgid,
            ip_protocol=u'tcp',
            from_port=-1,
            to_port=-1,
            cidr='10.0.0.0/8').AndReturn('Created rule')
        fw_rules._fw_rule_object_to_view('Created rule').AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact({ u'protocol': u'TCP', u'source': u'10.0.0.0/8' })
        self.assertEquals(data, 'REPLY')

    def test_create_fw_rule_bad_port(self):
        self.mox.ReplayAll()
        params = {
            'protocol': 'TCP',
            'source': '10.0.0.0/8',
            'port-range-first': 100500
        }
        data = self.interact(params, expected_status_code=400)
        self.assertEquals('port-range-first', data.get('element-name'))
        self.assertEquals(100500, data.get('element-value'))

    def test_create_fw_rule_bad_protocol(self):
        self.mox.ReplayAll()
        params = {
            'protocol': 'tcp',
            'source': '10.0.0.0/8',
        }
        data = self.interact(params, expected_status_code=400)
        self.assertEquals('protocol', data.get('element-name'))
        self.assertEquals('tcp', data.get('element-value'))

    def test_create_rule_one_port(self):
        fw_rules._get_security_group(self.sgid).AndReturn(self.sg)
        fw_rules.auth.client_set_for_tenant('PID', fallback_to_api=True,
                                            eperm_status=404) \
                .AndReturn(self.tcs)
        self.tcs.compute.security_group_rules.create(
            parent_group_id=self.sgid,
            ip_protocol=u'tcp',
            from_port=80,
            to_port=80,
            cidr='10.0.0.0/8').AndReturn('Created rule')
        fw_rules._fw_rule_object_to_view('Created rule').AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact({
            u'protocol': u'TCP',
            u'port-range-first': 80,
            u'source': u'10.0.0.0/8'
        })
        self.assertEquals(data, 'REPLY')

    def test_create_rule_two_port(self):
        fw_rules._get_security_group(self.sgid).AndReturn(self.sg)
        fw_rules.auth.client_set_for_tenant('PID', fallback_to_api=True,
                                            eperm_status=404) \
                .AndReturn(self.tcs)
        self.tcs.compute.security_group_rules.create(
            parent_group_id=self.sgid,
            ip_protocol=u'tcp',
            from_port=42,
            to_port=60042,
            cidr='10.0.0.0/8').AndReturn('Created rule')
        fw_rules._fw_rule_object_to_view('Created rule').AndReturn('REPLY')

        self.mox.ReplayAll()

        data = self.interact({
            u'protocol': u'TCP',
            u'port-range-first': 42,
            u'port-range-last': 60042,
            u'source': u'10.0.0.0/8'
        })
        self.assertEquals(data, 'REPLY')

    def test_create_rule_late_not_found(self):
        fw_rules._get_security_group(self.sgid).AndReturn(self.sg)
        fw_rules.auth.client_set_for_tenant('PID', fallback_to_api=True,
                                            eperm_status=404) \
                .AndReturn(self.tcs)
        self.tcs.compute.security_group_rules.create(
            parent_group_id=self.sgid,
            ip_protocol=u'tcp',
            from_port=-1,
            to_port=-1,
            cidr='10.0.0.0/8')\
                .AndRaise(osc_exc.NotFound('gone'))

        self.mox.ReplayAll()
        self.interact({ u'protocol': u'TCP', u'source': u'10.0.0.0/8' },
                      expected_status_code=404)

