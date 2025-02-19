import os
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_p4runtime_API import SimpleSwitchP4RuntimeAPI
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI


class Controller(object):
    def __init__(self):
        if not os.path.exists('topology.json'):
            print('Could not find topology object!!!\n')
            raise Exception

        self.topo = load_topo('topology.json')
        self.controllers = {}
        self.init()

    def init(self):
        self.connect_to_switches()

    def reset_states(self):
        """Resets registers, tables, etc.
        """
        for p4rtswitch, controller in self.controllers.items():
            # Reset grpc server
            controller.reset_state()

            # Connect to thrift server
            thrift_port = self.topo.get_thrift_port(p4rtswitch)
            controller_thrift = SimpleSwitchThriftAPI(thrift_port)
            # Reset forwarding states
            controller_thrift.reset_state()

    def connect_to_switches(self):
        for p4rtswitch, data in self.topo.get_p4switches().items():
            device_id = self.topo.get_p4switch_id(p4rtswitch)
            grpc_port = self.topo.get_grpc_port(p4rtswitch)
            p4rt_path = data['p4rt_path']
            json_path = data['json_path']
            self.controllers[p4rtswitch] = SimpleSwitchP4RuntimeAPI(device_id, grpc_port,
                                                                    p4rt_path=p4rt_path,
                                                                    json_path=json_path)

    def set_table_defaults(self):
        for controller in self.controllers.values():
            controller.table_set_default("ipv4_lpm", "drop", [])
            controller.table_set_default("ecmp_group_to_nhop", "drop", [])

    def route(self):
        ecmp_grps = {sw: {} for sw in self.topo.get_p4rtswitches().keys()}
        for sw_src, controller in self.controllers.items():
            for sw_dst in self.topo.get_p4switches():
                if (sw_src == sw_dst):
                    hosts = self.topo.get_hosts_connected_to(sw_dst)
                    for host in hosts:
                        sw_port = self.topo.node_to_node_port_num(sw_dst, host)
                        host_ip = self.topo.get_host_ip(host) + '/32'
                        host_mac = self.topo.get_host_mac(host)

                        controller.table_add('ipv4_lpm', 'set_nhop', [host_ip], [host_mac, str(sw_port)])
                else:
                    hosts = self.topo.get_hosts_connected_to(sw_dst)
                    if (len(hosts) > 0):
                        paths = self.topo.get_shortest_paths_between_nodes(sw_src, sw_dst)
                        if (len(paths) == 1):
                            next_hop = paths[0][1]
                            subnet = self.topo.get_host_ip(hosts[0]) + '/24'
                            sw_port = self.topo.node_to_node_port_num(sw_src, next_hop)
                            next_hop_mac = self.topo.node_to_node_mac(next_hop, sw_src)
                            controller.table_add('ipv4_lpm', 'set_nhop', [subnet], [next_hop_mac, str(sw_port)])
                        elif (len(paths) > 1):
                            next_hops = [x[1] for x in paths]
                            next_hop_macs_ports = [(self.topo.node_to_node_mac(next_hop, sw_src),
                                                    self.topo.node_to_node_port_num(sw_src, next_hop))
                                                   for next_hop in next_hops]
                            hosts = self.topo.get_hosts_connected_to(sw_dst)
                            subnet = self.topo.get_host_ip(hosts[0]) + '/24'
                            if (ecmp_grps[sw_src].get(tuple(next_hop_macs_ports), None)):
                                ecmp_group_id = ecmp_grps[sw_src].get(tuple(next_hop_macs_ports))
                                controller.table_add('ipv4_lpm', 'ecmp_group', [subnet], [str(ecmp_group_id), len(next_hop_macs_ports)])
                            else:
                                new_ecmp_grp = len(next_hop_macs_ports) + 1
                                ecmp_grps[sw_src][tuple(next_hop_macs_ports)] = new_ecmp_grp
                                for i, (mac, port) in enumerate(next_hop_macs_ports):
                                    controller.table_add('ecmp_group_to_nhop', 'set_nhop', [str(new_ecmp_grp), str(i)],
                                                         [mac, str(port)])
                                controller.table_add('ipv4_lpm', 'ecmp_group', [subnet], [str(new_ecmp_grp), str(len(next_hop_macs_ports))])

    def main(self):
        self.route()


if __name__ == '__main__':
    controller = Controller().main()
