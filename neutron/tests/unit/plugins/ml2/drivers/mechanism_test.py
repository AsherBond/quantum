# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
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

import uuid

from neutron_lib.api.definitions import portbindings
from neutron_lib.api.definitions import provider_net as pnet
from neutron_lib import constants as const
from neutron_lib.plugins.ml2 import api

from neutron.plugins.ml2.drivers import mech_agent


VIF_TYPE_TEST = 'vif_type_test'


class TestMechanismDriver(api.MechanismDriver):
    """Test mechanism driver for testing mechanism driver api."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._supported_vnic_types = ('test_mechanism_driver_vnic_type', )
        self._supported_extensions = set()

    def initialize(self):
        self.bound_ports = set()

    def _check_network_context(self, context, original_expected):
        assert(isinstance(context, api.NetworkContext))
        assert(isinstance(context.current, dict))
        assert(context.current['id'] is not None)
        if original_expected:
            assert(isinstance(context.original, dict))
            assert(context.current['id'] == context.original['id'])
        else:
            assert(not context.original)

    def create_network_precommit(self, context):
        self._check_network_context(context, False)

    def create_network_postcommit(self, context):
        self._check_network_context(context, False)

    def update_network_precommit(self, context):
        self._check_network_context(context, True)

    def update_network_postcommit(self, context):
        self._check_network_context(context, True)

    def delete_network_precommit(self, context):
        self._check_network_context(context, False)

    def delete_network_postcommit(self, context):
        self._check_network_context(context, False)

    def _check_subnet_context(self, context, original_expected):
        assert(isinstance(context, api.SubnetContext))
        assert(isinstance(context.current, dict))
        assert(context.current['id'] is not None)
        if original_expected:
            assert(isinstance(context.original, dict))
            assert(context.current['id'] == context.original['id'])
        else:
            assert(not context.original)
        network_context = context.network
        assert(isinstance(network_context, api.NetworkContext))
        self._check_network_context(network_context, False)

    def create_subnet_precommit(self, context):
        self._check_subnet_context(context, False)

    def create_subnet_postcommit(self, context):
        self._check_subnet_context(context, False)

    def update_subnet_precommit(self, context):
        self._check_subnet_context(context, True)

    def update_subnet_postcommit(self, context):
        self._check_subnet_context(context, True)

    def delete_subnet_precommit(self, context):
        self._check_subnet_context(context, False)

    def delete_subnet_postcommit(self, context):
        self._check_subnet_context(context, False)

    def _check_port_context(self, context, original_expected):
        assert(isinstance(context, api.PortContext))

        self._check_port_info(context.current, context.host,
                              context.vif_type, context.vif_details,
                              context.binding_levels)

        if context.vif_type in (portbindings.VIF_TYPE_UNBOUND,
                                portbindings.VIF_TYPE_BINDING_FAILED):
            if (context.segments_to_bind and
                    context.segments_to_bind[0][api.NETWORK_TYPE] == 'vlan'):
                # Partially bound.
                self._check_bound(context.binding_levels,
                                  context.top_bound_segment,
                                  context.bottom_bound_segment)
            else:
                self._check_unbound(context.binding_levels,
                                    context.top_bound_segment,
                                    context.bottom_bound_segment)
            assert((context.current['id'], context.host)
                   not in self.bound_ports)
        else:
            self._check_bound(context.binding_levels,
                              context.top_bound_segment,
                              context.bottom_bound_segment)
            assert((context.current['id'], context.host) in self.bound_ports)

        if original_expected:
            self._check_port_info(context.original, context.original_host,
                                  context.original_vif_type,
                                  context.original_vif_details,
                                  context.binding_levels)

            assert(context.current['id'] == context.original['id'])

            if (context.original_vif_type in
                (portbindings.VIF_TYPE_UNBOUND,
                 portbindings.VIF_TYPE_BINDING_FAILED)):
                self._check_unbound(context.original_binding_levels,
                                    context.original_top_bound_segment,
                                    context.original_bottom_bound_segment)
            else:
                self._check_bound(context.original_binding_levels,
                                  context.original_top_bound_segment,
                                  context.original_bottom_bound_segment)
        else:
            assert(context.original is None)
            assert(context.original_host is None)
            assert(context.original_vif_type is None)
            assert(context.original_vif_details is None)
            assert(context.original_status is None)
            self._check_unbound(context.original_binding_levels,
                                context.original_top_bound_segment,
                                context.original_bottom_bound_segment)

        network_context = context.network
        assert(isinstance(network_context, api.NetworkContext))
        self._check_network_context(network_context, False)

    def _check_port_info(self, port, host, vif_type, vif_details,
                         binding_levels):
        assert(isinstance(port, dict))
        assert(port['id'] is not None)
        assert(vif_type in (portbindings.VIF_TYPE_UNBOUND,
                            portbindings.VIF_TYPE_BINDING_FAILED,
                            portbindings.VIF_TYPE_DISTRIBUTED,
                            portbindings.VIF_TYPE_OVS,
                            portbindings.VIF_TYPE_BRIDGE))
        bound_drivers = port[portbindings.VIF_DETAILS].pop(
            portbindings.VIF_DETAILS_BOUND_DRIVERS, None)
        if port['device_owner'] == const.DEVICE_OWNER_DVR_INTERFACE:
            assert(port[portbindings.HOST_ID] == '')
            assert(port[portbindings.VIF_TYPE] ==
                   portbindings.VIF_TYPE_DISTRIBUTED)
            assert(port[portbindings.VIF_DETAILS] == {})
        else:
            assert(port[portbindings.HOST_ID] == host)
            assert(port[portbindings.VIF_TYPE] !=
                   portbindings.VIF_TYPE_DISTRIBUTED)
            assert(port[portbindings.VIF_TYPE] == vif_type)
            assert(isinstance(vif_details, dict))

            assert(port[portbindings.VIF_DETAILS] == vif_details)
        if bound_drivers and binding_levels:
            bd_reference = {str(idx): bl['bound_driver'] for
                            idx, bl in enumerate(binding_levels)}
            assert(bd_reference == bound_drivers)

    def _check_unbound(self, levels, top_segment, bottom_segment):
        assert(levels is None)
        assert(top_segment is None)
        assert(bottom_segment is None)

    def _check_bound(self, levels, top_segment, bottom_segment):
        assert(isinstance(levels, list))
        top_level = levels[0]
        assert(isinstance(top_level, dict))
        assert(isinstance(top_segment, dict))
        assert(top_segment == top_level[api.BOUND_SEGMENT])
        assert('test' == top_level[api.BOUND_DRIVER])
        bottom_level = levels[-1]
        assert(isinstance(bottom_level, dict))
        assert(isinstance(bottom_segment, dict))
        assert(bottom_segment == bottom_level[api.BOUND_SEGMENT])
        assert('test' == bottom_level[api.BOUND_DRIVER])

    def create_port_precommit(self, context):
        self._check_port_context(context, False)

    def create_port_postcommit(self, context):
        self._check_port_context(context, False)

    def update_port_precommit(self, context):
        if ((context.original_top_bound_segment and
             not context.top_bound_segment) or
                (context.host == "host-fail")):
            self.bound_ports.remove((context.original['id'],
                                     context.original_host))
        self._check_port_context(context, True)

    def update_port_postcommit(self, context):
        self._check_port_context(context, True)

    def delete_port_precommit(self, context):
        self._check_port_context(context, False)

    def delete_port_postcommit(self, context):
        self._check_port_context(context, False)

    def bind_port(self, context):
        self._check_port_context(context, False)

        host = context.host
        segment = context.segments_to_bind[0]
        segment_id = segment[api.ID]
        if host == "host-ovs-no_filter":
            context.set_binding(segment_id, portbindings.VIF_TYPE_OVS,
                                {portbindings.CAP_PORT_FILTER: False})
            self.bound_ports.add((context.current['id'], host))
        elif host == "host-bridge-filter":
            context.set_binding(segment_id, portbindings.VIF_TYPE_BRIDGE,
                                {portbindings.CAP_PORT_FILTER: True})
            self.bound_ports.add((context.current['id'], host))
        elif host == "host-ovs-filter-active":
            context.set_binding(segment_id, portbindings.VIF_TYPE_OVS,
                                {portbindings.CAP_PORT_FILTER: True},
                                status=const.PORT_STATUS_ACTIVE)
            self.bound_ports.add((context.current['id'], host))
        elif host == "host-hierarchical":
            segment_type = segment[api.NETWORK_TYPE]
            if segment_type == 'local':
                next_segment = context.allocate_dynamic_segment(
                    {api.NETWORK_TYPE: 'vlan',
                     api.PHYSICAL_NETWORK: 'physnet1'}
                )
                context.continue_binding(segment_id, [next_segment])
            elif segment_type == 'vlan':
                context.set_binding(segment_id,
                                    portbindings.VIF_TYPE_OVS,
                                    {portbindings.CAP_PORT_FILTER: False})
                self.bound_ports.add((context.current['id'], host))
        elif host == "host-fail":
            context.set_binding(None,
                                portbindings.VIF_TYPE_BINDING_FAILED,
                                {portbindings.CAP_PORT_FILTER: False})
            self.bound_ports.add((context.current['id'], host))

    def filter_hosts_with_segment_access(
            self, context, segments, candidate_hosts, agent_getter):
        return set()

    @property
    def resource_provider_uuid5_namespace(self):
        return uuid.UUID('7f0ce65c-1f13-11e9-8921-3c6aa7b21d17')

    @property
    def supported_vnic_types(self):
        return self._supported_vnic_types

    def get_standard_device_mappings(self, agent):
        return {}

    def supported_extensions(self, extensions):
        if self._supported_extensions:
            return extensions & self._supported_extensions
        return extensions


class TestMechanismDriverWithAgent(mech_agent.AgentMechanismDriverBase,
                                   TestMechanismDriver):
    """Test mechanism driver with agent for testing mechanism driver api."""

    def __init__(self):
        super().__init__(
            'test_agent_type', [portbindings.VNIC_NORMAL])
        self.bound_ports = set()
        self._agent_type = 'test_mechanism_driver_agent'

    def get_supported_vif_type(self, agent):
        return VIF_TYPE_TEST

    def get_vif_type(self, context, agent, segment):
        return VIF_TYPE_TEST

    @staticmethod
    def provider_network_attribute_updates_supported():
        return [pnet.SEGMENTATION_ID]

    def try_to_bind_segment_for_agent(self, context, segment, agent):
        pass

    @property
    def agent_type(self):
        return self._agent_type

    @agent_type.setter
    def agent_type(self, agent_type):
        self._agent_type = agent_type

    @TestMechanismDriver.supported_vnic_types.setter
    def supported_vnic_types(self, vnic_types):
        self._supported_vnic_types = vnic_types
