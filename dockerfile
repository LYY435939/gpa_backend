FROM python:3.8
RUN groupadd -g 1001 product && \
    useradd -r -m -u 1001 -g product product
RUN mkdir -p /data/gpa
RUN mkdir -p /data/gpa/log
RUN chown -R product /data && chgrp -R product /data
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
RUN pip config set install.trusted-host mirrors.aliyun.com
WORKDIR /data/gpa
ADD requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ADD . .
ENV DJANGO_SETTINGS_MODULE=gpa.settings
EXPOSE 8000
RUN chmod u+x ./run.sh
ENTRYPOINT /bin/bash ./run.sh