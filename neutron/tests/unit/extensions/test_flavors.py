#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import copy
from unittest import mock

import fixtures
from neutron_lib import context
from neutron_lib.db import api as db_api
from neutron_lib.db import constants as db_const
from neutron_lib.exceptions import flavors as flav_exc
from neutron_lib.plugins import constants
from oslo_config import cfg
from oslo_utils import uuidutils
from webob import exc

from neutron.db.models import l3 as l3_models
from neutron.db import servicetype_db
from neutron.extensions import flavors
from neutron.objects import flavor as flavor_obj
from neutron.services.flavors import flavors_plugin
from neutron.services import provider_configuration as provconf
from neutron.tests import base
from neutron.tests.common import test_db_base_plugin_v2
from neutron.tests.unit.api.v2 import test_base
from neutron.tests.unit import dummy_plugin
from neutron.tests.unit.extensions import base as extension

_uuid = uuidutils.generate_uuid
_get_path = test_base._get_path

_driver = ('neutron.tests.unit.extensions.test_flavors.'
           'DummyServiceDriver')
_provider = dummy_plugin.RESOURCE_NAME
_long_name = 'x' * (db_const.NAME_FIELD_SIZE + 1)
_long_description = 'x' * (db_const.LONG_DESCRIPTION_FIELD_SIZE + 1)


