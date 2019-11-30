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

class remote_shell_client(socket.socket):
    '''
    自定义的远程Shell终端(rsh)的客户端类
    继承自socket.socket
    基本命令类似于bash
    可以对本地或远程文件进行操作
    或者进行文件传输
    '''
    def __init__(self, root_dir='./client_root_dir/', HOST='127.0.0.1', PORT = 65432):
        socket.socket.__init__(self,socket.AF_INET, socket.SOCK_STREAM)#继承父类
        self.HOST = HOST# The server's hostname or IP address, you may set it to sth like '192.168.26.128'
        self.PORT = PORT# The port used by the server
        self.root_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],root_dir.strip('./'))#客户端根目录
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
        if self.system=='Windows':
            from colorama import init
            init(autoreset=True)
    def PS1_update(self):
        if self.pos == 'local':
            path = self.current_local_path.strip('.')
        else:
            path = self.current_remote_path.strip('.')
        self.PS1 = '\033[1;32m'+self.usrname+'@'+self.pos+'\033[0m'+':'+'\033[0;34m~'+path+'\033[0m'+'$ '
        #self.PS1 = '\033[1;32m'+self.usrname+'@'+self.pos+'\033[0m:\033[1;34m~'+path+'\033[0m$ '

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
            if server_response.decode("utf-8") == 'not found':
                logging.warning("no such dir!")
                return
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
            if not os.path.exists(full_path):
                print("no such dir!")
                return
            print_list = [p if os.path.isfile(os.path.join(full_path,p)) else (p+'/') for p in os.listdir(full_path)]
            print_str = '  '.join(['\033[1;34m'+s.strip('/')+'\033[0m' if s.endswith('/') else s for s in print_list])
            print(print_str)
            
    def cmd_get_file(self, filename, savename):
        '''
        从服务器接收一个文件
        '''
        # 接收预处理，决定是否需要接收，需要接收多少字节
        cmd_str = 'get %s'%(filename)
        self.sendall(bytes(cmd_str, encoding="utf-8"))
        server_response = self.recv(1024)
        if server_response.decode("utf-8") == 'not found':
            logging.warning("文件不存在")
            return
        file_size = int(server_response.decode("utf-8"))
        file_full_name = os.path.join(self.root_dir,savename)
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
                self.send(bytes("cancle", encoding="utf-8"))  # 取消接收
                return
        else:
            self.send(bytes("ready", encoding="utf-8"))  # 接收确认
        
        # 开始接收文件，并写入本地磁盘空间
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
        # md5校验
        md5_sever = self.recv(1024).decode("utf-8")
        md5_client = m.hexdigest()
        #print("服务器发来的md5:", md5_sever)
        #print("接收文件的md5:", md5_client)
        if md5_sever != md5_client:
            logging.warning("MD5 Verification Failed，所下载文件可能存在风险")
        else:
            logging.info("MD5 Verification successful!")
    def cmd_getdir(self, targetpath, savepath):
        full_path = os.path.join(self.root_dir, savepath)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        # 将远程文件夹full_path 递归地下载到本地文件夹local_full_path
        self.send(bytes("getdir %s"%targetpath, encoding="utf-8"))  
        # 向远程服务器发送命令，下载文件夹，远程服务器检查是文件夹还是文件
        # 如果是文件夹，发回 'dir'，以及该文件夹下所有文件夹和文件，否则返回'None'
        server_response = self.recv(1024*16).decode("utf-8") #我们先假定此次发回的字节数不会超过1KB
        server_response_list = server_response.split(' ')
        if server_response_list[0]=='dir':
            info_list = server_response_list[1:]
            print(info_list)
            for i in info_list:
                if i.endswith('/'):
                    self.cmd_getdir(os.path.join(targetpath, i), os.path.join(savepath, i))
                else:
                    new_target_path = os.path.join(targetpath, i)
                    new_save_path = os.path.join(savepath, i)
                    self.cmd_get_file(new_target_path, new_save_path)
    def cmd_put_file(self, filename, savename):
        '''
        将本地文件发送至远程服务器
        '''
        file_full_name = os.path.join(self.root_dir,filename)
        if os.path.isfile(file_full_name):  # 判断文件存在
            # 通知服务器，准备接收
            cmd_str = 'put %s'%(savename)
            self.sendall(bytes(cmd_str, encoding="utf-8"))
            server_response = self.recv(1024)
            if server_response.decode("utf-8") == 'deny':
                logging.warning("服务器拒绝接收")
                return
            # 1.先发送文件大小，让服务器端准备接收
            size = os.stat(file_full_name).st_size  #获取文件大小
            self.send(str(size).encode("utf-8"))  # 发送数据长度
            print("预计发送的大小：", size)
            # 2.发送文件内容
            server_ACK = self.recv(1024).decode("utf-8")  # 再次接收确认   ready
            if server_ACK == 'ready':
                m = hashlib.md5()
                f = open(file_full_name, "rb")
                for line in f:
                    self.send(line)  # 发送数据
                    m.update(line)
                f.close()
                # 3.发送md5值进行校验
                md5 = m.hexdigest()
                self.send(md5.encode("utf-8"))  # 发送md5值
                print("md5:", md5)
                server_ACK = self.recv(1024).decode("utf-8")  # 完成确认   ready
                if server_ACK == 'done':
                    print("done!")
            elif server_ACK == 'cancle':
                pass
        else:
            logging.warning("file: %s not found"%file_full_name)
    def cmd_putdir(self, targetpath, savepath):
        full_path = os.path.join(self.root_dir,targetpath)
        #print("targetpath:", targetpath)
        #print("savepath:", savepath)
        #print("full_path", full_path)
        if os.path.isdir(full_path):
            full_path_list = os.listdir(full_path)
            for p in full_path_list:
                full_name = os.path.join(full_path,p)
                if os.path.isfile(full_name):
                    self.cmd_put_file(os.path.join(targetpath, p), os.path.join(savepath, p))
                else:
                    target_path = os.path.join(self.current_local_path,os.path.join(targetpath, p))
                    save_path = os.path.join(self.current_remote_path, os.path.join(savepath, p))
                    #print("r: ",target_path, save_path)
                    self.cmd_putdir(target_path, save_path)







