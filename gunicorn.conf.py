#!/usr/bin/env python
# coding:UTF-8
# =================================================================
# @ Author : zhaolin
# @ Desc : gunicorn 配置文件
# @ Date : 2021-11-01
# @ Remark :
# ==================================================================

import multiprocessing
import os

if not os.path.exists("/data/gpa/log"):
    os.mkdir("/data/gpa/log")

bind = '0.0.0.0:8000'
backlog = 1024
chdir = '/data/gpa'
timeout = 60
daemon = False
reload = False
worker_class = 'sync'
workers = 2
# 处理完多少个请求后重启
max_requests = 20
user = "root"
group = "root"
raw_env = ["DJANGO_SETTINGS_MODULE=gpa.settings"]
# -e DJANGO_SETTINGS_MODULE=sanhang_cup.settings_pro
# 需要额外安装组件支持进程的重命名, 否则显示gunicorn
name = "gunicorn-shsj"
# 日志级别，这个日志级别指的是错误日志的级别，而访问日志的级别无法设置
loglevel = 'debug'
# 设置gunicorn访问日志格式，错误日志无法设置
access_log_format = '%(t)s %(p)s %(h)s %(U)s %(q)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'
# 访问日志文件
accesslog = "/data/gpa/log/gunicorn_access.log"
# 错误日志文件
errorlog = "/data/gpa/log/gunicorn_error.log"
# 进程号记录文件
pidfile = "/data/gpa/log/gunicorn.pid"
