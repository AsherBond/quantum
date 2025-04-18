# Copyright 2012 Red Hat, Inc.
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

from neutron_lib import constants as n_const
from neutron_lib.plugins.ml2 import ovs_constants
from oslo_config import cfg

from neutron._i18n import _
from neutron.conf.agent import common
from neutron.conf.agent.metadata import config as meta_conf


DEFAULT_BRIDGE_MAPPINGS = []
DEFAULT_TUNNEL_TYPES = []

ovs_opts = [
    cfg.StrOpt('integration_bridge', default='br-int',
               help=_("Integration bridge to use. "
                      "Do not change this parameter unless you have a good "
                      "reason to. This is the name of the OVS integration "
                      "bridge. There is one per hypervisor. The integration "
                      "bridge acts as a virtual 'patch bay'. All VM VIFs are "
                      "attached to this bridge and then 'patched' according "
                      "to their network connectivity.")),
    cfg.StrOpt('tunnel_bridge', default='br-tun',
               help=_("Tunnel bridge to use.")),
    cfg.StrOpt('int_peer_patch_port', default='patch-tun',
               help=_("Peer patch port in integration bridge for tunnel "
                      "bridge.")),
    cfg.StrOpt('tun_peer_patch_port', default='patch-int',
               help=_("Peer patch port in tunnel bridge for integration "
                      "bridge.")),
    cfg.IPOpt('local_ip',
              help=_("IP address of local overlay (tunnel) network endpoint. "
                     "Use either an IPv4 or IPv6 address that resides on one "
                     "of the host network interfaces. The IP version of this "
                     "value must match the value of the 'overlay_ip_version' "
                     "option in the ML2 plug-in configuration file on the "
                     "neutron server node(s).")),
    cfg.ListOpt('bridge_mappings',
                default=DEFAULT_BRIDGE_MAPPINGS,
                help=_("Comma-separated list of <physical_network>:<bridge> "
                       "tuples mapping physical network names to the agent's "
                       "node-specific Open vSwitch bridge names to be used "
                       "for flat and VLAN networks. The length of bridge "
                       "names should be no more than 11. Each bridge must "
                       "exist, and should have a physical network interface "
                       "configured as a port. All physical networks "
                       "configured on the server should have mappings to "
                       "appropriate bridges on each agent. "
                       "Note: If you remove a bridge from this "
                       "mapping, make sure to disconnect it from the "
                       "integration bridge as it won't be managed by the "
                       "agent anymore.")),
    cfg.ListOpt('resource_provider_bandwidths',
                default=[],
                help=_("Comma-separated list of "
                       "<bridge>:<egress_bw>:<ingress_bw> tuples, showing "
                       "the available bandwidth for the given bridge in the "
                       "given direction. The direction is meant from VM "
                       "perspective. Bandwidth is measured in kilobits per "
                       "second (kbps). The bridge must appear in "
                       "bridge_mappings as the value. But not all bridges in "
                       "bridge_mappings must be listed here. For a bridge not "
                       "listed here we neither create a resource provider in "
                       "placement nor report inventories against. An omitted "
                       "direction means we do not report an inventory for the "
                       "corresponding class.")),
    cfg.DictOpt('resource_provider_hypervisors',
                default={},
                help=_("Mapping of bridges to hypervisors: "
                       "<bridge>:<hypervisor>,... "
                       "hypervisor name is used to locate the parent of the "
                       "resource provider tree. Only needs to be set in the "
                       "rare case when the hypervisor name is different from "
                       "the resource_provider_default_hypervisor config "
                       "option value as known by the nova-compute managing "
                       "that hypervisor.")),
    cfg.ListOpt('resource_provider_packet_processing_without_direction',
                default=[],
                help=_("Comma-separated list of "
                       "<hypervisor>:<packet_rate> tuples, defining the "
                       "minimum packet rate the OVS backend can guarantee in "
                       "kilo (1000) packet per second. The hypervisor name is "
                       "used to locate the parent of the resource provider "
                       "tree. Only needs to be set in the rare case when the "
                       "hypervisor name is different from the DEFAULT.host "
                       "config option value as known by the nova-compute "
                       "managing that hypervisor or if multiple hypervisors "
                       "are served by the same OVS backend. The default is :0 "
                       "which means no packet processing capacity is "
                       "guaranteed on the hypervisor named according to "
                       "DEFAULT.host.")),
    cfg.ListOpt('resource_provider_packet_processing_with_direction',
                default=[],
                help=_("Similar to the "
                       "resource_provider_packet_processing_without_direction "
                       "but used in case the OVS backend has hardware offload "
                       "capabilities. In this case the format is "
                       "<hypervisor>:<egress_pkt_rate>:<ingress_pkt_rate> "
                       "which allows defining packet processing capacity per "
                       "traffic direction. The direction is meant from the VM "
                       "perspective. Note that the "
                       "resource_provider_packet_processing_without_direction "
                       "and the "
                       "resource_provider_packet_processing_with_direction "
                       "are mutually exclusive options.")),
    cfg.StrOpt('resource_provider_default_hypervisor',
               help=_("The default hypervisor name used to locate the parent "
                      "of the resource provider. If this option is not set, "
                      "canonical name is used")),
    cfg.DictOpt('resource_provider_inventory_defaults',
                default={'allocation_ratio': 1.0,
                         'min_unit': 1,
                         'step_size': 1,
                         'reserved': 0},
                help=_("Key:value pairs to specify defaults used "
                       "while reporting resource provider inventories. "
                       "Possible keys with their types: "
                       "allocation_ratio:float, "
                       "max_unit:int, min_unit:int, "
                       "reserved:int, step_size:int, "
                       "See also: "
                       "https://docs.openstack.org/api-ref/placement/"
                       "#update-resource-provider-inventories")),
    cfg.DictOpt('resource_provider_packet_processing_inventory_defaults',
                default={'allocation_ratio': 1.0,
                         'min_unit': 1,
                         'step_size': 1,
                         'reserved': 0},
                help=_("Key:value pairs to specify defaults used "
                       "while reporting packet rate inventories. "
                       "Possible keys with their types: "
                       "allocation_ratio:float, "
                       "max_unit:int, min_unit:int, "
                       "reserved:int, step_size:int, "
                       "See also: "
                       "https://docs.openstack.org/api-ref/placement/"
                       "#update-resource-provider-inventories")),
    cfg.StrOpt('datapath_type', default=ovs_constants.OVS_DATAPATH_SYSTEM,
               choices=[(ovs_constants.OVS_DATAPATH_SYSTEM,
                         "Kernel datapath"),
                        (ovs_constants.OVS_DATAPATH_NETDEV,
                         "Userspace datapath")],
               help=_("OVS datapath to use.")),
    cfg.StrOpt('vhostuser_socket_dir',
               default=ovs_constants.VHOST_USER_SOCKET_DIR,
               help=_("OVS vhost-user socket directory.")),
    cfg.IPOpt('of_listen_address', default='127.0.0.1',
              help=_("Address to listen on for OpenFlow connections.")),
    cfg.PortOpt('of_listen_port', default=6633,
                help=_("Port to listen on for OpenFlow connections.")),
    cfg.IntOpt('of_connect_timeout', default=300,
               help=_("Timeout in seconds to wait for "
                      "the local switch connecting the controller.")),
    cfg.IntOpt('of_request_timeout', default=300,
               help=_("Timeout in seconds to wait for a single "
                      "OpenFlow request.")),
    cfg.IntOpt('of_inactivity_probe', default=10,
               help=_("The inactivity_probe interval in seconds for the local "
                      "switch connection to the controller. "
                      "A value of 0 disables inactivity probes.")),
    cfg.BoolOpt('openflow_processed_per_port',
                default=False,
                help=_('If enabled, all OpenFlow rules associated to a port '
                       'are processed at once, in one single transaction. '
                       'That avoids possible inconsistencies during OVS agent '
                       'restart and port updates. '
                       'If disabled, the flows will be processed in batches '
                       'of ``_constants.AGENT_RES_PROCESSING_STEP`` number of '
                       'OpenFlow rules.')),
    cfg.BoolOpt('qos_meter_bandwidth', default=False,
                help="Whether to enable the Openvswitch meter bandwidth "
                     "limit features which will add meter kbps rules "
                     "and apply them to the OpenFlow flow table "
                     "BANDWIDTH_RATE_LIMIT for VM ports."),
]

