#!/bin/bash

LOG_PATH=/var/www/github-slack-bot/logs/
LOG_PREFIX=wsgi
WSGI_LOG=${LOG_PATH}/${LOG_PREFIX}.log

ALL_LOGS="${WSGI_LOG}"

if [[ $1 =~ "--flush" ]]; then
    rm -f ${ALL_LOGS}
    exit 0
fi

# Writes to a merged logfile, and separated logfiles
# Also writes to stdout/stderr
echo "LOGS: ${ALL_LOGS}"
uwsgi --ini wsgi.ini --strict >> "${WSGI_LOG}" 2>&1
