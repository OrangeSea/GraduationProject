import time
from indus_feature_header import *

def get_if():
    ifs=get_if_list()
    iface=None # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface

def main():
    features = {f'feature_{i}': 0 for i in range(6)}
    iface = get_if()
    for i in range(50):
        packet = Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff') / \
                 IP(dst="10.1.2.2", proto=27) / \
                 indus_feature_header(feature_0=1, feature_1=2, feature_2=3, feature_3=4, feature_4=5, feature_5=6, feature_6=7, feature_7=8)
        packet.show()
        sendp(packet)
        print(f'send packets {i + 1}')


if __name__ == '__main__':
    main()
