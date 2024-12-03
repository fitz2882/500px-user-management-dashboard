#!/bin/bash
rm -rf /etc/nginx/nginx.conf && cp nginx.conf /etc/nginx/ && cp nginx-app.conf /etc/nginx/conf.d/
/usr/sbin/nginx
exec python3 /application/app.py