FROM ubuntu

WORKDIR /application/

COPY . /application/

RUN apt update \
    && apt install -y nginx \
    && apt install -y pip \
    && pip install -r requirements.txt --break-system-packages

CMD sh run.sh