class FlavorExtensionTestCase(extension.ExtensionTestCase):

    def setUp(self):
        super().setUp()
        ctx = context.get_admin_context()
        ctx.project_id = 'test-project'
        self.env = {'neutron.context': ctx}
        self.setup_extension(
            'neutron.services.flavors.flavors_plugin.FlavorsPlugin',
            constants.FLAVORS, flavors.Flavors, '',
            supported_extension_aliases=['flavors'])

    def test_create_flavor(self):
        # Use service_type FLAVORS since plugin must be loaded to validate
        data = {'flavor': {'name': 'GOLD',
                           'service_type': constants.FLAVORS,
                           'description': 'the best flavor',
                           'enabled': True}}

        expected = copy.deepcopy(data)
        expected['flavor']['service_profiles'] = []

        instance = self.plugin.return_value
        instance.create_flavor.return_value = expected['flavor']
        res = self.api.post(_get_path('flavors', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/%s' % self.fmt,
                            extra_environ=self.env)

        # NOTE(slaweq): we need to do such complicated assertion as in the
        # arguments of the tested method may or may not be 'tenant_id' and
        # 'project_id' included. It is not really needed but in the neutron-lib
        # versions <= 3.13 is is included and should be gone once bug
        # https://bugs.launchpad.net/neutron/+bug/2022043/ will be fixed
        actual_flavor_arg = instance.create_flavor.call_args.kwargs['flavor']
        actual_flavor_arg['flavor'].pop('project_id', None)
        actual_flavor_arg['flavor'].pop('tenant_id', None)
        self.assertDictEqual(expected, actual_flavor_arg)
        res = self.deserialize(res)
        self.assertIn('flavor', res)
        self.assertEqual(expected, res)

    def test_create_flavor_invalid_service_type(self):
        data = {'flavor': {'name': 'GOLD',
                           'service_type': 'BROKEN',
                           'description': 'the best flavor',
                           'enabled': True}}
        self.api.post(_get_path('flavors', fmt=self.fmt),
                      self.serialize(data),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_create_flavor_too_long_name(self):
        data = {'flavor': {'name': _long_name,
                           'service_type': constants.FLAVORS,
                           'description': 'the best flavor',
                           'enabled': True}}
        self.api.post(_get_path('flavors', fmt=self.fmt),
                      self.serialize(data),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_create_flavor_too_long_description(self):
        data = {'flavor': {'name': _long_name,
                           'service_type': constants.FLAVORS,
                           'description': _long_description,
                           'enabled': True}}
        self.api.post(_get_path('flavors', fmt=self.fmt),
                      self.serialize(data),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_create_flavor_invalid_enabled(self):
        data = {'flavor': {'name': _long_name,
                           'service_type': constants.FLAVORS,
                           'description': 'the best flavor',
                           'enabled': 'BROKEN'}}
        self.api.post(_get_path('flavors', fmt=self.fmt),
                      self.serialize(data),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_update_flavor(self):
        flavor_id = 'fake_id'
        data = {'flavor': {'name': 'GOLD',
                           'description': 'the best flavor',
                           'enabled': True}}
        expected = copy.copy(data)
        expected['flavor']['service_profiles'] = []

        instance = self.plugin.return_value
        instance.update_flavor.return_value = expected['flavor']
        res = self.api.put(_get_path('flavors', id=flavor_id, fmt=self.fmt),
                           self.serialize(data),
                           content_type='application/%s' % self.fmt)

        instance.update_flavor.assert_called_with(mock.ANY,
                                                  flavor_id,
                                                  flavor=expected)
        res = self.deserialize(res)
        self.assertIn('flavor', res)
        self.assertEqual(expected, res)

    def test_update_flavor_too_long_name(self):
        flavor_id = 'fake_id'
        data = {'flavor': {'name': _long_name,
                           'description': 'the best flavor',
                           'enabled': True}}
        self.api.put(_get_path('flavors', id=flavor_id, fmt=self.fmt),
                     self.serialize(data),
                     content_type='application/%s' % self.fmt,
                     status=exc.HTTPBadRequest.code)

    def test_update_flavor_too_long_description(self):
        flavor_id = 'fake_id'
        data = {'flavor': {'name': 'GOLD',
                           'description': _long_description,
                           'enabled': True}}
        self.api.put(_get_path('flavors', id=flavor_id, fmt=self.fmt),
                     self.serialize(data),
                     content_type='application/%s' % self.fmt,
                     status=exc.HTTPBadRequest.code)

    def test_update_flavor_invalid_enabled(self):
        flavor_id = 'fake_id'
        data = {'flavor': {'name': 'GOLD',
                           'description': _long_description,
                           'enabled': 'BROKEN'}}
        self.api.put(_get_path('flavors', id=flavor_id, fmt=self.fmt),
                     self.serialize(data),
                     content_type='application/%s' % self.fmt,
                     status=exc.HTTPBadRequest.code)

    def test_delete_flavor(self):
        flavor_id = 'fake_id'
        instance = self.plugin.return_value
        self.api.delete(_get_path('flavors', id=flavor_id, fmt=self.fmt),
                        content_type='application/%s' % self.fmt)

        instance.delete_flavor.assert_called_with(mock.ANY,
                                                  flavor_id)

    def test_show_flavor(self):
        flavor_id = 'fake_id'
        expected = {'flavor': {'id': flavor_id,
                               'name': 'GOLD',
                               'description': 'the best flavor',
                               'enabled': True,
                               'service_profiles': ['profile-1']}}
        instance = self.plugin.return_value
        instance.get_flavor.return_value = expected['flavor']
        res = self.api.get(
            _get_path('flavors', id=flavor_id, fmt=self.fmt),
            extra_environ=test_base._get_neutron_env(as_admin=True))
        instance.get_flavor.assert_called_with(mock.ANY,
                                               flavor_id,
                                               fields=mock.ANY)
        res = self.deserialize(res)
        self.assertEqual(expected, res)

    def test_get_flavors(self):
        data = {'flavors': [{'id': 'id1',
                             'name': 'GOLD',
                             'description': 'the best flavor',
                             'enabled': True,
                             'service_profiles': ['profile-1']},
                            {'id': 'id2',
                             'name': 'GOLD',
                             'description': 'the best flavor',
                             'enabled': True,
                             'service_profiles': ['profile-2', 'profile-1']}]}
        instance = self.plugin.return_value
        instance.get_flavors.return_value = data['flavors']
        res = self.api.get(
            _get_path('flavors', fmt=self.fmt),
            extra_environ=test_base._get_neutron_env(as_admin=True))
        instance.get_flavors.assert_called_with(mock.ANY,
                                                fields=mock.ANY,
                                                filters=mock.ANY)
        res = self.deserialize(res)
        self.assertEqual(data, res)

    def test_create_service_profile(self):
        expected = {'service_profile': {'description': 'the best sp',
                                        'driver': '',
                                        'enabled': True,
                                        'metainfo': '{"data": "value"}'}}

        instance = self.plugin.return_value
        instance.create_service_profile.return_value = (
            expected['service_profile'])
        res = self.api.post(_get_path('service_profiles', fmt=self.fmt),
                            self.serialize(expected),
                            content_type='application/%s' % self.fmt,
                            extra_environ=self.env)
        # NOTE(slaweq): we need to do such complicated assertion as in the
        # arguments of the tested method may or may not be 'tenant_id' and
        # 'project_id' included. It is not really needed but in the neutron-lib
        # versions <= 3.13 is is included and should be gone once bug
        # https://bugs.launchpad.net/neutron/+bug/2022043/ will be fixed
        actual_service_profile_arg = (
            instance.create_service_profile.call_args.kwargs[
                'service_profile'])
        actual_service_profile_arg['service_profile'].pop('project_id', None)
        actual_service_profile_arg['service_profile'].pop('tenant_id', None)
        self.assertDictEqual(expected,
                             actual_service_profile_arg)
        res = self.deserialize(res)
        self.assertIn('service_profile', res)
        self.assertEqual(expected, res)

    def test_create_service_profile_too_long_description(self):
        expected = {'service_profile': {'description': _long_description,
                                        'driver': '',
                                        'enabled': True,
                                        'metainfo': '{"data": "value"}'}}
        self.api.post(_get_path('service_profiles', fmt=self.fmt),
                      self.serialize(expected),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_create_service_profile_too_long_driver(self):
        expected = {'service_profile': {'description': 'the best sp',
                                        'driver': _long_description,
                                        'enabled': True,
                                        'metainfo': '{"data": "value"}'}}
        self.api.post(_get_path('service_profiles', fmt=self.fmt),
                      self.serialize(expected),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_create_service_profile_invalid_enabled(self):
        expected = {'service_profile': {'description': 'the best sp',
                                        'driver': '',
                                        'enabled': 'BROKEN',
                                        'metainfo': '{"data": "value"}'}}
        self.api.post(_get_path('service_profiles', fmt=self.fmt),
                      self.serialize(expected),
                      content_type='application/%s' % self.fmt,
                      status=exc.HTTPBadRequest.code)

    def test_update_service_profile(self):
        sp_id = "fake_id"
        expected = {'service_profile': {'description': 'the best sp',
                                        'enabled': False,
                                        'metainfo': '{"data1": "value3"}'}}

        instance = self.plugin.return_value
        instance.update_service_profile.return_value = (
            expected['service_profile'])
        res = self.api.put(_get_path('service_profiles',
                                     id=sp_id, fmt=self.fmt),
                           self.serialize(expected),
                           content_type='application/%s' % self.fmt)

        instance.update_service_profile.assert_called_with(
            mock.ANY,
            sp_id,
            service_profile=expected)
        res = self.deserialize(res)
        self.assertIn('service_profile', res)
        self.assertEqual(expected, res)

    def test_update_service_profile_too_long_description(self):
        sp_id = "fake_id"
        expected = {'service_profile': {'description': 'the best sp',
                                        'enabled': 'BROKEN',
                                        'metainfo': '{"data1": "value3"}'}}
        self.api.put(_get_path('service_profiles',
                               id=sp_id, fmt=self.fmt),
                     self.serialize(expected),
                     content_type='application/%s' % self.fmt,
                     status=exc.HTTPBadRequest.code)

    def test_update_service_profile_invalid_enabled(self):
        sp_id = "fake_id"
        expected = {'service_profile': {'description': 'the best sp',
                                        'enabled': 'BROKEN',
                                        'metainfo': '{"data1": "value3"}'}}
        self.api.put(_get_path('service_profiles',
                               id=sp_id, fmt=self.fmt),
                     self.serialize(expected),
                     content_type='application/%s' % self.fmt,
                     status=exc.HTTPBadRequest.code)

    def test_delete_service_profile(self):
        sp_id = 'fake_id'
        instance = self.plugin.return_value
        self.api.delete(_get_path('service_profiles', id=sp_id, fmt=self.fmt),
                        content_type='application/%s' % self.fmt)
        instance.delete_service_profile.assert_called_with(mock.ANY,
                                                           sp_id)

    def test_show_service_profile(self):
        sp_id = 'fake_id'
        expected = {'service_profile': {'id': 'id1',
                                        'driver': _driver,
                                        'description': 'desc',
                                        'metainfo': '{}',
                                        'enabled': True}}
        instance = self.plugin.return_value
        instance.get_service_profile.return_value = (
            expected['service_profile'])
        res = self.api.get(_get_path('service_profiles',
                                     id=sp_id, fmt=self.fmt))
        instance.get_service_profile.assert_called_with(mock.ANY,
                                                        sp_id,
                                                        fields=mock.ANY)
        res = self.deserialize(res)
        self.assertEqual(expected, res)

    def test_get_service_profiles(self):
        expected = {'service_profiles': [{'id': 'id1',
                                          'driver': _driver,
                                          'description': 'desc',
                                          'metainfo': '{}',
                                          'enabled': True},
                                         {'id': 'id2',
                                          'driver': _driver,
                                          'description': 'desc',
                                          'metainfo': '{}',
                                          'enabled': True}]}
        instance = self.plugin.return_value
        instance.get_service_profiles.return_value = (
            expected['service_profiles'])
        res = self.api.get(_get_path('service_profiles', fmt=self.fmt))
        instance.get_service_profiles.assert_called_with(mock.ANY,
                                                         fields=mock.ANY,
                                                         filters=mock.ANY)
        res = self.deserialize(res)
        self.assertEqual(expected, res)

    def test_associate_service_profile_with_flavor(self):
        expected = {'service_profile': {'id': _uuid()}}
        instance = self.plugin.return_value
        instance.create_flavor_service_profile.return_value = (
            expected['service_profile'])
        res = self.api.post('/flavors/fl_id/service_profiles',
                            self.serialize(expected),
                            content_type='application/%s' % self.fmt,
                            extra_environ=self.env)
        # NOTE(slaweq): we need to do such complicated assertion as in the
        # arguments of the tested method may or may not be 'tenant_id' and
        # 'project_id' included. It is not really needed but in the neutron-lib
        # versions <= 3.13 is is included and should be gone once bug
        # https://bugs.launchpad.net/neutron/+bug/2022043/ will be fixed
        actual_flavor_id_arg = (
            instance.create_flavor_service_profile.call_args.kwargs[
                'flavor_id'])
        self.assertEqual('fl_id', actual_flavor_id_arg)
        actual_service_profile_arg = (
            instance.create_flavor_service_profile.call_args.kwargs[
                'service_profile'])
        actual_service_profile_arg['service_profile'].pop('project_id', None)
        actual_service_profile_arg['service_profile'].pop('tenant_id', None)
        self.assertDictEqual(expected,
                             actual_service_profile_arg)
        res = self.deserialize(res)
        self.assertEqual(expected, res)

    def test_disassociate_service_profile_with_flavor(self):
        instance = self.plugin.return_value
        instance.delete_flavor_service_profile.return_value = None
        self.api.delete('/flavors/fl_id/service_profiles/%s' % 'fake_spid',
                        content_type='application/%s' % self.fmt)
        instance.delete_flavor_service_profile.assert_called_with(
            mock.ANY,
            'fake_spid',
            flavor_id='fl_id')

    def test_update_association_error(self):
        """Confirm that update is not permitted with user error."""
        new_id = uuidutils.generate_uuid()
        data = {'service_profile': {'id': new_id}}
        self.api.put('/flavors/fl_id/service_profiles/%s' % 'fake_spid',
                     self.serialize(data),
                     content_type='application/%s' % self.fmt,
                     status=exc.HTTPBadRequest.code)


class DummyServicePlugin:

    def driver_loaded(self, driver, service_profile):
        pass

    @classmethod
    def get_plugin_type(cls):
        return dummy_plugin.DUMMY_SERVICE_TYPE

    def get_plugin_description(self):
        return "Dummy service plugin, aware of flavors"


class DummyServiceDriver:

    @staticmethod
    def get_service_type():
        return dummy_plugin.DUMMY_SERVICE_TYPE

    def __init__(self, plugin):
        pass


class FlavorPluginTestCase(test_db_base_plugin_v2.NeutronDbPluginV2TestCase,
                           base.PluginFixture):
    def setUp(self):
        super().setUp()

        self.config_parse()
        cfg.CONF.set_override(
            'service_plugins',
            ['neutron.tests.unit.extensions.test_flavors.DummyServicePlugin'])

        self.useFixture(
            fixtures.MonkeyPatch('neutron.manager.NeutronManager._instance'))

        self.plugin = flavors_plugin.FlavorsPlugin()
        self.ctx = context.get_admin_context()

        providers = [DummyServiceDriver.get_service_type() +
                     ":" + _provider + ":" + _driver]
        self.service_manager = servicetype_db.ServiceTypeManager.get_instance()
        self.service_providers = mock.patch.object(
            provconf.NeutronModule, 'service_providers').start()
        self.service_providers.return_value = providers
        for provider in providers:
            self.service_manager.add_provider_configuration(
                provider.split(':', maxsplit=1)[0],
                provconf.ProviderConfiguration())

        db_api.CONTEXT_WRITER.get_engine()

    def _create_flavor(self, description=None):
        flavor = {'flavor': {'name': 'GOLD',
                             'service_type': dummy_plugin.DUMMY_SERVICE_TYPE,
                             'description': description or 'the best flavor',
                             'enabled': True}}
        return self.plugin.create_flavor(self.ctx, flavor), flavor

    def test_create_flavor(self):
        self._create_flavor()
        res = flavor_obj.Flavor.get_objects(self.ctx)
        self.assertEqual(1, len(res))
        self.assertEqual('GOLD', res[0]['name'])
        self.assertEqual(
            dummy_plugin.DUMMY_SERVICE_TYPE, res[0]['service_type'])

    def test_update_flavor(self):
        fl, flavor = self._create_flavor()
        flavor = {'flavor': {'name': 'Silver',
                             'enabled': False}}
        self.plugin.update_flavor(self.ctx, fl['id'], flavor)

        # don't reuse cached models from previous plugin call
        self.ctx.session.expire_all()

        res = flavor_obj.Flavor.get_object(self.ctx, id=fl['id'])
        self.assertEqual('Silver', res['name'])
        self.assertFalse(res['enabled'])

    def test_delete_flavor(self):
        fl, _ = self._create_flavor()
        self.plugin.delete_flavor(self.ctx, fl['id'])
        self.assertFalse(flavor_obj.Flavor.objects_exist(self.ctx))

    def test_show_flavor(self):
        fl, _ = self._create_flavor()
        show_fl = self.plugin.get_flavor(self.ctx, fl['id'])
        self.assertEqual(fl, show_fl)

    def test_get_flavors(self):
        fl, flavor = self._create_flavor()
        flavor['flavor']['name'] = 'SILVER'
        self.plugin.create_flavor(self.ctx, flavor)
        show_fl = self.plugin.get_flavors(self.ctx)
        self.assertEqual(2, len(show_fl))

    def _create_service_profile(self, description=None):
        data = {'service_profile':
                {'description': description or 'the best sp',
                 'driver': _driver,
                 'enabled': True,
                 'metainfo': '{"data": "value"}'}}
        sp = self.plugin.create_service_profile(self.ctx,
                                                data)
        return sp, data

    def test_create_service_profile(self):
        sp, data = self._create_service_profile()
        res = flavor_obj.ServiceProfile.get_object(self.ctx, id=sp['id'])
        self.assertIsNotNone(res)
        self.assertEqual(data['service_profile']['driver'], res.driver)
        self.assertEqual(data['service_profile']['metainfo'], res.metainfo)

    def test_create_service_profile_empty_driver(self):
        data = {'service_profile':
                {'description': 'the best sp',
                 'driver': '',
                 'enabled': True,
                 'metainfo': '{"data": "value"}'}}
        sp = self.plugin.create_service_profile(self.ctx,
                                                data)
        res = flavor_obj.ServiceProfile.get_object(self.ctx, id=sp['id'])
        self.assertIsNotNone(res)
        self.assertEqual(data['service_profile']['driver'], res.driver)
        self.assertEqual(data['service_profile']['metainfo'], res.metainfo)

    def test_create_service_profile_invalid_driver(self):
        data = {'service_profile':
                {'description': 'the best sp',
                 'driver': "Broken",
                 'enabled': True,
                 'metainfo': '{"data": "value"}'}}
        self.assertRaises(flav_exc.ServiceProfileDriverNotFound,
                          self.plugin.create_service_profile,
                          self.ctx,
                          data)

    def test_create_service_profile_invalid_empty(self):
        data = {'service_profile':
                {'description': '',
                 'driver': '',
                 'enabled': True,
                 'metainfo': ''}}
        self.assertRaises(flav_exc.ServiceProfileEmpty,
                          self.plugin.create_service_profile,
                          self.ctx,
                          data)

    def test_update_service_profile(self):
        sp, data = self._create_service_profile()
        data['service_profile']['metainfo'] = '{"data": "value1"}'
        sp = self.plugin.update_service_profile(self.ctx, sp['id'],
                                                data)

        # don't reuse cached models from previous plugin call
        self.ctx.session.expire_all()

        res = flavor_obj.ServiceProfile.get_object(self.ctx, id=sp['id'])
        self.assertEqual(data['service_profile']['metainfo'], res['metainfo'])

    def test_delete_service_profile(self):
        sp, data = self._create_service_profile()
        self.plugin.delete_service_profile(self.ctx, sp['id'])
        res = flavor_obj.ServiceProfile.get_objects(self.ctx)
        self.assertFalse(res)

    def test_show_service_profile(self):
        sp, data = self._create_service_profile()
        sp_show = self.plugin.get_service_profile(self.ctx, sp['id'])
        self.assertEqual(sp, sp_show)

    def test_get_service_profiles(self):
        self._create_service_profile()
        self._create_service_profile(description='another sp')
        self.assertEqual(2, len(self.plugin.get_service_profiles(self.ctx)))

    def test_associate_service_profile_with_flavor(self):
        sp, data = self._create_service_profile()
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        binding = flavor_obj.FlavorServiceProfileBinding.get_objects(
            self.ctx)[0]
        self.assertEqual(fl['id'], binding['flavor_id'])
        self.assertEqual(sp['id'], binding['service_profile_id'])

        # don't reuse cached models from previous plugin call
        self.ctx.session.expire_all()

        res = self.plugin.get_flavor(self.ctx, fl['id'])
        self.assertEqual(1, len(res['service_profiles']))
        self.assertEqual(sp['id'], res['service_profiles'][0])

        res = self.plugin.get_service_profile(self.ctx, sp['id'])
        self.assertEqual(1, len(res['flavors']))
        self.assertEqual(fl['id'], res['flavors'][0])

    def test_autodelete_flavor_associations(self):
        sp, data = self._create_service_profile()
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        self.plugin.delete_flavor(self.ctx, fl['id'])
        self.assertFalse(
            flavor_obj.FlavorServiceProfileBinding.objects_exist(self.ctx))

    def test_associate_service_profile_with_flavor_exists(self):
        sp, data = self._create_service_profile()
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        self.assertRaises(flav_exc.FlavorServiceProfileBindingExists,
                          self.plugin.create_flavor_service_profile,
                          self.ctx,
                          {'service_profile': {'id': sp['id']}},
                          fl['id'])

    def test_disassociate_service_profile_with_flavor(self):
        sp, data = self._create_service_profile()
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        self.plugin.delete_flavor_service_profile(
            self.ctx, sp['id'], fl['id'])

        self.assertFalse(
            flavor_obj.FlavorServiceProfileBinding.objects_exist(self.ctx))

        self.assertRaises(
            flav_exc.FlavorServiceProfileBindingNotFound,
            self.plugin.delete_flavor_service_profile,
            self.ctx, sp['id'], fl['id'])

    def test_delete_service_profile_in_use(self):
        sp, data = self._create_service_profile()
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        self.assertRaises(
            flav_exc.ServiceProfileInUse,
            self.plugin.delete_service_profile,
            self.ctx,
            sp['id'])

    def test_delete_flavor_in_use(self):
        # make use of router since it has a flavor id
        fl, data = self._create_flavor()
        with db_api.CONTEXT_WRITER.using(self.ctx):
            self.ctx.session.add(l3_models.Router(flavor_id=fl['id']))
        self.assertRaises(
            flav_exc.FlavorInUse,
            self.plugin.delete_flavor,
            self.ctx,
            fl['id'])

    def test_get_flavor_next_provider_no_binding(self):
        fl, data = self._create_flavor()
        self.assertRaises(
            flav_exc.FlavorServiceProfileBindingNotFound,
            self.plugin.get_flavor_next_provider,
            self.ctx,
            fl['id'])

    def test_get_flavor_next_provider_disabled(self):
        data = {'service_profile':
                {'description': 'the best sp',
                 'driver': _driver,
                 'enabled': False,
                 'metainfo': '{"data": "value"}'}}
        sp = self.plugin.create_service_profile(self.ctx,
                                                data)
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        self.assertRaises(
            flav_exc.ServiceProfileDisabled,
            self.plugin.get_flavor_next_provider,
            self.ctx,
            fl['id'])

    def test_get_flavor_next_provider_no_driver(self):
        data = {'service_profile':
                {'description': 'the best sp',
                 'driver': '',
                 'enabled': True,
                 'metainfo': '{"data": "value"}'}}
        sp = self.plugin.create_service_profile(self.ctx,
                                                data)
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        self.assertRaises(
            flav_exc.ServiceProfileDriverNotFound,
            self.plugin.get_flavor_next_provider,
            self.ctx,
            fl['id'])

    def test_get_flavor_next_provider(self):
        sp, data = self._create_service_profile()
        fl, data = self._create_flavor()
        self.plugin.create_flavor_service_profile(
            self.ctx,
            {'service_profile': {'id': sp['id']}},
            fl['id'])
        providers = self.plugin.get_flavor_next_provider(
            self.ctx,
            fl['id'])
        self.assertEqual(_provider, providers[0].get('provider', None))
