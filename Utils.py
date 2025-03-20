from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_p4runtime_API import SimpleSwitchP4RuntimeAPI
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import os

class Utils:
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

    def reset(self):
        # Reset grpc server
        self.controller.reset_state()
        # Due to a bug in the way the grpc switch reset its states with the message
        # SetForwardingPipelineConfigRequest and Action VERIFY_AND_COMMIT (this is
        # a problem in the implementation of the server), subsequent initializations
        # (i.e. those which happen after the switch reset) of multicast groups
        # (with the same multicast id) are appended to the previous ones
        # (i.e. those present before the reset), which are supposed to be erased by the reset, but
        # they actually are not. This leads to duplicate packets sent to the same port.
        # This seems to be caused by the fact that, even if the grpc server is reset, the
        # switch forwarding states are not completely erased. In order to overcome this,
        # a complete reset can be achieved by resetting the switch via thrift.
        thrift_port = self.topo.get_thrift_port(self.sw_name)
        controller_thrift = SimpleSwitchThriftAPI(thrift_port)
        # Reset forwarding states
        controller_thrift.reset_state()

    def config_digest(self):
        self.controllers['s1'].digest_enable('faeture_t', 1000000, 10, 1000000 )

    def run_digest_loop(self):
        self.config_digest()
        while True:
            dig_list = self.controllers['s1'].get_digest_list()
            self.recv_msg_digest(dig_list)

    def recv_msg_digest(self, dig_list):
        learning_data = self.unpack_digest(dig_list)
        self.learn(learning_data)

    def learn(self, learning_data):

        print(learning_data)
            # print("mac: %012X ingress_port: %s " % (mac_addr, ingress_port))

    def unpack_digest(self, dig_list):
        learning_data = []
        for dig in dig_list.data:
            mac_addr = int.from_bytes(dig.struct.members[0].bitstring, byteorder='big')
            ingress_port = int.from_bytes(dig.struct.members[1].bitstring, byteorder='big')
            a3 = int.from_bytes(dig.struct.members[2].bitstring, byteorder='big')
            a4 = int.from_bytes(dig.struct.members[3].bitstring, byteorder='big')
            a5 = int.from_bytes(dig.struct.members[4].bitstring, byteorder='big')
            a6 = int.from_bytes(dig.struct.members[5].bitstring, byteorder='big')
            a7 = int.from_bytes(dig.struct.members[6].bitstring, byteorder='big')
            a8 = int.from_bytes(dig.struct.members[7].bitstring, byteorder='big')
            a9 = int.from_bytes(dig.struct.members[8].bitstring, byteorder='big')
            a10 = int.from_bytes(dig.struct.members[9].bitstring, byteorder='big')
            a11 = int.from_bytes(dig.struct.members[10].bitstring, byteorder='big')
            a12 = int.from_bytes(dig.struct.members[11].bitstring, byteorder='big')
            a13 = int.from_bytes(dig.struct.members[12].bitstring, byteorder='big')
            a14 = int.from_bytes(dig.struct.members[13].bitstring, byteorder='big')
            a15 = int.from_bytes(dig.struct.members[14].bitstring, byteorder='big')

            learning_data.append((mac_addr, ingress_port, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15))
        return learning_data

if __name__ == '__main__':
    Utils().run_digest_loop()