#!/usr/bin/env python3

import os
import re
import logging
import socket
import hashlib
from tqdm import tqdm
import platform
import getpass
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

class remote_bash_client(socket.socket):
    '''
    自定义的远程bash终端的客户端类
    继承自socket.socket
    基本命令类似于bash
    可以对本地或远程文件进行操作
    或者进行文件传输
    '''
    def __init__(self, root_dir='./client_root_dir/', HOST='127.0.0.1', PORT = 65432):
        socket.socket.__init__(self,socket.AF_INET, socket.SOCK_STREAM)#继承父类
        self.HOST = HOST# The server's hostname or IP address, you may set it to sth like '192.168.26.128'
        self.PORT = PORT# The port used by the server
        self.root_dir = root_dir#客户端根目录
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
        self.system = platform.system()#识别当前操作系统，增加兼容性
        self.current_local_path = '.'#客户端当前路径
        self.current_remote_path = '.'#远程服务器当前路径，实际上该变量不发送给远程服务器，客户端不应该修改服务器的变量
        self.pos = 'local'#当前位置，本地-local 或 远端-remote
        self.PS1 = ''#命令提示符
        self.usrname = getpass.getuser()
        self.cmd = ''
        self.cmd_list = []
    def PS1_update(self):
        if self.pos == 'local':
            path = self.current_local_path.strip('.')
        else:
            path = self.current_remote_path.strip('.')
        self.PS1 = '\033[1;32m'+self.usrname+'@'+self.pos+'\033[0m:\033[1;34m~'+path+'\033[0m$ '
    def cmd_process(self):
        self.cmd = self.cmd.replace('\t', ' ')
        self.cmd = re.sub(' +', ' ', self.cmd)
        self.cmd = self.cmd.strip(' ')
        self.cmd_list = self.cmd.split(' ')
    def cmd_cd(self):
        if self.pos == 'remote':
            if len(self.cmd_list)==2:
                if self.cmd_list[1]=='..':
                    self.current_remote_path = os.path.dirname(self.current_remote_path).strip('/')
                else:
                    self.current_remote_path = os.path.join(self.current_remote_path, self.cmd_list[1].strip('/'))
            else:
                self.current_remote_path = '.'
        else:
            if len(self.cmd_list)==2:
                if self.cmd_list[1]=='..':
                    self.current_local_path = os.path.dirname(self.current_local_path).strip('/')
                else:
                    self.current_local_path = os.path.join(self.current_local_path, self.cmd_list[1].strip('/'))
            else:
                self.current_local_path = '.'

    def cmd_ls(self):
        '''
        接收服务器发来的文件夹下文件信息
        print(' file \033[1;34m dir \033[0m') #彩色打印
        '''
        if self.pos == 'remote':
            self.cmd = self.cmd_list[0] + ' ' + self.current_remote_path + '/'
            if len(self.cmd_list)==2:
                self.cmd += self.cmd_list[1]
            self.sendall(bytes(self.cmd, encoding="utf-8"))
            server_response = self.recv(1024)
            info_size = int(server_response.decode("utf-8"))
            #print("文件大小：", info_size)
            info = bytes('', encoding='utf-8')
            # 2.接收文件内容
            self.send("ready".encode("utf-8"))  # 接收确认
            received_size = 0
            while received_size < info_size:
                size = 0  # 准确接收数据大小，解决粘包
                if info_size - received_size > 1024: # 多次接收
                    size = 1024
                else:  # 最后一次接收完毕
                    size = info_size - received_size

                data = self.recv(size)  # 多次接收内容，接收大数据
                info += data
                received_size += len(data)
            info_str = str(info, encoding='utf-8')
            #print(info_str)
            p = info_str.split(' ')
            print_str = '  '.join(['\033[1;34m'+s.strip('/')+'\033[0m' if s.endswith('/') else s for s in p])
            print(print_str)
        else:
            path = self.current_local_path
            if len(self.cmd_list)==2:
                path = os.path.join(path,self.cmd_list[1])
            full_path = os.path.join(self.root_dir,path)
            print_list = [p if os.path.isfile(os.path.join(full_path,p)) else (p+'/') for p in os.listdir(full_path)]
            print_str = '  '.join(['\033[1;34m'+s.strip('/')+'\033[0m' if s.endswith('/') else s for s in print_list])
            print(print_str)
            
    def get_file(self, filename):
        '''
        从服务器接收一个文件
        '''
        server_response = self.recv(1024)
        file_size = int(server_response.decode("utf-8"))
        #print("文件大小：", file_size)
        if file_size==0:
            logging.warning("文件不存在")
            return
        # 2.接收文件内容
        file_full_name = os.path.join(self.root_dir,self.current_local_path.strip('.\/'),os.path.basename(filename))
        filepath = os.path.split(file_full_name)[0]
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        if os.path.exists(file_full_name):
            overwrite_flag = input("file %s already exist, overwrite it?(yes, no or rename?)\n"%file_full_name)
            if overwrite_flag == "yes":
                self.send(bytes("ready", encoding="utf-8"))  # 接收确认
            elif overwrite_flag == "no":
                self.send(bytes("cancle", encoding="utf-8"))  # 取消接收
                return
            elif overwrite_flag == "rename":
                file_full_name += input("add postfix(eg. .new): ")
                self.send(bytes("ready", encoding="utf-8"))  # 接收确认
        else:
            self.send(bytes("ready", encoding="utf-8"))  # 接收确认
        with open(file_full_name, "wb") as f:
            received_size = 0
            m = hashlib.md5()
            with tqdm(total=file_size, unit='B', unit_scale=True, leave=True, desc="%s"%filename) as pbar:#进度条
                while received_size < file_size:
                    size = 0  # 准确接收数据大小，解决粘包
                    if file_size - received_size > 1024: # 多次接收
                        size = 1024
                    else:  # 最后一次接收完毕
                        size = file_size - received_size

                    data = self.recv(size)  # 多次接收内容，接收大数据
                    received_size += len(data)
                    pbar.update(len(data))
                    m.update(data)
                    f.write(data)
        print("file saved as \' %s \'"%file_full_name)
        
        #print("实际接收的大小:", received_size)  # 解码

        # 3.md5值校验
        md5_sever = self.recv(1024).decode("utf-8")
        md5_client = m.hexdigest()
        #print("服务器发来的md5:", md5_sever)
        #print("接收文件的md5:", md5_client)
        if md5_sever != md5_client:
            logging.warning("MD5 Verification Failed，所下载文件可能存在风险")
        else:
            logging.info("MD5 Verification successful!")




