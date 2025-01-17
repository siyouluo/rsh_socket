#!/usr/bin/env python3
#-*- coding: utf-8 -*-
import os
import re
import sys
import logging
import socket
import hashlib
from tqdm import tqdm
import platform
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

class remote_shell_server(socket.socket):
    '''
    自定义的远程Shell终端(rsh)的服务器类
    继承自socket.socket
    可以响应来自于客户端的类似于bash的命令
    可以将服务器端的文件传输给客户端，或则接收来自客户端的文件
    '''
    def __init__(self, root_dir='./SERVER_ROOT_DIR/', HOST='127.0.0.1', PORT = 65432):
        socket.socket.__init__(self,socket.AF_INET, socket.SOCK_STREAM)#继承父类
        self.HOST = HOST# The server's hostname or IP address, you may set it to sth like '192.168.26.128'
        self.PORT = PORT# The port used by the server
        self.root_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],root_dir.strip('./'))#客户端根目录
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
        self.system = platform.system#识别当前操作系统，增加兼容性
        self.current_local_path = '.'#客户端当前路径
        self.current_remote_path = '.'#远程服务器当前路径，实际上该变量不发送给远程服务器，客户端不应该修改服务器的变量
        self.cmd = ''
        self.cmd_list = []
        self.conn = None
        self.addr = None
    def send_file(self, filename):
        file_full_name = os.path.join(self.root_dir,filename)
        if os.path.isfile(file_full_name):  # 判断文件存在
            # 1.先发送文件大小，让客户端准备接收
            size = os.stat(file_full_name).st_size  #获取文件大小
            self.conn.send(str(size).encode("utf-8"))  # 发送数据长度
            print("预计发送的大小：", size)
            # 2.发送文件内容
            client_ACK = self.conn.recv(1024).decode("utf-8")  # 接收确认   ready
            if client_ACK == 'ready':
                m = hashlib.md5()
                f = open(file_full_name, "rb")
                for line in f:
                    self.conn.send(line)  # 发送数据
                    m.update(line)
                f.close()
                # 3.发送md5值进行校验
                md5 = m.hexdigest()
                self.conn.send(md5.encode("utf-8"))  # 发送md5值
                print("md5:", md5)
            elif client_ACK == 'cancel':
                pass
        else:
            self.conn.send('not found'.encode("utf-8"))#文件不存在
    def send_dir_info(self, path):
        full_path = os.path.join(self.root_dir,path)
        if not os.path.exists(full_path):
            self.conn.send('not found'.encode("utf-8"))  # 发送数据长度
            return
        #print(full_path)
        #print(os.listdir(full_path))
        info_str = ' '.join([p if os.path.isfile(os.path.join(full_path,p)) else (p+'/') for p in os.listdir(full_path)])
        size = len(info_str)
        self.conn.send(str(size).encode("utf-8"))  # 发送数据长度
    #    print("发送的大小：", size)
        self.conn.recv(1024)  # 接收确认
        self.conn.send(info_str.encode('utf-8'))  # 发送数据
    def cmd_getdir_process(self):
        full_path = os.path.join(self.root_dir,self.cmd_list[1])
        if os.path.isdir(full_path):
            full_path_list = os.listdir(full_path)
            info_str = ' '.join([p if os.path.isfile(os.path.join(full_path,p)) else (p+'/') for p in full_path_list])
            self.conn.send(('dir '+ info_str).encode('utf-8'))  # 发送数据
            print('fpl:',('dir '+ info_str))
        else:
            self.conn.send('None'.encode('utf-8'))  # 发送数据
    def recieve_file(self, savename):
        self.conn.send("ACK".encode("utf-8"))
        client_response = self.conn.recv(1024)
        file_size = int(client_response.decode("utf-8"))
        self.conn.send("ready".encode("utf-8"))
        # 开始接收文件，并写入服务器硬盘空间
        file_full_name = os.path.join(self.root_dir,savename)
        file_full_name = file_full_name.replace('./', '')
        savedir = os.path.split(file_full_name)[0]
        if not os.path.exists(savedir):
            os.makedirs(savedir)
        with open(file_full_name, "wb") as f:
            received_size = 0
            m = hashlib.md5()
            with tqdm(total=file_size, unit='B', unit_scale=True, leave=True, desc="%s"%savename) as pbar:#进度条
                while received_size < file_size:
                    size = 0  # 准确接收数据大小，解决粘包
                    if file_size - received_size > 1024: # 多次接收
                        size = 1024
                    else:  # 最后一次接收完毕
                        size = file_size - received_size

                    data = self.conn.recv(size)  # 多次接收内容，接收大数据
                    received_size += len(data)
                    pbar.update(len(data))
                    m.update(data)
                    f.write(data)
        print("file saved as \' %s \'"%file_full_name)
        #print("实际接收的大小:", received_size)  # 解码
        # md5校验
        md5_client = self.conn.recv(1024).decode("utf-8")
        md5_sever = m.hexdigest()
        #print("客户端发来的md5:", md5_client)
        #print("接收文件的md5:", md5_sever)
        if md5_sever != md5_client:
            logging.warning("MD5 Verification Failed，所接收文件可能存在风险")
        else:
            logging.info("MD5 Verification successful!")
        self.conn.send("done".encode("utf-8"))




def main(ip='127.0.0.1', port=65432):
    with remote_shell_server(HOST=ip, PORT=port) as server:
        server.bind((server.HOST, server.PORT))
        print('server socket:\n',server)
        server.listen()
        print("server: start listen...\n")
        while True:
            server.conn, server.addr = server.accept()
            print('server: Connected by', server.addr)
            while server.conn:
                server.cmd = server.conn.recv(1024).decode("utf-8")
                if not server.cmd:
                    break
                print('client: ',server.cmd)
                server.cmd_list = server.cmd.split(' ')
                if server.cmd_list[0]=="get":
                    server.send_file(server.cmd_list[1])
                elif server.cmd_list[0]=="getdir":
                    server.cmd_getdir_process()
                elif server.cmd_list[0]=="ls":
                    server.send_dir_info(server.cmd_list[1])
                elif server.cmd_list[0]=="put":
                    server.recieve_file(server.cmd_list[1])
                elif server.cmd_list[0]=="putdir":
                    pass
            print("server: disconnect with client addr:", server.addr,'\n')

if __name__=="__main__":       
    try:
        if len(sys.argv)==1:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))#8.8.8.8是Google提供的免费DNS服务器的IP地址
                ip = s.getsockname()[0]
            port = 65432
        elif len(sys.argv)==2:
            ip = str(sys.argv[1])
            port = 65432
        elif len(sys.argv)==3:
            ip = str(sys.argv[1])
            port = int(sys.argv[2])
        main(ip=ip, port=port)
    except KeyboardInterrupt:
        exit()
