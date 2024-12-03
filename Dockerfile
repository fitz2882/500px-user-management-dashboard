FROM ubuntu:24.04

WORKDIR /application/

COPY ./application requirements.txt start.sh /application/

RUN apt update \
    && apt install -y nginx \
    && apt install -y pip \
    && pip install -r requirements.txt --break-system-packages

RUN rm -rf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/
COPY nginx-app.conf /etc/nginx/conf.d/

CMD sh start.sh