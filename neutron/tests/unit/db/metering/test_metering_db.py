# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import contextlib

from neutron_lib.api.definitions import metering as metering_apidef
from neutron_lib import constants as n_consts
from neutron_lib.db import constants as db_const
from neutron_lib.plugins import constants
from oslo_utils import uuidutils
import webob.exc

from neutron.api import extensions
from neutron.common import config
import neutron.extensions
from neutron.services.metering import metering_plugin
from neutron.tests.common import test_db_base_plugin_v2

DB_METERING_PLUGIN_KLASS = (
    "neutron.services.metering."
    "metering_plugin.MeteringPlugin"
)

extensions_path = ':'.join(neutron.extensions.__path__)
_long_description_ok = 'x' * (db_const.LONG_DESCRIPTION_FIELD_SIZE)
_long_description_ng = 'x' * (db_const.LONG_DESCRIPTION_FIELD_SIZE + 1)
_fake_uuid = uuidutils.generate_uuid


class MeteringPluginDbTestCaseMixin:
    def _create_metering_label(self, fmt, name, description, **kwargs):
        data = {'metering_label': {'name': name,
                                   'shared': kwargs.get('shared', False),
                                   'description': description}}
        req = self.new_create_request(
            'metering-labels', data, fmt,
            tenant_id=kwargs.get('tenant_id', self._tenant_id),
            as_admin=kwargs.get('is_admin', True))

        return req.get_response(self.ext_api)

    def _make_metering_label(self, fmt, name, description, **kwargs):
        res = self._create_metering_label(fmt, name, description, **kwargs)
        if res.status_int >= 400:
            raise webob.exc.HTTPClientError(code=res.status_int)
        return self.deserialize(fmt, res)

    def _create_metering_label_rule(self, fmt, metering_label_id, direction,
                                    excluded, remote_ip_prefix=None,
                                    source_ip_prefix=None,
                                    destination_ip_prefix=None,
                                    **kwargs):
        data = {
            'metering_label_rule': {
                        'metering_label_id': metering_label_id,
                        'direction': direction,
                        'excluded': excluded,
                     }
                }

        if remote_ip_prefix:
            data['metering_label_rule']['remote_ip_prefix'] = remote_ip_prefix

        if source_ip_prefix:
            data['metering_label_rule']['source_ip_prefix'] = source_ip_prefix

        if destination_ip_prefix:
            data['metering_label_rule']['destination_ip_prefix'] =\
                destination_ip_prefix

        req = self.new_create_request(
            'metering-label-rules', data, fmt,
            tenant_id=kwargs.get('tenant_id', self._tenant_id),
            as_admin=kwargs.get('is_admin', True))

        return req.get_response(self.ext_api)

    def _make_metering_label_rule(self, fmt, metering_label_id, direction,
                                  excluded, **kwargs):
        res = self._create_metering_label_rule(fmt, metering_label_id,
                                               direction, excluded, **kwargs)
        if res.status_int >= 400:
            raise webob.exc.HTTPClientError(code=res.status_int)
        return self.deserialize(fmt, res)

    @contextlib.contextmanager
    def metering_label(self, name='label', description='desc',
                       fmt=None, **kwargs):
        if 'project_id' in kwargs:
            kwargs['tenant_id'] = kwargs['project_id']
        if not fmt:
            fmt = self.fmt
        metering_label = self._make_metering_label(fmt, name,
                                                   description, **kwargs)
        yield metering_label

    @contextlib.contextmanager
    def metering_label_rule(self, metering_label_id=None, direction='ingress',
                            excluded=False, fmt=None, **kwargs):
        if 'project_id' in kwargs:
            kwargs['tenant_id'] = kwargs['project_id']
        if not fmt:
            fmt = self.fmt
        metering_label_rule = self._make_metering_label_rule(fmt,
                                                             metering_label_id,
                                                             direction,
                                                             excluded,
                                                             **kwargs)
        yield metering_label_rule


class MeteringPluginDbTestCase(
        test_db_base_plugin_v2.NeutronDbPluginV2TestCase,
        MeteringPluginDbTestCaseMixin):
    fmt = 'json'

    resource_prefix_map = {
        k.replace('_', '-'): "/metering"
        for k in metering_apidef.RESOURCE_ATTRIBUTE_MAP.keys()
    }

    def setUp(self, plugin=None):
        service_plugins = {'metering_plugin_name': DB_METERING_PLUGIN_KLASS}

        super().setUp(
            plugin=plugin,
            service_plugins=service_plugins
        )

        self.plugin = metering_plugin.MeteringPlugin()
        ext_mgr = extensions.PluginAwareExtensionManager(
            extensions_path,
            {constants.METERING: self.plugin}
        )
        app = config.load_paste_app('extensions_test_app')
        self.ext_api = extensions.ExtensionMiddleware(app, ext_mgr=ext_mgr)


