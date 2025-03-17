from scapy.all import *
import sys


def tcp_syn_scan(target_ip, target_port, window_size=512):
    # 构造IP层
    ip = IP(dst=target_ip)

    # 构造TCP层（SYN包，窗口大小设置为512）
    tcp = TCP(dport=target_port, flags="S", window=window_size)

    # 发送SYN包并接收响应
    response = sr1(ip / tcp, timeout=1, verbose=False)

    # 分析响应
    if response and response.haslayer(TCP):
        if response[TCP].flags & 0x12:  # SYN-ACK标志
            print(f"Port {target_port} is open (Window Size: {response[TCP].window})")
        elif response[TCP].flags & 0x14:  # RST-ACK标志
            print(f"Port {target_port} is closed")
    else:
        print(f"Port {target_port} is filtered or no response")


def scan_port_range(target_ip, start_port, end_port, window_size=512):
    for port in range(start_port, end_port + 1):
        tcp_syn_scan(target_ip, port, window_size)


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <target_ip> <start_port> <end_port>")
        sys.exit(1)

    target_ip = sys.argv[1]
    start_port = int(sys.argv[2])
    end_port = int(sys.argv[3])

    # 扫描端口范围
    scan_port_range(target_ip, start_port, end_port, window_size=512)


if __name__ == "__main__":
    main()