def main():
    with remote_shell_client() as client:
        client.connect((client.HOST, client.PORT))#连接服务器
        while True:
            client.PS1_update()#根据用户名，当前路径等设置命令提示符
            print(client.PS1, end='')#打印命令提示符，例如 usr@local: ~$ xxx
            client.cmd = input()#等待用户输入
            client.cmd_process()#用户输入命令可能不够规范，需要进行预处理
            #print(bytes(client.cmd, encoding="utf-8")) #调试，显示读取到的用户命令
            #print(client.cmd_list)#cmd_list是分解后的用户命令字符串列表
            if client.cmd_list[0]=='local':
                client.pos = 'local'
            elif client.cmd_list[0]=='remote':
                client.pos = 'remote'
            elif client.cmd_list[0]=='\x0c':#CTRL+L 清屏指令，需要输入回车才能执行
                if client.system == 'Windows':
                    os.system('cls')
                elif client.system == 'Linux':
                    os.system('clear')
            if client.cmd_list[0]=='disconnect':#与服务器断开连接
                break
            elif client.cmd_list[0]=='get':
                file_name = os.path.join(client.current_remote_path, client.cmd_list[1])
                save_name = os.path.join(client.current_local_path, os.path.basename(client.cmd_list[1]).strip('/'))
                client.cmd_get_file(file_name, save_name)
            elif client.cmd_list[0]=="getdir":
                target_path = os.path.join(client.current_remote_path,client.cmd_list[1])
                save_path = os.path.join(client.current_local_path, os.path.basename(client.cmd_list[1].strip('/')))
                client.cmd_getdir(target_path, save_path)
            elif client.cmd_list[0]=='ls':
                client.cmd_ls()
            elif client.cmd_list[0]=="cd":
                client.cmd_cd()
            elif client.cmd_list[0]=='put':
                file_name = os.path.join(client.current_local_path, client.cmd_list[1])
                save_name = os.path.join(client.current_remote_path, os.path.basename(client.cmd_list[1]).strip('/'))
                client.cmd_put_file(file_name, save_name)
            elif client.cmd_list[0]=="putdir":
                target_path = os.path.join(client.current_local_path,client.cmd_list[1])
                save_path = os.path.join(client.current_remote_path, os.path.basename(client.cmd_list[1].strip('/')))
                client.cmd_putdir(target_path, save_path)


if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()
