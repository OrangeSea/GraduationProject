import mysql.connector
import mysql.connector.pooling
import logging
import time
import redis

CREDIT_VALUE_MAX = 30
r = redis.Redis(host='localhost', port=6379, db=0)

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'knowledge',
    'pool_name': 'knowledge_pool',
    'pool_size': 5,
    'pool_reset_session': True
}
logging.basicConfig(
    level=logging.INFO,
    format = "%(levelname)s - %(message)s",  # 日志格式
    handlers = [logging.StreamHandler()]
)

connection_pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)

create_malicious_table_sql = """
CREATE TABLE IF NOT EXISTS {table_name} (
    behavior_index INT AUTO_INCREMENT PRIMARY KEY,
    malicious_type VARCHAR(50) NOT NULL,
    penalty_coefficient FLOAT NOT NULL,
    timestamp DATETIME NOT NULL
)
"""

create_normal_table_sql = """
CREATE TABLE IF NOT EXISTS {table_name} (
    behavior_index INT AUTO_INCREMENT PRIMARY KEY,
    last_penalty_index INT DEFAULT 0,
    timestamp DATETIME NOT NULL
)
"""

def create_table_for_host(host_id):
    '''
    为指定主机创建两张表（如果表不存在）
    :param host_id:
    :return:
    '''
    malicious_table_name = f'host_malicious_behavior_{host_id}'
    normal_table_name = f'host_normal_behavior_{host_id}'

    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()

        cursor.execute(create_malicious_table_sql.format(table_name=malicious_table_name))

        cursor.execute(create_normal_table_sql.format(table_name=normal_table_name))

    except mysql.connector.Error as e:
        print(f'MySQL ERROE:{e}')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print('MySQL closed....')

def insert_malicious(host_id, data):
    malicious_table_name = f'host_malicious_behavior_{host_id}'
    insert_query = f"""
    INSERT INTO {malicious_table_name} (malicious_type, penalty_coefficient, timestamp)
    VALUES (%s, %s, %s)
    """
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()

        for record in data:
            cursor.execute(insert_query, record)

        connection.commit()
        logging.info(f'insert into {malicious_table_name}, values {data}')
    except mysql.connector.Error as e:
        logging.error(f'Database error:{e}')
        logging.exception('Exception details:')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info('Connection returned to the pool.')

def insert_normal(host_id, time_stamp):
    normal_table_name = f'host_normal_behavior_{host_id}'
    insert_query = f"""
    INSERT INTO {normal_table_name} (last_penalty_index, timestamp)
    VALUES (%s, %s)
    """
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        last_penalty_index = r.get('h' + str(host_id) + "_last_normal_index")
        last_penalty_index = int(last_penalty_index)
        data = [(last_penalty_index, time_stamp)]
        for record in data:
            cursor.execute(insert_query, record)

        connection.commit()
        logging.info(f'insert into {normal_table_name}, values {data}')
    except mysql.connector.Error as e:
        logging.error(f'Database error:{e}')
        logging.exception('Exception details:')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info('Connection returned to the pool.')

def query_last_penakty_index(host_id):
    last_penalty_index = 0
    normal_table_name = f'host_normal_behavior_{host_id}'
    query = f"""
    SELECT last_penalty_index from {normal_table_name} ORDER BY timestamp DESC LIMIT 1
    """
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            return last_penalty_index
        else:
            last_penalty_index = rows[0][0] # 获取最后一行的 last_penalty_index
            print(f'last_penalty_index:{last_penalty_index}')
            return last_penalty_index
    except mysql.connector.Error as e:
        logging.error(f'Database error:{e}')
        logging.exception('Exception details:')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info('Connection returned to the pool.')

def calculate_CrN(host_id):
    '''
    返回惩罚函数计算结果
    :param host_id:
    :return:
    '''
    CrN = 0
    malicious_table_name = f'host_malicious_behavior_{host_id}'
    normal_table_name = f'host_normal_behavior_{host_id}'
    query_malicious_sum = f"""
    SELECT COUNT(*) FROM {malicious_table_name}
    """
    query_all_behavior = f"""
    SELECT behavior_index, penalty_coefficient FROM {malicious_table_name}
    """
    query_last_normal_behavior_index = f"""
    SELECT behavior_index FROM {normal_table_name} ORDER BY timestamp DESC LIMIT 1
    """
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(query_malicious_sum)
        result = cursor.fetchall()
        if not result:
            return 0
        else:
            sum = result[0][0]
            logging.info(f'host_malicious_behavior_{host_id} count: {sum}')
            cursor.execute(query_all_behavior)
            for (behavior_index, penalty_coefficient) in cursor:
                val = penalty_coefficient / (sum - (behavior_index - 1))
                CrN += val
            logging.info(f'Penalty value is {CrN}')
            cursor.execute(query_last_normal_behavior_index)
            row = cursor.fetchall()
            if not row:
                last_normal_behavior_index = 0
            else:
                last_normal_behavior_index = row[0][0]
                r.set('h' + str(host_id) + '_last_normal_index', last_normal_behavior_index)
            return CrN, last_normal_behavior_index
    except mysql.connector.Error as e:
        logging.error(f'Database error:{e}')
        logging.exception('Exception details:')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info('Connection returned to the pool.')

def calculate_CrP(host_id):
    normal_table_name = f'host_normal_behavior_{host_id}'
    query_malicious_sum = f"""
        SELECT COUNT(*) FROM {normal_table_name}
    """
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(query_malicious_sum)
        result = cursor.fetchall()
        if not result:
            return 0
        else:
            sum = result[0][0]
            last_normal_behavior_index = query_last_penakty_index(host_id)
            logging.info(f'last_normal_behavior_index: {last_normal_behavior_index}')
            return min(sum - last_normal_behavior_index, CREDIT_VALUE_MAX)
    except mysql.connector.Error as e:
        logging.error(f'Database error:{e}')
        logging.exception('Exception details:')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info('Connection returned to the pool.')


if __name__ == '__main__':
    host_id = 1
    timestamp = time.time()
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    data = [('DOS_UDP', 0.3, formatted_time)]
    # insert_malicious(host_id, data)

    # data = [(0, formatted_time)]
    # insert_normal(1, formatted_time)

    # query_last_penakty_index(host_id)

    CrN, last_normal_behavior_index = calculate_CrN(host_id)
    print(f'CrN = {CrN}, last_normal_behavior_index:{last_normal_behavior_index}')
    CrP = calculate_CrP(host_id)
    print(f'CrP = {CrP}')
    Cr = CrP - CrN
    print(f'Cr = {Cr}')



