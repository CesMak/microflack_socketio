#!/bin/sh -e

# start service discovery task in the background
if [ "$SERVICE_URL" != "" ]; then
    python -c "from microflack_common.container import register; register()" &
fi

# run web server
exec gunicorn -b 0.0.0.0:5000 -k eventlet --access-logfile - --log-level debug --error-logfile gunicorn_error.log app:app
