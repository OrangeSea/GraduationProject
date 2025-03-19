import subprocess
import pandas as pd
import os
import time
from threading import Thread

features = ['protocol', 'fwd_pkt_len_min', 'fwd_pkt_len_mean', 'bwd_pkt_len_min',
            'bwd_pkt_len_std', 'flow_pkts_s', 'fwd_pkts_s', 'pkt_len_mean', 'pkt_len_std',
            'fin_flag_cnt', 'rst_flag_cnt', 'pkt_size_avg', 'fwd_seg_size_avg', 'init_fwd_win_byts',
            'init_bwd_win_byts'
            ]

s1_cli = subprocess.Popen(
        f'simple_switch_CLI --thrift-port 9090',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
)
s2_cli = subprocess.Popen(
        f'simple_switch_CLI --thrift-port 9091',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
)

reg_name = 'indus_features'

def listening_port(port, output_file):
    cmd = f'sudo cicflowmeter -i {port} -c {output_file} '

    os.system(cmd)

    # subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def read_csv(file_name):
    try:
        df = pd.read_csv(file_name)
        if not df.empty:
            return df  # 返回最后一行
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        print(f"Error reading file: {e}")
    return None
    # if os.path.exists(file_name):
    #     return pd.read_csv(file_name)
    # return pd.DataFrame()

def monitor_output(file_name, interval):
    while True:
        if os.path.exists(file_name):
            last_line = read_csv(file_name)
            if last_line is not None:
                print("Last line:")
                print(last_line.iloc[-1])
                for i, feature in enumerate(features):
                    register_write(9090, reg_name=reg_name, index=i, val=int(last_line[feature].iloc[-1]))
                    register_write(9091, reg_name=reg_name, index=i, val=int(last_line[feature].iloc[-1]))
                    print(f'{feature}: {int(last_line[feature].iloc[-1])}')
        else:
            print(f"File {file_name} does not exist.")
        time.sleep(interval)

def register_write(sw_port, reg_name, index, val):
    command = f'register_write {reg_name} {index} {val}\n'
    input = bytes(command, encoding="utf8")
    if sw_port == 9090:
        s1_cli.stdin.write(input)
        s1_cli.stdin.flush()
    elif sw_port == 9091:
        s2_cli.stdin.write(input)
        s2_cli.stdin.flush()

if __name__ == '__main__':
    port = 's1-eth1'
    file_name = 'output.csv'
    listen_thread = Thread(target=listening_port, args=(port, file_name))
    listen_thread.start()
    # listening_port(port, file_name)
    monitor_output(file_name, 0.5)


