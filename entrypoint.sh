#!/bin/bash
nginx
exec python3 app.py & exec python3 scheduler.py