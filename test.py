from scapy.all import *
from scapy.layers.inet import IP


def main():
    pkt = IP(dst='wwww.baidu.com')
    send(pkt)

if __name__ == '__main__':
    main()