# Copyright 2013 NEC Corporation
# All rights reserved.
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

from http import client as httplib

from neutron_lib.api.definitions import portbindings
from neutron_lib import context
from neutron_lib.plugins import directory
from webob import exc

from neutron.tests.common import test_db_base_plugin_v2
from neutron.tests.unit import dummy_plugin


class PortBindingsTestCase(test_db_base_plugin_v2.NeutronDbPluginV2TestCase):

    # VIF_TYPE must be overridden according to plugin vif_type
    VIF_TYPE = portbindings.VIF_TYPE_OTHER
    # VIF_DETAILS must be overridden according to plugin vif_details
    VIF_DETAILS = None

    def _check_response_portbindings(self, port):
        self.assertEqual(port[portbindings.VIF_TYPE], self.VIF_TYPE)
        # REVISIT(rkukura): Consider reworking tests to enable ML2 to bind

        if self.VIF_TYPE not in [portbindings.VIF_TYPE_UNBOUND,
                                 portbindings.VIF_TYPE_BINDING_FAILED]:
            # NOTE(r-mibu): The following six lines are just for backward
            # compatibility.  In this class, HAS_PORT_FILTER has been replaced
            # by VIF_DETAILS which can be set expected vif_details to check,
            # but all replacement of HAS_PORT_FILTER in successor has not been
            # completed.
            if self.VIF_DETAILS is None:
                expected = getattr(self, 'HAS_PORT_FILTER', False)
                vif_details = port[portbindings.VIF_DETAILS]
                port_filter = vif_details[portbindings.CAP_PORT_FILTER]
                self.assertEqual(expected, port_filter)
                return
            self.assertEqual(self.VIF_DETAILS, port[portbindings.VIF_DETAILS])

    def _check_response_no_portbindings(self, port):
        self.assertIn('status', port)
        self.assertNotIn(portbindings.VIF_TYPE, port)
        self.assertNotIn(portbindings.VIF_DETAILS, port)

    def test_port_vif_details(self):
        with self.port(is_admin=True, name='name') as port:
            port_id = port['port']['id']
            # Check a response of create_port
            self._check_response_portbindings(port['port'])
            # Check a response of get_port
            port = self._show('ports', port_id, as_admin=True)['port']
            self._check_response_portbindings(port)
            # By default user is admin - now test non admin user
            non_admin_port = self._show('ports', port_id)['port']
            self._check_response_no_portbindings(non_admin_port)

    def test_ports_vif_details(self):
        plugin = directory.get_plugin()
        with self.port(), self.port():
            ctx = context.get_admin_context()
            ports = plugin.get_ports(ctx)
            self.assertEqual(len(ports), 2)
            for port in ports:
                self._check_response_portbindings(port)
            ports = self._list('ports')['ports']
            self.assertEqual(len(ports), 2)
            for non_admin_port in ports:
                self._check_response_no_portbindings(non_admin_port)

    def _check_port_binding_profile(self, port, profile=None):
        # For plugins which does not use binding:profile attr
        # we just check an operation for the port succeed.
        self.assertIn('id', port)

    def _test_create_port_binding_profile(self, profile):
        profile_arg = {portbindings.PROFILE: profile}
        with self.port(is_service=True,
                       arg_list=(portbindings.PROFILE,),
                       **profile_arg) as port:
            port_id = port['port']['id']
            self._check_port_binding_profile(port['port'], profile)
            port = self._show('ports', port_id, as_admin=True)
            self._check_port_binding_profile(port['port'], profile)

    def test_create_port_binding_profile_none(self):
        self._test_create_port_binding_profile(None)

    def test_create_port_binding_profile_with_empty_dict(self):
        self._test_create_port_binding_profile({})

    def _test_update_port_binding_profile(self, profile):
        profile_arg = {portbindings.PROFILE: profile}
        with self.port(is_admin=True) as port:
            self._check_port_binding_profile(port['port'])
            port_id = port['port']['id']
            port = self._update('ports', port_id, {'port': profile_arg},
                                as_service=True)['port']
            self._check_port_binding_profile(port, profile)
            port = self._show('ports', port_id, as_admin=True)['port']
            self._check_port_binding_profile(port, profile)

    def test_update_port_binding_profile_none(self):
        self._test_update_port_binding_profile(None)

    def test_update_port_binding_profile_with_empty_dict(self):
        self._test_update_port_binding_profile({})

    def test_port_create_portinfo_non_admin(self):
        profile_arg = {portbindings.PROFILE: {dummy_plugin.RESOURCE_NAME:
                                              dummy_plugin.RESOURCE_NAME}}
        with self.network() as net1:
            with self.subnet(network=net1) as subnet1:
                # succeed without binding:profile
                with self.port(subnet=subnet1):
                    pass
                # fail with binding:profile
                try:
                    with self.port(subnet=subnet1,
                                   expected_res_status=403,
                                   arg_list=(portbindings.PROFILE,),
                                   **profile_arg):
                        pass
                except exc.HTTPClientError:
                    pass

    def test_port_update_portinfo_non_admin(self):
        profile_arg = {portbindings.PROFILE: {dummy_plugin.RESOURCE_NAME:
                                              dummy_plugin.RESOURCE_NAME}}
        with self.network() as net1:
            with self.subnet(network=net1) as subnet1:
                with self.port(subnet=subnet1) as port:
                    # By default user is admin - now test non admin user
                    port_id = port['port']['id']
                    port = self._update('ports', port_id,
                                        {'port': profile_arg},
                                        expected_code=exc.HTTPForbidden.code)


