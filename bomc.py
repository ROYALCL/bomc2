# -*- coding:utf-8 -*-
# -*- env:python3 -*-
import paramiko
import re
import logging
import configparser
import os
import time
import sys

# 用于建立SSH连接，通过SSH互信，返回一个连接
def login_ssh_trusted(hostname, port, pkey):
    pkey = cf.get('HOST', 'LOGIN_PKEY')
    key = paramiko.RSAKey.from_private_key_file(pkey)
    sshclient = paramiko.SSHClient()
    sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        sshclient.connect(hostname, port, pkey=key, timeout=TIMEOUT)
        logging.info("Server " + hostname + " connect successful!")
    except Exception:
        logging.error("Server " + hostname + " connect failed!")
        sshclient.close()
    return sshclient


# 通过用户名和密码建立连接
def login_ssh_passwd(hostname, port, username, passwd):
    sshclient = paramiko.SSHClient()
    sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        sshclient.connect(hostname, port, username, passwd, timeout=TIMEOUT)
        logging.info("Server " + hostname + " connect successful!")
    except Exception:
        logging.error("Server " + hostname + " connect failed!")
        sshclient.close()
    return sshclient


def exec_bash(conn, bash, hostname):
    result = ''
    try:
        if not re.match(r".*rm\ .*", bash):
            stdin, stdout, stderr = conn.exec_command(r"%s" % bash)
        else:
            logging.warning("Bash " + bash + " not promit")
    except Exception:
        logging.error("Server " + hostname + " Commond " + bash + " execute error!")
    if len(stderr.readlines()) != 0:
        for num in stderr:
            result += r"%s" % num
    for num in stdout:
        result += r"%s" % num
    return result


# 执行结果，参数分别是需要执行的主机，执行的命令，执行后原始数据，需要告警的数据
def batch_execute(hosts, primary_file):
    # 逐行读取hosts里面的的主机记录
    for host in hosts:
        # 如果没有匹配到空行或者#
        if not re.match(r"^#.*", host):
            # 字典格式如下
            # example_dict = {'IP': '', 'HOSTNAME': '','PORT':'', 'USERNAME': '', 'PASSWD': '',
            #                 'CPU': {'BASH': '', 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
            #                 'MEM': {'BASH': '', 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
            #                 'FILE': {'BASH': "", 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
            #                 'INODE': {'BASH': '', 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
            #                 'PROCESS': ['', '']}
            # 将字符串转换成字典
            host_dict = eval(host)
            try:
                conn = login_ssh_passwd(host_dict['IP'], host_dict['PORT'], host_dict['USERNAME'],
                                        host_dict['PASSWD'])
                primary_file.write(
                    "==========================" + host_dict['IP'] + "=================================\n")
                primary_file.write(
                    "--------------------------" + host_dict['CPU']['BASH'] + "---------------------------------\n")
                # 执行CPU命令
                result_tmp = exec_bash(conn, host_dict['CPU']['BASH'], host_dict['IP'])
                primary_file.write(result_tmp)
                # 数据清洗，写入alarm_file，用于告警
                primary_file.write(
                    "--------------------------" + host_dict['MEM']['BASH'] + "---------------------------------\n")
                # 执行MEM命令
                result_tmp = exec_bash(conn, host_dict['MEM']['BASH'], host_dict['IP'])
                primary_file.write(result_tmp)
                # 数据清洗，写入alarm_file，用于告警
                primary_file.write(
                    "--------------------------" + host_dict['FILE']['BASH'] + "---------------------------------\n")
                # 执行FILE命令
                result_tmp = exec_bash(conn, host_dict['FILE']['BASH'], host_dict['IP'])
                primary_file.write(result_tmp)
                # 数据清洗，写入alarm_file，用于告警
                primary_file.write(
                    "--------------------------" + host_dict['INODE']['BASH'] + "---------------------------------\n")
                # 执行INODE命令
                result_tmp = exec_bash(conn, host_dict['INODE']['BASH'], host_dict['IP'])
                primary_file.write(result_tmp)
                # 数据清洗，写入alarm_file，用于告警

                for i in range(len(host_dict['PROCESS'])):
                    print(host_dict['PROCESS'][i])
                    primary_file.write(
                        "--------------------------" + host_dict['PROCESS'][i] + "---------------------------------\n")
                    # 执行进程命令
                    result_tmp = exec_bash(conn, host_dict['PROCESS'][i], host_dict['IP'])
                    primary_file.write(result_tmp)
                    # 数据清洗，写入alarm_file，用于告警
                conn.close()
            except Exception:
                # alarm_file IP+HOSTNAME+CONTENT+NP+TIME
                #conn.close()
                logging.error("Server " + host_dict['IP'] + " Commonds execute error!")
                pass


# 发送告警
def alarmExtE(ip, status, value, lalarm):
    # 通过AddExtEvent.sh直接调用extevent包发送告警
    # AddExtEvent中对应内容：
    # 1为host，即为主机名，也可以是IP
    # 2-4是需要配置标准化短信内容需要的，暂可以不管（2为实例，每个告警指标实例必须唯一，不然会造成发送不出来，3和4需要标准化配置，如调试可暂时采用
    # 3的内容输入：logerror
    # 4的内容输入：zw）
    # 5为status，即为告警等级，目前告警等级有critical，major，minor等，如需要值班组告警则必须要为critical
    # 6为value，即为告警内容，在这里需要填写你方告警内容，同时将告警规则写进去（如NP144），这样我方就可以通过匹配规则将对应短信发送到具体人员，同时值班组也才能查看到人员，从而进行电话联系
    # 7-8可以不管
    # 9为occurtime，即为告警时间，指的是你方产生告警的时间
    # Example: AddExtEvent.sh 192.168.0.2 usr FSCapacity FILESYSTEM OK 0 80 70 "03/31/2005 17:36:51"
    # IP 告警等级 告警内容

    # 生成格式化当前时间字符串
    time2 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 发送告警
    os.system("sh ./AddExtEvent.sh " + ip + " " + status + " " + value + " 80 70 " + time2)
    # 告警信息写入文件作为记录
    try:
        lalarm.write(time2 + " :  --" + status + "--| Host " + ip + "  " + value)
    except:
        time.sleep(10)
        lalarm.write(time2 + " :  --" + status + "--| Host " + ip + "  " + value)


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    # 读取配置文件
    conf = './conf/bomc.conf'
    global cf
    cf = configparser.RawConfigParser()
    cf.read(conf,encoding='utf-8')
    # 初始化日志配置
    FILE = cf.get('LOG', 'LOG_FILE')
    LOG_FORMAT = cf.get('LOG', 'LOG_FORMAT')
    DATE_FORMAT = cf.get('LOG', 'LOG_DATE_FORMAT')
    LEVEL = int(cf.get('LOG', 'LOG_LEVEL'))
    logging.basicConfig(filename=FILE, level=LEVEL, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    # global TIMEOUT
    TIMEOUT = float(cf.get('HOST', 'HOST_TIMEOUT'))
    PRI_PATH = cf.get('PRIMARY', 'PRI_PATH')
    hosts = open(cf.get('HOST', 'HOST_FILE'), 'r')
    # 构造结果文件名称 ./log/PRIMARY_2018-07-28.log
    file_name = PRI_PATH + 'PRIMARY_' + time.strftime('%Y-%m-%d', time.localtime()) + '.log'
    primary_file = open(file_name, 'a')
    # try:
    batch_execute(hosts, primary_file)
    primary_file.close()
    hosts.close()