agent_opts = [
    cfg.BoolOpt('minimize_polling',
                default=True,
                help=_("Minimize polling by monitoring OVSDB for interface "
                       "changes.")),
    cfg.IntOpt('ovsdb_monitor_respawn_interval',
               default=ovs_constants.DEFAULT_OVSDBMON_RESPAWN,
               help=_("The number of seconds to wait before respawning the "
                      "OVSDB monitor after losing communication with it.")),
    cfg.ListOpt('tunnel_types', default=DEFAULT_TUNNEL_TYPES,
                help=_("Network types supported by the agent "
                       "(gre, vxlan and/or geneve).")),
    cfg.PortOpt('vxlan_udp_port', default=n_const.VXLAN_UDP_PORT,
                help=_("The UDP port to use for VXLAN tunnels.")),
    cfg.BoolOpt('l2_population', default=False,
                help=_("Use ML2 l2population mechanism driver to learn "
                       "remote MAC and IPs and improve tunnel scalability.")),
    cfg.BoolOpt('arp_responder', default=False,
                help=_("Enable local ARP responder if it is supported. "
                       "Requires OVS 2.1 and ML2 l2population driver. "
                       "Allows the switch (when supporting an overlay) "
                       "to respond to an ARP request locally without "
                       "performing a costly ARP broadcast into the overlay. "
                       "NOTE: If enable_distributed_routing is set to True "
                       "then arp_responder will automatically be set to True "
                       "in the agent, regardless of the setting in the config "
                       "file.")),
    cfg.BoolOpt('dont_fragment', default=True,
                help=_("Set or un-set the do not fragment (DF) bit on "
                       "outgoing IP packet carrying GRE/VXLAN tunnel.")),
    cfg.BoolOpt('enable_distributed_routing', default=False,
                help=_("Make the l2 agent run in DVR mode.")),
    cfg.BoolOpt('drop_flows_on_start', default=False,
                help=_("Reset flow table on start. Setting this to True will "
                       "cause brief traffic interruption.")),
    cfg.BoolOpt('tunnel_csum', default=False,
                help=_("Set or un-set the tunnel header checksum on "
                       "outgoing IP packet carrying GRE/VXLAN tunnel.")),
    cfg.BoolOpt('baremetal_smartnic', default=False,
                help=_("Enable the agent to process Smart NIC ports.")),
    # TODO(liuyulong): consider adding a new configuration
    # item to control ingress behavior.
    cfg.BoolOpt('explicitly_egress_direct', default=False,
                help=_("When set to True, the accepted egress unicast "
                       "traffic will not use action NORMAL. The accepted "
                       "egress packets will be taken care of in the final "
                       "egress tables direct output flows for unicast "
                       "traffic. This will aslo change the pipleline for "
                       "ingress traffic to ports without security, the final "
                       "output action will be hit in table 94. ")),
]