class PortBindingsHostTestCaseMixin:
    fmt = 'json'
    hostname = 'testhost'

    def _check_response_portbindings_host(self, port):
        self.assertEqual(port[portbindings.HOST_ID], self.hostname)

    def _check_response_no_portbindings_host(self, port):
        self.assertIn('status', port)
        self.assertNotIn(portbindings.HOST_ID, port)

    def test_port_vif_non_admin(self):
        with self.network(set_context=True,
                          tenant_id='test') as net1:
            with self.subnet(network=net1) as subnet1:
                host_arg = {portbindings.HOST_ID: self.hostname}
                try:
                    with self.port(subnet=subnet1,
                                   expected_res_status=403,
                                   arg_list=(portbindings.HOST_ID,),
                                   set_context=True,
                                   tenant_id='test',
                                   **host_arg):
                        pass
                except exc.HTTPClientError:
                    pass

    def test_port_vif_host(self):
        host_arg = {portbindings.HOST_ID: self.hostname}
        with self.port(name='name', is_admin=True,
                       arg_list=(portbindings.HOST_ID,),
                       **host_arg) as port:
            port_id = port['port']['id']
            # Check a response of create_port
            self._check_response_portbindings_host(port['port'])
            # Check a response of get_port
            port = self._show('ports', port_id, as_admin=True)['port']
            self._check_response_portbindings_host(port)
            non_admin_port = self._show('ports', port_id)['port']
            self._check_response_no_portbindings_host(non_admin_port)

    def test_ports_vif_host(self):
        host_arg = {portbindings.HOST_ID: self.hostname}
        with self.port(name='name1',
                       is_admin=True,
                       arg_list=(portbindings.HOST_ID,),
                       **host_arg), self.port(name='name2'):
            ports = self._list('ports', as_admin=True)['ports']
            self.assertEqual(2, len(ports))
            for port in ports:
                if port['name'] == 'name1':
                    self._check_response_portbindings_host(port)
                else:
                    self.assertFalse(port[portbindings.HOST_ID])
            ports = self._list('ports')['ports']
            self.assertEqual(2, len(ports))
            for non_admin_port in ports:
                self._check_response_no_portbindings_host(non_admin_port)

    def test_ports_vif_host_update(self):
        host_arg = {portbindings.HOST_ID: self.hostname}
        with self.port(name='name1', is_admin=True,
                       arg_list=(portbindings.HOST_ID,),
                       **host_arg) as port1, self.port(name='name2') as port2:
            data = {'port': {portbindings.HOST_ID: 'testhosttemp'}}
            req = self.new_update_request('ports', data, port1['port']['id'],
                                          as_admin=True)
            req.get_response(self.api)
            req = self.new_update_request('ports', data, port2['port']['id'],
                                          as_admin=True)
            req.get_response(self.api)
            ports = self._list('ports', as_admin=True)['ports']
        self.assertEqual(2, len(ports))
        for port in ports:
            self.assertEqual('testhosttemp', port[portbindings.HOST_ID])

    def test_ports_vif_non_host_update(self):
        host_arg = {portbindings.HOST_ID: self.hostname}
        with self.port(name='name', is_admin=True,
                       arg_list=(portbindings.HOST_ID,),
                       **host_arg) as port:
            data = {'port': {'admin_state_up': False}}
            req = self.new_update_request('ports', data, port['port']['id'],
                                          as_admin=True)
            res = self.deserialize(self.fmt, req.get_response(self.api))
            self.assertEqual(port['port'][portbindings.HOST_ID],
                             res['port'][portbindings.HOST_ID])

    def test_ports_vif_non_host_update_when_host_null(self):
        with self.port(is_admin=True) as port:
            data = {'port': {'admin_state_up': False}}
            req = self.new_update_request('ports', data, port['port']['id'],
                                          as_admin=True)
            res = self.deserialize(self.fmt, req.get_response(self.api))
            self.assertEqual(port['port'][portbindings.HOST_ID],
                             res['port'][portbindings.HOST_ID])

    def test_ports_vif_host_list(self):
        host_arg = {portbindings.HOST_ID: self.hostname}
        with self.port(name='name1',
                       is_admin=True,
                       arg_list=(portbindings.HOST_ID,),
                       **host_arg) as port1,\
                self.port(name='name2'),\
                self.port(name='name3',
                          is_admin=True,
                          arg_list=(portbindings.HOST_ID,),
                          **host_arg) as port3:
            self._test_list_resources(
                'port', (port1, port3),
                query_params='{}={}'.format(
                    portbindings.HOST_ID, self.hostname))


