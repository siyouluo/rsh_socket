# socket文件传输
本项目是《计算机网络》课程项目，要求用socket实现一个简单的文件服务器，在不同机器之间进行文件的上传和下载。
本人开发环境为Ubuntu16.04，在windows下也是可以运行的（但是在开发期间我不保证这一点）。
在指定ip地址后，甚至可以在Ubuntu虚拟机和windows物理主机之间进行文件传输，某种意义上可以实现一个共享文件夹的功能。


# 预期功能
服务器端开始运行后，运行客户端程序。客户端可以选择下载(get)或者上传(put)文件  

1. 若选择下载(get)，服务器将根目录下所有文件和文件夹名发送给客户端，依次列出。客户端可以选择：
    1. 下载某个文件
    2. 递归下载某个文件夹
    3. 进入某个文件夹操作
2.  若选择上传(put)，客户端可以选择：
    1. 上传客户端中的某个文件
    2. 递归地上传客户端中某个文件夹

## 预期实现的指令
```bash
# cd，ls命令可以通过local，remote命令指定操作的是服务器还是客户端
# 实际上这只是改变客户端中的两个变量
# local，remote不影响get，put操作，即get，put的方向始终不变
local
remote
cd
cd <DIR>
ls [-l,-a] <DIR>
get <FILE> -n <NEW NAME>
get -d <DIR>
get -f
put
```

# 依赖库
## tqdm
```bash
python3 -m pip install tqdm
```

# 演示
![server.png](./img/server.png)  
![client.png](./img/client.png)  

# issues
在cmd、power shell、terminal中输出彩色字符的方式是不同的
目前彩色输出在windows平台上存在一些bug
后期可以考虑根据不同平台调用不同方法
```python
import platform
def UsePlatform( ):
    sysstr = platform.system()
    if(sysstr =="Windows"):
        print ("Call Windows tasks")
    elif(sysstr == "Linux"):
        print ("Call Linux tasks")
    else:
        print ("Other System tasks")

```


# Tutorials
* [Socket Programming in Python (Guide)](https://realpython.com/python-sockets/)  
* [Python编程：socket实现文件传输](https://blog.csdn.net/mouday/article/details/79101951)  
* [python3 socket文件传输](https://juejin.im/post/5af270fc6fb9a07aa43c3114)  
* [Python 文件I/O](https://www.runoob.com/python/python-files-io.html)  
* [Python os.path() 模块](https://www.runoob.com/python/python-os-path.html)  
* [python中print打印显示颜色](https://blog.csdn.net/qq_34857250/article/details/79673698)  
* [Python3改变cmd（命令行）输出颜色](https://blog.csdn.net/wy_97/article/details/79663014)  
* [Python判断当前操作系统类型以及os/sys/platform模块简介](https://blog.csdn.net/gatieme/article/details/45674367)  
* [python类的继承](https://www.cnblogs.com/bigberg/p/7182741.html)  
* [python 获取脚本所在目录的正确方法](https://blog.csdn.net/vitaminc4/article/details/78702852)  
* [解决CMD命令行窗口不显示颜色问题python](https://blog.csdn.net/qq_15158911/article/details/88943571)  

