import subprocess

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

if __name__ == '__main__':
    reg_name = 'indus_features'
    index = 3
    val = 50
    write_register(9090, reg_name, index, val)
    write_register(9090, reg_name, 4, 100)
    index = 3
    val = 50
    write_register(9091, reg_name, index, val)
    write_register(9091, reg_name, 4, 100)