dhcp_opts = [
    cfg.BoolOpt('enable_ipv6', default=True,
                help=_("When set to True, the OVS agent DHCP "
                       "extension will add related flows for "
                       "DHCPv6 packets.")),
]

local_ip_opts = [
    cfg.BoolOpt('static_nat', default=False,
                help=_("When set to True, the Local IP Openvswitch agent "
                       "extension will use static NAT rules instead of using "
                       "conntrack. This allows to use feature in OVS offload "
                       "and DPDK scenarios at the cost of number and "
                       "complexity of flows. This also allows using this "
                       "feature together with the OVS firewall.")),
]


metadata_opts = [
    cfg.StrOpt('provider_cidr', default='240.0.0.0/16',
               help=_("Local metadata CIDR for VMs metadata traffic, "
                      "will be used as the IP range to generate the "
                      "VM's metadata IP.")),
    cfg.IntOpt('provider_vlan_id', default=1,
               help=_("The metadata tap device local vlan ID. This is only "
                      "available on the metadata bridge device.")),
    cfg.StrOpt('provider_base_mac', default="fa:16:ee:00:00:00",
               help=_("The base MAC address Neutron Openvswitch agent "
                      "will use for metadata traffic.")),
    cfg.IntOpt('host_proxy_listen_port', default=80,
               help=_("Host haproxy listen port for metadata path. This "
                      "is transparent for metadata traffic, VMs still try to "
                      "access 169.254.169.254:80 for metadata. But in "
                      "the metadata datapath flow pipeline, the destination "
                      "TCP port 80 will be changed to the value of "
                      "`host_proxy_listen_port` which the host haproxy "
                      "will listen on. For return traffic, the TCP source "
                      "port will be changed back to 80.")),
]


def register_ovs_agent_opts(cfg=cfg.CONF):
    cfg.register_opts(ovs_opts, "OVS")
    cfg.register_opts(agent_opts, "AGENT")
    cfg.register_opts(dhcp_opts, "DHCP")
    cfg.register_opts(common.DHCP_PROTOCOL_OPTS, "DHCP")
    cfg.register_opts(local_ip_opts, "LOCAL_IP")
    cfg.register_opts(meta_conf.METADATA_PROXY_HANDLER_OPTS, "METADATA")
    cfg.register_opts(metadata_opts, "METADATA")


def register_ovs_opts(cfg=cfg.CONF):
    cfg.register_opts(ovs_opts, "OVS")
