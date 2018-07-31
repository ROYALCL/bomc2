# coding:utf-8
# -*- coding:utf-8 -*-
# -*- env:python27 -*-
import paramiko
import re
import logging
import ConfigParser
import os
import time
import threadpool
import sys


# 通过用户名和密码建立连接
def login_ssh_passwd(hostname, port, username, passwd):
    paramiko.util.log_to_file('./log/paramiko.log')
    sshclient = paramiko.SSHClient()
    sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        sshclient.connect(hostname, port, username, passwd, timeout=TIMEOUT)
        return sshclient
    except Exception:
        sshclient.close()
        return -1


def exec_bash(conn, bash, hostname):
    result = ''
    if not re.match(r".*rm\ .*", bash):
        try:
            stdin, stdout, stderr = conn.exec_command(r"%s" % bash)
            if len(stderr.readlines()) != 0:
                for num in stderr:
                    result += r"%s" % num
            for num in stdout:
                result += r"%s" % num
            return result
        except Exception:
            logging.error("Server " + hostname + " Commond " + bash + " execute error!")
            return result
    else:
        logging.warning("Bash " + bash + " not promit")
        return result


# 执行结果，参数分别是需要执行的主机，执行的命令，执行后原始数据，需要告警的数据
# @hosts hosts 文件里面的一行
# @primary_file 执行返回的初始结果
def batch_execute(hosts_str):
    # 字典格式如下
    # example_dict = {'IP': '', 'HOSTNAME': '','PORT':'', 'USERNAME': '', 'PASSWD': '',
    #                 'CPU': {'BASH': '', 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
    #                 'MEM': {'BASH': '', 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
    #                 'FILE': {'BASH': "", 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
    #                 'INODE': {'BASH': '', 'THRESHOLD1': '', 'THRESHOLD2': '', 'THRESHOLD3': '', 'NP': ''},
    #                 'PROCESS': ['', '']}
    # 将字符串转换成字典
    if not re.match(r"^#.*", hosts_str):
        host_dict = eval(hosts_str)
        conn = ''
        # 创建原始数据缓存list
        clist = ['==========================' + host_dict['IP'] + '=================================\n',
                 "--------------------------" + host_dict['CPU']['BASH'] + "---------------------------------\n"]
        try:
            conn = login_ssh_passwd(host_dict['IP'], host_dict['PORT'], host_dict['USERNAME'], host_dict['PASSWD'])
            # 返回值为-1，即创建连接失败，后续处理完后跳到下一个连接
            if conn == -1:
                logging.error("Server " + host_dict['IP'] + " connect failed!")
                # 调用告警，通知连接失败
            else:
                # 执行CPU命令
                logging.info("Server " + host_dict['IP'] + " connect successful!")
                result_cpu = exec_bash(conn, host_dict['CPU']['BASH'], host_dict['IP'])
                # 将结果存进缓存list里面
                clist.append(result_cpu)
                # 数据清洗，写入alarm_file，用于告警
                clist.append(
                    "--------------------------" + host_dict['MEM']['BASH'] + "---------------------------------\n")
                # 执行MEM命令
                result_mem = exec_bash(conn, host_dict['MEM']['BASH'], host_dict['IP'])
                clist.append(result_mem)
                # 数据清洗，写入alarm_file，用于告警
                clist.append(
                    "--------------------------" + host_dict['FILE']['BASH'] + "---------------------------------\n")
                # 执行FILE命令
                result_file = exec_bash(conn, host_dict['FILE']['BASH'], host_dict['IP'])
                clist.append(result_file)
                # 数据清洗，写入alarm_file，用于告警
                clist.append(
                    "--------------------------" + host_dict['INODE']['BASH'] + "---------------------------------\n")
                # 执行INODE命令
                result_inode = exec_bash(conn, host_dict['INODE']['BASH'], host_dict['IP'])
                clist.append(result_inode)
                # 数据清洗，写入alarm_file，用于告警
                # 进程部分
                clist.append("--------------------------PROCESS---------------------------------\n")
                for i in range(len(host_dict['PROCESS'])):
                    # 执行进程命令
                    result_tmp = exec_bash(conn, host_dict['PROCESS'][i], host_dict['IP'])
                    clist.append(
                        'IP ' + host_dict['IP'] + " \"" + host_dict['PROCESS'][i] + '\"   ' + result_tmp + '\n')
                    # 数据清洗，写入alarm_file，用于告警
                conn.close()
                # ？是否需要加锁？
                for i in range(len(clist)):
                    primary_file.write(clist[i])
                # 刷新文件，从缓冲区写入硬盘
                primary_file.flush()
                # 计算CPU使用量
                CPU_NUM = float("".join(re.findall(r".*Cpu.*", result_cpu)).split(' ')[2]) + float(
                    "".join(re.findall(r".*Cpu.*", result_cpu)).split(' ')[5])
                print "CPU used:" + str(CPU_NUM)
                # MEM_NUM = float(re.split("\s*", "".join(re.findall(r".*Mem.*", result_mem)))[2]) / float(
                #     re.split("\s*", "".join(re.findall(r".*Mem.*", result_mem)))[1])
                print "MEM used:" + result_mem
                # 文件系统
                for i in re.findall(r".*% /.*", result_file):
                    print "Filesystem " + i.split(' ')[-2].split('%')[0]
                for i in re.findall(r".*% /.*", result_file):
                    print "Inode " + i.split(' ')[-2].split('%')[0]
                # [- 192.168.1.0 -]  On-Site Inspection  OK
                print '[- ' + host_dict['IP'] + ' -]   On-Site Inspection  OK'
        except Exception:
            # alarm_file IP+HOSTNAME+CONTENT+NP+TIME
            conn.close()
            logging.error("Server " + host_dict['IP'] + " Commonds execute error!")
            print '[- ' + host_dict['IP'] + ' -]   On-Site Inspection  FAILED'