class PortBindingsVnicTestCaseMixin:
    fmt = 'json'
    vnic_type = portbindings.VNIC_NORMAL

    def _check_response_portbindings_vnic_type(self, port):
        self.assertIn('status', port)
        self.assertEqual(port[portbindings.VNIC_TYPE], self.vnic_type)

    def test_port_vnic_type_non_admin(self):
        with self.network(set_context=True,
                          tenant_id='test') as net1:
            with self.subnet(network=net1) as subnet1:
                vnic_arg = {portbindings.VNIC_TYPE: self.vnic_type}
                with self.port(subnet=subnet1,
                               expected_res_status=httplib.CREATED,
                               arg_list=(portbindings.VNIC_TYPE,),
                               set_context=True,
                               tenant_id='test',
                               **vnic_arg) as port:
                    # Check a response of create_port
                    self._check_response_portbindings_vnic_type(port['port'])

    def test_port_vnic_type(self):
        vnic_arg = {portbindings.VNIC_TYPE: self.vnic_type}
        with self.port(name='name', arg_list=(portbindings.VNIC_TYPE,),
                       **vnic_arg) as port:
            port_id = port['port']['id']
            # Check a response of create_port
            self._check_response_portbindings_vnic_type(port['port'])
            # Check a response of get_port
            port = self._show('ports', port_id, as_admin=True)['port']
            self._check_response_portbindings_vnic_type(port)
            non_admin_port = self._show('ports', port_id)['port']
            self._check_response_portbindings_vnic_type(non_admin_port)

    def test_ports_vnic_type(self):
        vnic_arg = {portbindings.VNIC_TYPE: self.vnic_type}
        with self.port(name='name1', arg_list=(portbindings.VNIC_TYPE,),
                       **vnic_arg), self.port(name='name2'):
            ports = self._list('ports', as_admin=True)['ports']
            self.assertEqual(2, len(ports))
            for port in ports:
                if port['name'] == 'name1':
                    self._check_response_portbindings_vnic_type(port)
                else:
                    self.assertEqual(portbindings.VNIC_NORMAL,
                                     port[portbindings.VNIC_TYPE])
            ports = self._list('ports')['ports']
            self.assertEqual(2, len(ports))
            for non_admin_port in ports:
                self._check_response_portbindings_vnic_type(non_admin_port)
