#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import re
import json
import requests

import flask


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
    return set(GITHUB_MENTION.findall(text))


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

    @staticmethod
    def _find_hook(hooks, url):
        for hook in hooks:
            if hook["config"].get("url", False) == url:
                return hook
        return False


def webhook_server(events, logger):
    app = flask.Flask(__name__)
    app.logger.addHandler(logger)

    @app.route('/robots.txt', methods=['GET'])
    def robots():
        robots_txt = "User-agent: *\nDisallow: /\n"

        response = flask.make_response(robots_txt)
        response.headers["Content-Type"] = "text/plain"

        return response

    @app.route('/webhook', methods=['POST'])
    def event():
        # Get the json data
        if flask.request.is_json:
            data = flask.request.get_json()
        else:
            logger.warning("ERROR: Could not decode data\nQuerystring: {query}\nData: {data}".format(
                data=flask.request.data,
                query=json.dumps(flask.request.args),
            ))
            data = {}

        # Find out what event this is
        event = flask.request.headers.get('X-GitHub-Event', False)
        action = data.get('action', False)

        # We shouldn't have any other events...
        if data.get("hook", False) and data.get("hook_id", False):
            # The webhook got created
            return "OK"
        elif event is False:
            logger.warning("Unknown Event({event})\nHeaders: {headers}\nData: {data}\n".format(
                event=event,
                headers=json.dumps(dict(flask.request.headers.iteritems())),
                data=json.dumps(data),
            ))
            return "OK"

        # See if we have an event for this
        if action is False:
            callback = getattr(events, "on_{event}".format(action=action, event=event), False)
        else:
            callback = getattr(events, "on_{event}_{action}".format(action=action, event=event), False)

        if callback is not False:
            callback(data)
        else:
            logger.info("Unhandled Event: {event}:{action}".format(
                event=event,
                action="" if action is False else action
            ))

        return "OK"

    @app.route('/', methods=['GET'])
    def hello():
        return 'Hello this is the MajikBot\n'

    return app
