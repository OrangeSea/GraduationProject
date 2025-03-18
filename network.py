from p4utils.mininetlib.network_API import NetworkAPI
import subprocess

def start_tcpdump(interface, output_file):
    '''
    启动tcpdump捕获指定接口的流量
    :param interface: 网络接口名称
    :param output_file: 输出文件路径
    :return:
    '''
    cmd = f"sudo tcpdump -i {interface} -w {output_file}"
    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"tcpdump started on interface {interface}, saving to {output_file}")

def main():
    net = NetworkAPI()

    net.setLogLevel('info')
    net.setCompiler(p4rt=True)

    for i in range(4):
        net.addP4RuntimeSwitch('s' + str(i + 1))

    net.setP4SourceAll('p4src/basic.p4')

    for i in range(4):
        net.addHost('h' + str(i + 1))

    net.addLink('h1', 's1')
    net.addLink('h2', 's1')
    net.addLink('s1', 's3')
    net.addLink('s1', 's4')

    net.addLink('h3', 's2')
    net.addLink('h4', 's2')
    net.addLink('s2', 's3')
    net.addLink('s2', 's4')
    net.l3()

    net.enablePcapDumpAll()
    net.enableLogAll()
    net.enableCli()
    net.startNetwork()

if __name__ == '__main__':
    main()