def main():
    with remote_bash_client() as client:
        client.connect((client.HOST, client.PORT))
        while True:
            client.PS1_update()
            client.cmd = input(client.PS1)
            client.cmd_process()
            #print(bytes(client.cmd, encoding="utf-8"))
            #print(client.cmd_list)
            if client.cmd.startswith('local'):
                client.pos = 'local'
            elif client.cmd.startswith('remote'):
                client.pos = 'remote'
            elif client.cmd.startswith('\x0c'):#CTRL+L
                if client.system == 'Windows':
                    os.system('cls')
                elif client.system == 'Linux':
                    os.system('clear')
            if client.cmd.startswith('disconnect'):
                client.sendall(bytes("disconnect", encoding="utf-8"))
                break
            elif client.cmd.startswith('get'):
                client.cmd = client.cmd_list[0] + ' ' + client.current_remote_path + '/'
                if len(client.cmd_list)==2:
                    client.cmd += client.cmd_list[1]
                client.sendall(bytes(client.cmd, encoding="utf-8"))
                client.get_file(client.cmd_list[1])
            elif client.cmd_list[0]=="getdir":
                client.sendall(bytes(client.cmd, encoding="utf-8"))
                pass
            elif client.cmd.startswith('ls'):
                client.cmd_ls()
            elif client.cmd_list[0]=="cd":
                client.cmd_cd()


if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()

