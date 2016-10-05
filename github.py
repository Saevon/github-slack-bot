#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from flask import Flask, request

import json
import re
import requests
import sys


reload(sys)
sys.setdefaultencoding('utf-8')


GITHUB_MENTION = re.compile(
    # Start with a non-word-boundary (ensuring the part before this can't be a word)
    # Followed by an @ (ensuring emails should work)
    r'(?:\B@)'

    # Followed by the username itself
    r'(?P<username>'
        # It must start with an alphanumeric
        r'[a-z0-9]'
        # Followed by a dash or alphanumeric
        # But the dash must always be followed by an alphanumeric char (if it exists)
        r'(?:-?[a-z0-9])'

        # The length of the name is 39 Char: 1 starting char and 38 of the following ones
        r'{0,38}'
    r')'

    # Then ensure there's a word boundary after as well
    r'(?=\b)'

    r'',
    re.IGNORECASE
)


def find_mentions(text):
    return GITHUB_MENTION.findall(text)


class GithubAPI(object):

    def __init__(self, user, token, endpoint):
        self.__user = user
        self.__token = token
        self.__endpoint = endpoint

    @property
    def auth_headers(self):
        return {
            "Authorization": "token {token}".format(token=self.__token),
        }

    def create_hook(self, repo, target):
        payload = {
            "name": "web",
            "config": {
                "url": target,
                "content_type": "json"
            },
            "events": [
                "pull_request",
            ],
            "active": True,
        }

        response = requests.post(
            self.__endpoint + "/repos/{user}/{repo}/hooks".format(user=self.__user, repo=repo),
            headers=self.auth_headers,
            data=json.dumps(payload),
        )

        content = json.loads(response.content)

        if response.status_code not in [200, 201]:
            raise BaseException(response.status_code, content["message"], content["errors"])

    def list_hooks(self, repo):
        response = requests.get(
            self.__endpoint + "/repos/{user}/{repo}/hooks".format(user=self.__user, repo=repo),
            headers=self.auth_headers
        )

        if response.status_code != 200:
            raise BaseException(response.status_code)

        return json.loads(response.content)

    def check_hook(self, repo, url):
        hooks = self.list_hooks(repo)
        hook = self._find_hook(hooks, url)

        return bool(hook)

    def _find_hook(self, hooks, url):
        for hook in hooks:
            if hook["config"].get("url", False) == url:
                return hook
        return False


def webhook_server(events, logger):
    app = Flask(__name__)
    app.logger.addHandler(logger)

    @app.route('/', methods=['POST'])
    def event():
        # Get the json data
        try:
            data = json.loads(request.data)
        except ValueError:
            logger.warning("ERROR: Could not decode data")
            logger.warning(request.args, request.data)
            data = {}

        # Find out what event this is
        event = request.headers.get('X-GitHub-Event')
        action = data.get('action', False)

        # We shouldn't have any other events...
        if data.get("hook", False) and data.get("hook_id", False):
            # The webhook got created
            return "OK"
        elif event is False:
            logger.warning("====================")
            logger.warning("Unknown Event({event})".format(event=event))
            logger.warning("Headers: ", json.dumps(dict(request.headers.iteritems())))
            logger.warning(json.dumps(data))
            logger.warning("====================")
            return "OK"

        # See if we have an event for this
        if action is False:
            callback = getattr(events, "on_{event}".format(action=action, event=event), False)
        else:
            callback = getattr(events, "on_{event}_{action}".format(action=action, event=event), False)

        if callback is not False:
            callback(data)
        else:
            logger.info("Unhandled Event: {event}:{action}".format(event=event, action=action))

        return "OK"

    @app.route('/', methods=['GET'])
    def hello():
        return 'Hello this is the MajikBot\n'

    return app

