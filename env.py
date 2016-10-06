
SERVER_IP = ""


HEARTBEAT_DURATION = 30 * 60

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(process)d %(thread)d %(message)s',
        },
        'simple': {
            'format': '[%(asctime)s] @%(levelname)s %(message)s',
        },
    },
    'filters': {

    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # 'file': {
        #     'level': 'DEBUG',
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'filename': '/var/www/github-slack-bot/logs/main.log',
        #     'mode': 'a',
        #     'maxBytes': 10 * 1024 * 1024,
        #     'backupCount': 20,
        #     'formatter': 'verbose',
        # },
    },
    'loggers': {
        # Default logger
        '': {
            'handlers': ['console'],
            # 'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    }
}

SLACK = {
    "TOKEN": "",
    "BOT_ID": "",
}


GITHUB = {
    "ENDPOINT": "https://api.github.com",
    "TOKEN": "",
    "BOT_URL": SERVER_IP,
}

REPOS = {
}

USER_MAPPING = [
]
