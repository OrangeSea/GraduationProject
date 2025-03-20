import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'knowledge'
}

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
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute(create_normal_table_sql.format(table_name=malicious_table_name))

        cursor.execute(create_normal_table_sql.format(table_name=normal_table_name))

    except mysql.connector.Error as e:
        print(f'MySQL ERROE:{e}')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print('MySQL closed....')