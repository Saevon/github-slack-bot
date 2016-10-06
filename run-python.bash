#!/bin/bash

LOG_PATH=/var/log/
LOG_PREFIX=github-slack-bot
MERGED_LOG=${LOG_PATH}/${LOG_PREFIX}.log

ALL_LOGS="${MERGED_LOG}"

if [[ $1 =~ "--flush" ]]; then
	rm -f ${ALL_LOGS}
	exit 0
fi

# Get the date today
TODAY=$(date --iso-8601="seconds")

# Writes to a merged logfile, and separated logfiles
# Also writes to stdout/stderr
echo "LOGS: ${ALL_LOGS}"
echo "[${TODAY})] Starting WSGI"
PYTHONDONTWRITEBYTECODE=1 python bot.py >> ${MERGED_LOG} 2>&1
