# #!/bin/env python
# # -*- coding: utf-8 -*-
# import paramiko
# import re
# import os
# def login_ssh(hostname,port,username,alarm_file):
#     #paramiko.util.log_to_file('./paramiko.log')
#     pkey='/home/sy_weihu1/.ssh/id_rsa'
#     key=paramiko.RSAKey.from_private_key_file(pkey)
#     s = paramiko.SSHClient()
#     s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     try:
#         s.connect(hostname,port,username,pkey=key,timeout=15)
#     except Exception:
#         alarm_file.write("%s broken\n"%hostname)
#         s.close()
#     return s
#
# def exec_cmd(conn,cmd):
#     result = ""
#     try:
#         if(not re.match(r".*rm\ .*",cmd)):
#             stdin,stdout,stderr = conn.exec_command(r"%s"%cmd)
#         else:
#             print "not excute"+cmd
#     except:
#         print("Commond execute error!")
#     if(len(stderr.readlines()) != 0):
#         print stderr.readlines()
#     for num in stdout:
#         result += r"%s"%num
#     return result
#
# def remote_close(conn):
#     conn.close()
#
# def batch_execute(hostname,cmdfile,file_log,alarm_file,type):
#     s1 =  login_ssh(hostname,22,'sy_weihu1',alarm_file)
#     for line1 in cmdfile:
#         try:
#             #s1 =  login_ssh(hostname,22,'root','BCzq@2017!')
#             file_log.write(exec_cmd(s1,line1).encode('utf8'))
#             file_log.write("====%s===%s===finish======\n"%(hostname,line1.strip('\n')))
#         except Exception as e:
#             print(e)
#     s1.close()
#     cmdfile.close()
# if __name__ == '__main__':
#     os.remove("./src/file.log")
#     file_log = open(r"./src/file.log","a+")
#     file_alarm = open("./src/finalalarm.log","w")
#     f = open(r"./src/hostall.txt","r")
#     for line2 in f:
#         if(not re.match("^#",line2)):
#             hostname = line2.split(' ')[0]
#             cmdfile = open("./conf/%s.cmd"%line2.split(' ')[1].strip('\n'),"r")
#             batch_execute(hostname,cmdfile,file_log,file_alarm,type)
#     f.close()
#     file_log.close()
#     file_alarm.close()
