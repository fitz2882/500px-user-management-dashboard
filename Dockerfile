FROM python:3.13-slim

WORKDIR /application

COPY requirements.txt ./

RUN apt update \
    && apt install -y nginx \
    && apt install -y build-essential \
    && pip install --upgrade setuptools \
    && pip install --no-cache-dir -r requirements.txt

COPY ./application entrypoint.sh ./

RUN rm -rf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/
COPY nginx-app.conf /etc/nginx/conf.d/

ENTRYPOINT ["./entrypoint.sh"]