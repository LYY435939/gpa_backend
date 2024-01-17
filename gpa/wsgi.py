"""
WSGI config for gpa project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from apscheduler.schedulers.background import BackgroundScheduler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gpa.settings')

application = get_wsgi_application()

scheduler = BackgroundScheduler()


# 定时任务, 清空session数据库,这个库不清的话,会不停的增大
# days为int值，几天一清理
# start_date开始日期
@scheduler.scheduled_job(trigger='interval', days=1, start_date='2023-03-15 10:00:00', id='clear_session')
def clear_session_job():
    print('clear session data base')
    os.system('python manage.py clearsessions')


scheduler.start()
