import subprocess
import os
import time
from scapy.all import sniff, wrpcap

def write_register(sw_port, reg_name, index, val):
    '''
    通过CLI写入寄存器
    :param reg_name:
    :param index:
    :param val:
    :return:
    '''

    command = f'register_write {reg_name} {index} {val}\n'

    cli_process = subprocess.Popen (
        f'simple_switch_CLI --thrift-port {sw_port}',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )

    input = bytes(command, encoding="utf8")

    cli_process.stdin.write(input)
    cli_process.stdin.flush()

    command = f'register_read {reg_name} {index}'
    input = bytes(command, encoding="utf8")
    cli_process.stdin.write(input)
    cli_process.stdin.flush()

    output = cli_process.stdout.readline()
    print("Output:", output)

    # input = bytes(command, encoding = "utf8")
    #
    # cli_process.communicate(input=input, timeout=1)
    #
    # command = f'register_read {reg_name} {index}'
    #
    # input = bytes(command, encoding="utf8")
    #
    # cli_process.communicate(input=input, timeout=1)
    #

def start_tcpdump(interface, output_file):
    """
    启动 tcpdump 捕获指定接口的流量
    :param interface: 网络接口名称
    :param output_file: 输出文件路径
    """
    cmd = f"sudo tcpdump -i {interface} -w {output_file}"
    os.system(cmd)
    # subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # print(f"tcpdump started on interface {interface}, saving to {output_file}")

def capture_traffic(interface, pcap_file):
    """
    使用 tcpdump 捕获流量并保存到 pcap 文件
    :param interface: 网络接口名称
    :param pcap_file: 输出 pcap 文件路径
    """
    print(f"Capturing traffic on interface {interface}...")
    # 使用 tcpdump 捕获流量
    cmd = f"tcpdump -i {interface} -w {pcap_file}"
    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def read_pcap(pcap_file):
    """
    使用 scapy 实时读取 pcap 文件并分析数据包
    :param pcap_file: pcap 文件路径
    """
    print(f"Reading pcap file {pcap_file}...")
    packets = sniff(offline=pcap_file)
    for packet in packets:
        print(packet.summary())  # 打印数据包摘要

if __name__ == '__main__':
    # reg_name = 'indus_features'
    # index = 3
    # val = 50
    # write_register(9090, reg_name, index, val)
    # write_register(9090, reg_name, 4, 100)
    # index = 3
    # val = 50
    # write_register(9091, reg_name, index, val)
    # write_register(9091, reg_name, 4, 100)

    # start_tcpdump('s1-eth1', 's1_ethe.pcap')

    pcap_file = 's1_eth1.pcap'
    capture_traffic('s1-eth1', pcap_file)
    time.sleep(5)
    read_pcap(pcap_file)



