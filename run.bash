#!/bin/bash

LOG_PATH=/var/www/github-slack-bot/logs/
WSGI_LOG=${LOG_PATH}/wsgi.log
DEV_LOG=${LOG_PATH}/dev.log


ALL_LOGS="main.log wsgi.log dev.log nginx.access.log nginx.error.log"


if [[ $1 =~ "--flush" ]]; then
    rm -f ${ALL_LOGS}
    exit 0
elif [[ $1 =~ "--mark-logs" ]]; then
    for logfile in ${ALL_LOGS}; do
        logfile=${LOG_PATH}/${logfile}
        if [ -s "${logfile}" ]; then
            printf "\n------------------------\n\n" >> "${logfile}"
        fi
    done
    exit 0
fi

# Get the date today
TODAY=$(date --iso-8601="seconds")


# Find out how we're running this
if [[ $1 =~ "wsgi" ]]; then
    NAME="WSGI"
    cmd="uwsgi --ini wsgi.ini --strict"
    LOG=${WSGI_LOG}
elif [[ $1 =~ "dev" ]]; then
    NAME="Dev Server"
    cmd="python bot.py"
    LOG=${DEV_LOG}
else
    1>&2 echo "Enter which server should we start [wsgi|dev]"
    exit 1
fi


# Writes to a logfile and to stdout/stderr
echo "LOGS: ${ALL_LOGS}"
echo "[${TODAY}] Starting ${NAME}"
PYTHONDONTWRITEBYTECODE=1 ${cmd} >> "${LOG}" 2>&1
