serv00和ct8主机一键安装哪吒探针和多主机保活
======================================================

## 1 背景
基于`serv00`和`ct8`这种配置较低的主机，比较适合用来做探针。目前还没发现能自动安装哪吒面板和agent客户端的脚本，以及多主机间动态保活，所以写了这个项目。效果体验：[https://monitor1.typecodes.us.kg](https://monitor1.typecodes.us.kg) 。


## 2 特点

```
1、支持分别安装最新版本的哪吒dashboard和agent客户端，且安装时基本一路点确认即可，无需复杂操作；
2、弃用PM2，使用脚本进行进程监控，尽量避免被serv00或者ct8杀掉；
3、自动生成crontab，实现进程监控和主机保活；
4、对于多个主机，可以实现相互保活；
5、多个主机之间的通信，使用ssh公私钥，无需暴露主机密码；
6、支持 青龙面板 或者其它云主机对自己的serv00或者ct8主机进行进程监控和保活；
7、支持自定义进程保活，例如自己写的任何一个服务，可以在monitor.conf配置文件中简单配置即可；
8、支持企业微信机器人、企业微信app应用、tg、pushPlus等监控通知。
```


## 2 使用步骤

```
1、下载脚本: git clone https://github.com/vfhky/serv00_ct8_nezha.git
2、进入项目: cd serv00_ct8_nezha
3、修改配置文件: vim config/host.eg 然后添加需要保活的主机信息。
4、开始安装: python3 main.py 。
```


## 3 配置文件说明

在`config`配置目录下面有4个模板文件，其中`host.eg`和`sys.eg`这两个配置文件是需要手工配置，其它两个文件都不需要修改，系统会自动根据相关逻辑生成对应的`xxx.conf`配置文件。

#### 3.1 主机配置模板 host.eg

`host.eg`模板文件是填写需要保活的主机信息。例如当前要保活另外一个s9的serv00机器(用户名是vhub)，那么填写：

```
s9.serv00.com|22|vhub|password
```

#### 3.2 系统常量模板 sys.eg

这个是系统配置文件，可以配置企业微信机器人、企业微信app应用、tg、pushPlus等监控通知等功能。

#### 3.3 进程监控模板 monitor.eg

用于进程监控：当进程不存在时（例如被serv00系统自动杀掉），会自动重新拉起进程。当安装完哪吒dashboard和agent后，系统会自动生成类似以下的配置。当然也可以手工追加其它进程来实现该进程的监控保活。

```
/home/vfhky/nezha_app/agent|nezha-agent|sh nezha-agent.sh|foreground
/home/vfhky/nezha_app/dashboard|nezha-dashboard|./nezha-dashboard|background
```

#### 3.4 多主机心跳保活模板 heartbeat.eg

当手工配置了`host.eg`主机模板并手工执行安装后，系统会根据这个模板自动生成主机需要保活的主机信息。示例如下：

`s9.serv00.com|22|vhub`


## 4 其它详细说明

详细操作过程，进程监控，保活原理以及青龙面板的使用等等，请参考`serv00和ct8主机一键安装哪吒探针和多主机保活`系列文章：

1、常规手工安装方式： 包括如何server00开启应用、开启端口、申请github的token等等，[《在serv00主机上安装哪吒探针》](https://typecodes.com/linux/server00installnezha.html)

2、使用项目一键安装： [《serv00和ct8主机一键安装哪吒探针和多主机保活》](https://typecodes.com/python/serv00ct8nezha.html)

3、项目的架构说明： [《serv00和ct8主机一键安装哪吒探针和多主机保活(二)》](https://typecodes.com/python/serv00ct8nezha2.html)

4、演示青龙面板保活： [《serv00和ct8主机一键安装哪吒探针和多主机保活(三)》](https://typecodes.com/python/serv00ct8nezha3.html)

5、utils.sh工具类使用教程： [《serv00和ct8主机一键安装哪吒探针和多主机保活(四)》](https://typecodes.com/python/serv00ct8nezha4.html)

6、使用七牛、腾讯云cos、阿里云oss云存储备份哪吒面板数据库的使用教程： [《serv00和ct8主机一键安装哪吒探针和多主机保活(五)》](https://typecodes.com/python/serv00ct8nezha5.html)

7、修复项目中哪吒面板不显示主机区域的问题： [《serv00和ct8主机一键安装哪吒探针和多主机保活(六)》](https://typecodes.com/python/serv00ct8nezha6.html)
