# Copyright 2015 Red Hat, Inc.
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

import datetime
import math
import os
import random
import signal

from neutron_lib.agent import topics
from neutron_lib import constants
from neutron_lib import context
from oslo_utils import timeutils

import neutron
from neutron.db import agents_db

HOST = 'localhost'
DEFAULT_AZ = 'nova'


def find_file(filename, path):
    """Find a file with name 'filename' located in 'path'."""
    for root, _, files in os.walk(path):
        if filename in files:
            return os.path.abspath(os.path.join(root, filename))


def find_sample_file(filename):
    """Find a file with name 'filename' located in the sample directory."""
    return find_file(
        filename,
        path=os.path.join(neutron.__path__[0], '..', 'etc'))


def get_test_log_path():
    return os.environ.get('OS_LOG_PATH', '/tmp')


class FakePlugin(agents_db.AgentDbMixin):
    pass


def _get_l3_agent_dict(host, agent_mode, internal_only=True,
                       az=DEFAULT_AZ):
    return {
        'agent_type': constants.AGENT_TYPE_L3,
        'binary': constants.AGENT_PROCESS_L3,
        'host': host,
        'topic': topics.L3_AGENT,
        'availability_zone': az,
        'configurations': {'agent_mode': agent_mode,
                           'handle_internal_only_routers': internal_only}}


def _register_agent(agent, plugin=None):
    if not plugin:
        plugin = FakePlugin()
    admin_context = context.get_admin_context()
    plugin.create_or_update_agent(admin_context, agent, timeutils.utcnow())
    return plugin._get_agent_by_type_and_host(
        admin_context, agent['agent_type'], agent['host'])


def register_l3_agent(host=HOST, agent_mode=constants.L3_AGENT_MODE_LEGACY,
                      internal_only=True, az=DEFAULT_AZ):
    agent = _get_l3_agent_dict(host, agent_mode, internal_only, az)
    return _register_agent(agent)


def _get_dhcp_agent_dict(host, networks=0, az=DEFAULT_AZ):
    agent = {
        'binary': constants.AGENT_PROCESS_DHCP,
        'host': host,
        'topic': topics.DHCP_AGENT,
        'agent_type': constants.AGENT_TYPE_DHCP,
        'availability_zone': az,
        'configurations': {'dhcp_driver': 'dhcp_driver',
                           'networks': networks}}
    return agent


def register_dhcp_agent(host=HOST, networks=0, admin_state_up=True,
                        alive=True, az=DEFAULT_AZ):
    agent = _register_agent(
        _get_dhcp_agent_dict(host, networks, az=az))

    if not admin_state_up:
        set_agent_admin_state(agent['id'])
    if not alive:
        kill_agent(agent['id'])

    return FakePlugin()._get_agent_by_type_and_host(
        context.get_admin_context(), agent['agent_type'], agent['host'])


def kill_agent(agent_id):
    hour_ago = timeutils.utcnow() - datetime.timedelta(hours=1)
    FakePlugin().update_agent(
        context.get_admin_context(),
        agent_id,
        {'agent': {
            'started_at': hour_ago,
            'heartbeat_timestamp': hour_ago}})


def revive_agent(agent_id):
    now = timeutils.utcnow()
    FakePlugin().update_agent(
        context.get_admin_context(), agent_id,
        {'agent': {'started_at': now, 'heartbeat_timestamp': now}})


def set_agent_admin_state(agent_id, admin_state_up=False):
    FakePlugin().update_agent(
        context.get_admin_context(),
        agent_id,
        {'agent': {'admin_state_up': admin_state_up}})