class TestMetering(MeteringPluginDbTestCase):
    def test_create_metering_label(self):
        name = 'my label'
        description = 'my metering label'
        keys = [('name', name,), ('description', description)]
        with self.metering_label(name, description) as metering_label:
            for k, v, in keys:
                self.assertEqual(metering_label['metering_label'][k], v)

    def test_create_metering_label_shared(self):
        name = 'my label'
        description = 'my metering label'
        shared = True
        keys = [('name', name,), ('description', description),
                ('shared', shared)]
        with self.metering_label(name, description,
                                 shared=shared) as metering_label:
            for k, v, in keys:
                self.assertEqual(metering_label['metering_label'][k], v)

    def test_create_metering_label_with_max_description_length(self):
        res = self._create_metering_label(self.fmt, 'my label',
                                          _long_description_ok)
        self.assertEqual(webob.exc.HTTPCreated.code, res.status_int)

    def test_create_metering_label_with_too_long_description(self):
        res = self._create_metering_label(self.fmt, 'my label',
                                          _long_description_ng)
        self.assertEqual(webob.exc.HTTPBadRequest.code, res.status_int)

    def test_update_metering_label(self):
        name = 'my label'
        description = 'my metering label'
        data = {'metering_label': {}}
        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']
            self._update('metering-labels', metering_label_id, data,
                         webob.exc.HTTPNotImplemented.code)

    def test_delete_metering_label(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']
            self._delete('metering-labels', metering_label_id, 204,
                         as_admin=True)

    def test_list_metering_label(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as v1,\
                self.metering_label(name, description) as v2:
            metering_label = (v1, v2)

            self._test_list_resources('metering-label', metering_label)

    def test_create_metering_label_rule(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']

            direction = 'egress'
            remote_ip_prefix = '192.168.0.0/24'
            excluded = True

            keys = [('metering_label_id', metering_label_id),
                    ('direction', direction),
                    ('excluded', excluded),
                    ('remote_ip_prefix', remote_ip_prefix)]
            with self.metering_label_rule(
                    metering_label_id, direction, excluded,
                    remote_ip_prefix=remote_ip_prefix) as label_rule:
                for k, v, in keys:
                    self.assertEqual(label_rule['metering_label_rule'][k], v)

    def test_create_metering_label_rule_with_non_existent_label(self):
        direction = 'egress'
        remote_ip_prefix = '192.168.0.0/24'
        excluded = True

        res = self._create_metering_label_rule(
            self.fmt, _fake_uuid(), direction, excluded,
            remote_ip_prefix=remote_ip_prefix)
        self.assertEqual(webob.exc.HTTPNotFound.code, res.status_int)

    def test_update_metering_label_rule(self):
        name = 'my label'
        description = 'my metering label'
        direction = 'egress'
        remote_ip_prefix = '192.168.0.0/24'
        data = {'metering_label_rule': {}}
        with self.metering_label(name, description) as metering_label, \
                self.metering_label_rule(
                    metering_label['metering_label']['id'], direction,
                    remote_ip_prefix=remote_ip_prefix) as label_rule:
            rule_id = label_rule['metering_label_rule']['id']
            self._update('metering-label-rules', rule_id, data,
                         webob.exc.HTTPNotImplemented.code, as_admin=True)

    def test_delete_metering_label_rule(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']

            direction = 'egress'
            remote_ip_prefix = '192.168.0.0/24'
            excluded = True

            with self.metering_label_rule(
                    metering_label_id, direction, excluded,
                    remote_ip_prefix=remote_ip_prefix) as label_rule:
                rule_id = label_rule['metering_label_rule']['id']
                self._delete('metering-label-rules', rule_id, 204,
                             as_admin=True)

    def test_list_metering_label_rule(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']

            direction = 'egress'
            remote_ip_prefix = '192.168.0.0/24'
            excluded = True

            with self.metering_label_rule(
                    metering_label_id, direction, excluded,
                    remote_ip_prefix=remote_ip_prefix) as v1,\
                    self.metering_label_rule(
                        metering_label_id, 'ingress', excluded,
                        remote_ip_prefix=remote_ip_prefix) as v2:
                metering_label_rule = (v1, v2)

                self._test_list_resources('metering-label-rule',
                                          metering_label_rule, as_admin=True)

    def test_create_metering_label_rules(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']

            direction = 'egress'
            remote_ip_prefix = '192.168.0.0/24'
            excluded = True

            with self.metering_label_rule(
                    metering_label_id, direction, excluded,
                    remote_ip_prefix=remote_ip_prefix) as v1,\
                    self.metering_label_rule(
                        metering_label_id, direction, False,
                        remote_ip_prefix=n_consts.IPv4_ANY) as v2:
                metering_label_rule = (v1, v2)

                self._test_list_resources('metering-label-rule',
                                          metering_label_rule, as_admin=True)

    def test_create_overlap_metering_label_rules(self):
        name = 'my label'
        description = 'my metering label'

        with self.metering_label(name, description) as metering_label:
            metering_label_id = metering_label['metering_label']['id']

            direction = 'egress'
            remote_ip_prefix1 = '192.168.0.0/24'
            remote_ip_prefix2 = '192.168.0.0/16'
            excluded = True

            with self.metering_label_rule(
                    metering_label_id, direction, excluded,
                    remote_ip_prefix=remote_ip_prefix1):
                res = self._create_metering_label_rule(
                    self.fmt, metering_label_id, direction, excluded,
                    remote_ip_prefix=remote_ip_prefix2)
                self.assertEqual(webob.exc.HTTPConflict.code, res.status_int)

    def test_create_metering_label_rule_two_labels(self):
        name1 = 'my label 1'
        name2 = 'my label 2'
        description = 'my metering label'

        with self.metering_label(name1, description) as metering_label1:
            metering_label_id1 = metering_label1['metering_label']['id']

            with self.metering_label(name2, description) as metering_label2:
                metering_label_id2 = metering_label2['metering_label']['id']

                direction = 'egress'
                remote_ip_prefix = '192.168.0.0/24'
                excluded = True

                with self.metering_label_rule(
                        metering_label_id1, direction, excluded,
                        remote_ip_prefix=remote_ip_prefix) as v1,\
                        self.metering_label_rule(
                            metering_label_id2, direction, excluded,
                            remote_ip_prefix=remote_ip_prefix) as v2:
                    metering_label_rule = (v1, v2)

                    self._test_list_resources('metering-label-rule',
                                              metering_label_rule,
                                              as_admin=True)