# 发送告警 IP +等级+内容+
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
        pass
    #     time.sleep(10)
    #     lalarm.write(time2 + " :  --" + status + "--| Host " + ip + "  " + value)


def mutliprocess(hosts, num, is_thread):
    # 根据配置文件，确定是单线程还是多线程执行
    if is_thread != 'true':
        logging.info("single thread exec")
        for host in hosts:
            # 如果没有匹配到空行或者#
            if not re.match(r"^#.*", host):
                batch_execute(host)
    else:
        logging.info('enable mutlithreading !')
        logging.info('Number of threads: ' + str(num))
        # 创建线程池executor
        # 如果要执行的线程>线程池容量。那么根据时间动态增加到线程池执行
        pool = threadpool.ThreadPool(num)
        requests = threadpool.makeRequests(batch_execute, hosts)
        [pool.putRequest(req) for req in requests]
        pool.wait()

        # with ThreadPoolExecutor(num) as executor:
        # for each in hosts:
        #  #       executor.submit(batch_execute, each)
        #     batch_execute(each)

    # with ThreadPoolExecutor(num) as executor:
    #     executor.map(batch_execute,hosts)


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    # 初始化函数，从配置文件bomc.conf读取脚本配置，初始基础参数
    # 读取配置文件
    conf = './conf/bomc.conf'
    cf = ConfigParser.RawConfigParser()
    cf.read(conf)
    # 初始化日志配置
    FILE = cf.get('LOG', 'LOG_FILE')
    LOG_FORMAT = cf.get('LOG', 'LOG_FORMAT')
    DATE_FORMAT = cf.get('LOG', 'LOG_DATE_FORMAT')
    LEVEL = int(cf.get('LOG', 'LOG_LEVEL'))
    logging.basicConfig(filename=FILE, level=LEVEL, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    # 设置ssh连接超时
    TIMEOUT = float(cf.get('HOST', 'HOST_TIMEOUT'))
    host_list = []
    # 打开主机配置文件
    hosts = open(cf.get('HOST', 'HOST_FILE'), mode='r')
    # for line in hosts.readlines():
    #    host_list.append(line)
    # hosts.close()
    # 构造结果文件名称 ./log/PRIMARY_2018-xx-xx.log
    PRI_PATH = cf.get('PRIMARY', 'PRI_PATH')
    file_name = PRI_PATH + 'PRIMARY_' + time.strftime('%Y-%m-%d', time.localtime()) + '.log'
    primary_file = open(file_name, 'a', buffering=True)
    # 调用多线程处理
    mutliprocess(hosts, int(cf.get('EXEC', 'MU_THREAD')), cf.get('EXEC', 'THREAD'))
    # 关闭已打开的文件
    primary_file.close()
    hosts.close()