def _get_l2_agent_dict(host, agent_type, binary, tunnel_types=None,
                       tunneling_ip='20.0.0.1', interface_mappings=None,
                       bridge_mappings=None, l2pop_network_types=None,
                       device_mappings=None, start_flag=True,
                       integration_bridge=None):
    agent = {
        'binary': binary,
        'host': host,
        'topic': constants.L2_AGENT_TOPIC,
        'configurations': {},
        'agent_type': agent_type,
        'tunnel_type': [],
        'start_flag': start_flag}

    if tunnel_types is not None:
        agent['configurations']['tunneling_ip'] = tunneling_ip
        agent['configurations']['tunnel_types'] = tunnel_types
    if bridge_mappings is not None:
        agent['configurations']['bridge_mappings'] = bridge_mappings
    if interface_mappings is not None:
        agent['configurations']['interface_mappings'] = interface_mappings
    if l2pop_network_types is not None:
        agent['configurations']['l2pop_network_types'] = l2pop_network_types
    if device_mappings is not None:
        agent['configurations']['device_mappings'] = device_mappings
    if integration_bridge is not None:
        agent['configurations']['integration_bridge'] = integration_bridge
    return agent


def register_ovs_agent(host=HOST, agent_type=constants.AGENT_TYPE_OVS,
                       binary=constants.AGENT_PROCESS_OVS,
                       tunnel_types=None, tunneling_ip='20.0.0.1',
                       interface_mappings=None, bridge_mappings=None,
                       l2pop_network_types=None, plugin=None, start_flag=True,
                       integration_bridge=None):
    if tunnel_types is None:
        tunnel_types = ['vxlan']
    agent = _get_l2_agent_dict(host, agent_type, binary, tunnel_types,
                               tunneling_ip, interface_mappings,
                               bridge_mappings, l2pop_network_types,
                               start_flag=start_flag,
                               integration_bridge=integration_bridge)
    return _register_agent(agent, plugin)


def register_macvtap_agent(host=HOST,
                           agent_type=constants.AGENT_TYPE_MACVTAP,
                           binary=constants.AGENT_PROCESS_MACVTAP,
                           interface_mappings=None, plugin=None):
    agent = _get_l2_agent_dict(host, agent_type, binary,
                               interface_mappings=interface_mappings)
    return _register_agent(agent, plugin)


def register_sriovnicswitch_agent(host=HOST,
                                  agent_type=constants.AGENT_TYPE_NIC_SWITCH,
                                  binary=constants.AGENT_PROCESS_NIC_SWITCH,
                                  device_mappings=None, plugin=None):
    agent = _get_l2_agent_dict(host, agent_type, binary,
                               device_mappings=device_mappings)
    return _register_agent(agent, plugin)


def get_not_used_vlan(bridge, vlan_range):
    port_vlans = bridge.ovsdb.db_find(
        'Port', ('tag', '!=', []), columns=['tag']).execute()
    used_vlan_tags = {val['tag'] for val in port_vlans}
    available_vlans = vlan_range - used_vlan_tags
    return random.choice(list(available_vlans))


class TestTimerTimeout(Exception):
    pass


class TestTimer:
    """Timer context manager class for testing.

    This class can be used inside a fixtures._fixtures.timeout.Timeout context.
    This class will halt the timeout counter and divert temporary the fixtures
    timeout exception. The goal of this class is to use the SIGALRM event
    without affecting the test case timeout counter.
    """
    def __init__(self, timeout):
        self._timeout = int(timeout)
        self._old_handler = None
        self._old_timer = None
        self._alarm_fn = getattr(signal, 'alarm', None)

    def _timeout_handler(self, *args, **kwargs):
        raise TestTimerTimeout()

    def __enter__(self):
        self._old_handler = signal.signal(signal.SIGALRM,
                                          self._timeout_handler)
        self._old_timer = math.ceil(signal.getitimer(signal.ITIMER_REAL)[0])
        if self._alarm_fn:
            self._alarm_fn(self._timeout)
        return self

    def __exit__(self, exc, value, traceback):
        if self._old_handler is not None:
            signal.signal(signal.SIGALRM, self._old_handler)

        if self._old_timer == 0:
            timeout = 0
        else:
            # If timer has expired, set the minimum required value (1) to
            # activate the SIGALRM event.
            timeout = self._old_timer - self._timeout
            timeout = 1 if timeout <= 0 else timeout

        if self._alarm_fn:
            self._alarm_fn(timeout)
