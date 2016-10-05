#!/bin/bash

LOG_PATH=/var/log/
LOG_PREFIX=github-slack-bot
MERGED_LOG=${LOG_PATH}/${LOG_PREFIX}.log

ALL_LOGS="${MERGED_LOG}"

if [[ $1 =~ "--flush" ]]; then
	rm -f ${ALL_LOGS}
	exit 0
fi

# Writes to a merged logfile, and separated logfiles
# Also writes to stdout/stderr
echo "LOGS: ${ALL_LOGS}"
python bot.py >> ${MERGED_LOG} 2>&1
