from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from scapy.all import sniff
import threading
import time

# 定义流量特征提取函数
def extract_flow_features(packet):
    """
    提取流量特征（模拟 CICFlowMeter 的功能）
    :param packet: 捕获的数据包
    """
    if packet.haslayer("IP"):
        src_ip = packet["IP"].src
        dst_ip = packet["IP"].dst
        proto = packet["IP"].proto
        length = len(packet)
        print(f"Flow: {src_ip} -> {dst_ip}, Protocol: {proto}, Length: {length}")

def capture_traffic(interface):
    """
    捕获指定接口的流量并提取特征
    :param interface: 网络接口名称
    """
    print(f"Capturing traffic on interface {interface}...")
    sniff(iface=interface, prn=extract_flow_features)


if __name__ == '__main__':
    capture_thread = threading.Thread(target=capture_traffic, args=("s1-eth1",))
    capture_thread.start()