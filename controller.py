import os
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_p4runtime_API import SimpleSwitchP4RuntimeAPI
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import redis
import random
import time
import threading
import subprocess
import logging
from SafetyLevelCalculation import *

TRUST_LEVEL = '_T'
COMPUTE_LEVEL = '_C'
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Controller(object):
    def __init__(self):
        if not os.path.exists('topology.json'):
            print('Could not find topology object!!!\n')
            raise Exception

        self.topo = load_topo('topology.json')
        self.controllers = {}
        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.s1_cli = subprocess.Popen(
            f'simple_switch_CLI --thrift-port 9090',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        self.s2_cli = subprocess.Popen(
            f'simple_switch_CLI --thrift-port 9091',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        self.init()
        
        

    def init(self):
        self.connect_to_switches()
        # for controller in self.controllers:
        #     controller.set_packet_in_handler(self.parse_register)
        for sw in self.topo.get_p4rtswitches().keys():
            hosts = self.topo.get_hosts_connected_to(sw)
            if hosts :
                for host in hosts:
                    ip_addr = self.topo.get_host_ip(host)
                    self.r.set(ip_addr + TRUST_LEVEL, 'Th')
                    self.r.set(ip_addr + COMPUTE_LEVEL, 'Cl')
                    host_id = int(host[1:])
                    create_table_for_host(host_id)

        

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
        ecmp_grps = {sw_name:{} for sw_name in self.topo.get_p4rtswitches().keys()}
        for sw_name, controller in self.controllers.items():
            for sw_dst in self.topo.get_p4rtswitches():
                if (sw_dst == sw_name):
                    hosts = self.topo.get_hosts_connected_to(sw_dst)
                    for host in hosts:
                        host_ip = self.topo.get_host_ip(host) + '/32'
                        host_mac = self.topo.get_host_mac(host)
                        port = self.topo.node_to_node_port_num(sw_dst, host)
                        print("table_add at {}:".format(sw_name))
                        controller.table_add('ipv4_lpm', 'set_nhop', [host_ip], [host_mac, str(port)])
                else:
                    hosts = self.topo.get_hosts_connected_to(sw_dst)
                    paths = self.topo.get_shortest_paths_between_nodes(sw_name, sw_dst)
                    if len(hosts) > 0:
                        # subnet = self.topo.get_host_ip(hosts[0]) + '/24'
                        if (len(paths) == 1):
                            for host in hosts:
                                next_hop = paths[0][1]
                                host_ip = self.topo.get_host_ip(host) + '/24'
                                next_hop_mac = self.topo.node_to_node_mac(next_hop, sw_name)
                                port = self.topo.node_to_node_port_num(sw_name, next_hop)
                                print("table_add at {}:".format(sw_name))
                                controller.table_add('ipv4_lpm', 'set_nhop', [host_ip], [next_hop_mac, str(port)])
                        elif(len(paths) > 1):
                            next_hops = [x[1] for x in paths]
                            dst_macs_ports = [(self.topo.node_to_node_mac(next_hop, sw_name),
                                                self.topo.node_to_node_port_num(sw_name, next_hop)) for next_hop in next_hops]
                            for host in hosts:
                                host_ip = self.topo.get_host_ip(host) + '/24'
                                if ecmp_grps[sw_name].get(tuple(dst_macs_ports), None):
                                    grp_id = ecmp_grps[sw_name][tuple(dst_macs_ports)]
                                    print("table_add at {}:".format(sw_name))
                                    controller.table_add('ipv4_lpm', 'ecmp_group', [host_ip], [str(grp_id), str(len(dst_macs_ports))])
                                else:
                                    new_grp_id = len(ecmp_grps[sw_name]) + 1
                                    ecmp_grps[sw_name][tuple(dst_macs_ports)] = new_grp_id
                                    print("table_add at {}:".format(sw_name))
                                    controller.table_add('ipv4_lpm', 'ecmp_group', [host_ip], [str(new_grp_id), str(len(dst_macs_ports))])
                                    for i, (mac, port) in enumerate(dst_macs_ports):
                                        print("table_add at {}:".format(sw_name))
                                        controller.table_add('ecmp_group_to_nhop', 'set_nhop', [str(new_grp_id), str(i)], [mac, str(port)])
                                
    def add_inuds_header(self):
        self.controllers['s1'].table_add('check_is_ingress_border', 'set_is_ingress_border', ['1'])
        self.controllers['s1'].table_add('check_is_egress_border', 'is_egress_border', ['1'])
        self.controllers['s1'].table_add('set_indus_valid', 'set_indus_feature', ['10.2.4.2'])

        self.controllers['s2'].table_add('check_is_ingress_border', 'set_is_ingress_border', ['2'])
        self.controllers['s2'].table_add('check_is_egress_border', 'is_egress_border', ['2'])
        self.controllers['s2'].table_add('set_indus_valid', 'set_indus_feature', ['10.1.1.2'])

    def read_counter(self):
        '''
        read counter and write them back to register
        :return:
        '''
        s1_port = 9090
        s2_port = 9091
        reg_name = 'indus_features'

        fwd_pkt_cnt = 0
        bwd_pkt_cnt = 0
        fwd_pkt_len_mean = 0
        flow_pkt_per_sec = 0
        while (True):
            x = self.controllers['s1'].counter_read('fwd_counter', 1)
            fwd_pkt_per_sec = x[1] - fwd_pkt_cnt
            fwd_pkt_cnt = x[1]
            if (x[1] != 0) :
                fwd_pkt_len_mean = int(x[0] / x[1])
            y = self.controllers['s2'].counter_read('fwd_counter', 2)
            bwd_pkt_per_sec = y[1] - bwd_pkt_cnt
            bwd_pkt_cnt = y[1]

            flow_pkt_per_sec = fwd_pkt_per_sec + bwd_pkt_per_sec
            # print(f'fwd_pkt_per_sec: {fwd_pkt_per_sec}')
            # print(f'bwd_pkt_per_sec: {bwd_pkt_per_sec}')
            # print(f'fwd_pkt_len_mean: {fwd_pkt_len_mean}')
            # print(f'flow_pkt_per_sec: {flow_pkt_per_sec}')

            self.register_write(s1_port, reg_name, index=5, val=flow_pkt_per_sec)
            logging.info(f'writing register {reg_name} {5}, flow_pkt_per_sec: {flow_pkt_per_sec}')
            self.register_write(s1_port, reg_name, index=6, val=fwd_pkt_per_sec)
            logging.info(f'writing register {reg_name} {6}, fwd_pkt_per_sec: {fwd_pkt_per_sec}')


            self.register_write(s2_port, reg_name, index=5, val=flow_pkt_per_sec)
            logging.info(f'writing register {reg_name} {5}, flow_pkt_per_sec: {flow_pkt_per_sec}')
            self.register_write(s2_port, reg_name, index=6, val=fwd_pkt_per_sec)
            logging.info(f'writing register {reg_name} {6}, fwd_pkt_per_sec: {fwd_pkt_per_sec}')



            time.sleep(1)

    def register_write(self, sw_port, reg_name, index, val):
        command = f'register_write {reg_name} {index} {val}\n'
        input = bytes(command, encoding="utf8")
        if sw_port == 9090:
            self.s1_cli.stdin.write(input)
            self.s1_cli.stdin.flush()
        elif sw_port == 9091:
            self.s2_cli.stdin.write(input)
            self.s2_cli.stdin.flush()


    def parse_register(self, packet):
        while True:
            self.parse_packet(packet)

    def parse_packet(self, packet):
        # 解析以太网头部
        eth_header = packet[:14]
        eth_dst = eth_header[:6].hex()
        eth_src = eth_header[6:12].hex()
        eth_type = int.from_bytes(eth_header[12:14], byteorder='big')

        # 解析 IPv4 头部
        if eth_type == 0x0800:
            ip_header = packet[14:34]
            ip_src = '.'.join(map(str, ip_header[12:16]))
            ip_dst = '.'.join(map(str, ip_header[16:20]))
            print(f"Ethernet src: {eth_src}, dst: {eth_dst}, type: {eth_type}")
            print(f"IPv4 src: {ip_src}, dst: {ip_dst}")
        else:
            print("Non-IPv4 packet received")

    def handel_packet(self, packet):
        print("Handling packet...")
        token = random.randint(0, 65535)
        self.r.set('token', token)


    def main(self):
        self.route()
        self.add_inuds_header()
        # thread = threading.Thread(target=self.read_counter)
        # thread.start()



if __name__ == '__main__':
    controller = Controller().main()
