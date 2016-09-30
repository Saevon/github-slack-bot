#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys

from github import GithubAPI, webhook_server

from env import *

from slackclient import SlackClient
import json

reload(sys)
sys.setdefaultencoding('utf-8')


def get_users(api):
    response = api.api_call("users.list")

    if not response.get('ok'):
        if response.get('error') == 'invalid_auth':
            sys.stderr.write('ERROR: Slack Authentication is Invalid\n')
        else:
            sys.stderr.write("ERROR: {error}\n".format(error=response))
        return []

    # retrieve all users so we can find our bot
    users = response.get('members')

    return users


def find_user(api, username):
    users = get_users(api)
    for user in users:
        if username == user.get("name"):
            return user


class UserMapping(object):

    def __init__(self, default=None):
        self.users = {}
        self.slacks = {}
        self.githubs = {}

        if default is not None:
            for user in default:
                self.add_user(**user)

    def add_user(self, name, github=None, slack=None):
        if github is None:
            github = name
        if slack is None:
            slack = name

        self.users[name] = {
            "github": github,
            "slack": slack,
            "name": name,
        }

        self.slacks[slack] = name
        self.githubs[github] = name

    def get_user(self, name=None, github=None, slack=None):
        '''
        Finds a user by one of the valid keys
        '''
        if github is not None:
            name = self.githubs.get(github)
        if slack is not None:
            name = self.slacks.get(slack)

        if name is not None:
            return self.users.get(name)



class WebhookEvents(object):

    def __init__(self, slack, mapping):
        self.slack = slack
        self.mapping = mapping

    def on_unassigned(self, data):
        pass

    def on_assigned(self, data):
        user_type = data.get("assignee").get("type")
        if user_type.lower() != "user":
            return

        ###############################
        # Pulls our github info
        user = self.mapping.get_user(
            github=data.get("assignee").get("login")
        )
        assigner = self.mapping.get_user(
            github=data.get("sender").get("login")
        )

        pr = data.get("pull_request")
        pr_message = pr.get("body")
        pr_branch = pr.get("head").get("ref")
        pr_url = pr.get("html_url")

        repo = data.get("repository")
        repo_name = repo.get("full_name")

        #####################################
        # Formats to slack style
        attachment = {
            "fallback": "PR Assigned: {link}: {message}\nAssigned By: {assigner}\nRepo: {repo_name}".format(
                link=pr_url,
                message=pr_message,
                assigner=assigner["name"],
                repo_name=repo_name,
            ),
            "color": "#36a64f",
            "author_name": "{assigner}".format(assigner=assigner["name"]),
            # "author_link": "http://flickr.com/bobby/",
            # "author_icon": "http://flickr.com/icons/bobby.jpg",
            # "pretext": "Optional text that appears above the attachment block",
            "title": "PR Assigned",
            "title_link": "{link}".format(link=pr_url),
            "text": pr_message,
            "fields": [
                {
                    "title": "Repo",
                    "value": repo_name,
                    "short": False,
                },
                {
                    "title": "Assigned By",
                    "value": assigner["name"],
                    "short": False,
                },
            ],
            "image_url": "http://my-website.com/path/to/image.jpg",
            "thumb_url": "http://example.com/path/to/thumb.png",
            "footer": "Github PR",
            "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            "ts": 123456789
        }

        ##################################
        # Log the event
        print(attachment["fallback"])

        #################################
        # Send a slack message
        slack_username = user["slack"]
        user = find_user(self.slack, slack_username)

        self.slack.api_call(
            "chat.postMessage",
            channel="@{username}".format(username=slack_username),
            text="",
            attachments=json.dumps([attachment]),
            username="majbot",
        )


if __name__ == "__main__":
    slack_client = SlackClient(SLACK["TOKEN"])

    # Prep the Webhooks
    for user, repos in REPOS.iteritems():
        for repo in repos:
            github = GithubAPI(
                user=user,
                token=GITHUB["TOKEN"],
                endpoint=GITHUB["ENDPOINT"]
            )
            enabled = github.check_hook(repo, SERVER_IP)
            if not enabled:
                github.create_hook(repo, SERVER_IP)
            print("Enabled Hook: {user}/{repo}".format(repo=repo, user=user))

    # Start the server
    mapping = UserMapping(USER_MAPPING)
    events = WebhookEvents(slack_client, mapping)
    webhook_server(events)



