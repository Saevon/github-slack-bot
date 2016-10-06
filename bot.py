#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys

from slackclient import SlackClient
import json
import logging
import logging.config
import time
import threading

from github import GithubAPI, webhook_server, find_mentions
import env

reload(sys)
sys.setdefaultencoding('utf-8')


def get_users(api):
    response = api.api_call("users.list")

    if not response.get('ok'):
        if response.get('error') == 'invalid_auth':
            error('ERROR: Slack Authentication is Invalid')
        else:
            error("ERROR: {error}".format(error=response))
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

        user = self.format_user(name, github, slack)

        self.users[name.lower()] = user

        self.slacks[slack.lower()] = name
        self.githubs[github.lower()] = name

        return user

    def format_user(self, name, github=None, slack=None):
        return {
            "github": github,
            "slack": slack,
            "name": name,
        }

    def get_user(self, name=None, github=None, slack=None):
        '''
        Finds a user by one of the valid keys
        '''
        if github is not None:
            name = self.githubs.get(github.lower())
        if slack is not None:
            name = self.slacks.get(slack.lower())

        if name is None:
            return None

        user = self.users.get(name.lower(), None)
        if user is None:
            user = {
                "name": name,
                "github": github,
                "slack": slack,
            }

        return user


class WebhookEvents(object):
    '''
    https://developer.github.com/webhooks/
    '''

    def __init__(self, slack, mapping, logger):
        self.slack = slack
        self.mapping = mapping
        self.logger = logger

    def log_event(self, message):
        self.logger.info(message)

    def on_mentions(self, slack_data):
        # Find any mentions
        mentions = find_mentions(slack_data.get("message"))
        for mention in mentions:
            # See if the user is listed
            user = self.mapping.get_user(github=mention)
            if user is None:
                error("Unmapped user found: {user}".format(user=user))

                # Not found, see if its a valid slack user
                if find_user(self.slack, mention) is None:
                    break
                # If it worked create a temporary mapping
                user = self.mapping.format_user(user)

            # Send individual mentions
            self.on_mention(slack_data, user)

    def on_mention(self, slack_data, mention):
        slack_data = slack_data.copy()
        slack_data["user"] = mention["name"]

        branch = slack_data.get("branch", False)
        if branch is False:
            slack_data["branch"] = ""

        #####################################
        # Formats to slack style
        attachment = {
            "fallback": "You've been Mentioned: {link}\n{message}\nSender: {assigner}\nMentioned User: {user}\nRepo: {repo_name} {branch}\nSource: {source}".format(**slack_data),
            "color": "#36a64f",
            "title": "You've been mentioned in a {source}".format(**slack_data),
            "title_link": "{link}".format(**slack_data),
            "text": "{message}".format(**slack_data),
            "fields": [
                {
                    "title": "Repo",
                    "value": slack_data["repo_name"],
                    "short": False,
                },
                {
                    "title": "Sender",
                    "value": slack_data["assigner"],
                    "short": False,
                },
            ],
            # "image_url": "http://my-website.com/path/to/image.jpg",
            # "thumb_url": "http://example.com/path/to/thumb.png",
            "footer": "Github Mention",
            # "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            # "ts": 123456789
        }

        # Not all things have a branch
        if branch is not False:
            attachment["fields"].append({
                "title": "Branch",
                "value": slack_data["branch"],
                "short": False,
            })

        ##################################
        # Log the event
        self.log_event(attachment["fallback"])

        #################################
        # Send a slack message
        slack_username = mention["slack"]

        self.slack.api_call(
            "chat.postMessage",
            channel="@{username}".format(username=slack_username),
            text="",
            attachments=json.dumps([attachment]),
            username="majbot",
        )

    ####################################################################
    # Github Events

    def on_commit_comment_created(self, data):
        ###############################
        # Pulls our github info
        assigner = self.mapping.get_user(
            github=data.get("sender").get("login")
        )

        comment = data.get("comment")
        comment_url = comment.get("html_url")
        message = comment.get("body")

        repo = data.get("repository")
        repo_name = repo.get("full_name")

        slack_data = {
            "message": message,
            "link": comment_url,
            "assigner": assigner["name"],
            "repo_name": repo_name,
            "source": "Commit",
        }

        # See if someone was mentioned
        self.on_mentions(slack_data)

    def on_issue_comment_created(self, data):
        return self.on_issue_comment(data)

    def on_issue_comment_edited(self, data):
        return self.on_issue_comment(data)

    def on_issue_comment(self, data):
        ###############################
        # Pulls our github info
        assigner = self.mapping.get_user(
            github=data.get("sender").get("login")
        )

        # Some issues are also a PR
        pr = data.get("pull_request", False)
        if pr:
            branch = pr.get("head").get("ref")
        else:
            branch = False

        comment = data.get("comment")
        comment_url = comment.get("html_url")
        message = comment.get("body")

        repo = data.get("repository")
        repo_name = repo.get("full_name")

        slack_data = {
            "message": message,
            "link": comment_url,
            "assigner": assigner["name"],
            "repo_name": repo_name,
            "source": "PR Comment",
        }

        # See if someone was mentioned
        self.on_mentions(slack_data)

    def on_pull_request_review_comment_edited(self, data):
        return self.on_pull_request_review_comment(data)

    def on_pull_request_review_comment_created(self, data):
        return self.on_pull_request_review_comment(data)

    def on_pull_request_review_comment(self, data):
        ###############################
        # Pulls our github info
        assigner = self.mapping.get_user(
            github=data.get("sender").get("login")
        )

        pr = data.get("pull_request")
        pr_title = pr.get("title")
        pr_branch = pr.get("head").get("ref")

        comment = data.get("comment")
        comment_url = comment.get("html_url")
        message = comment.get("body")

        repo = data.get("repository")
        repo_name = repo.get("full_name")

        slack_data = {
            "message": message,
            "link": comment_url,
            "branch": pr_branch,
            "assigner": assigner["name"],
            "repo_name": repo_name,
            "source": "PR Review",
        }

        # See if someone was mentioned
        self.on_mentions(slack_data)

    def on_pull_request_opened(self, data):
        ###############################
        # Pulls our github info
        assigner = self.mapping.get_user(
            github=data.get("sender").get("login")
        )

        pr = data.get("pull_request")
        pr_message = pr.get("body")
        pr_branch = pr.get("head").get("ref")
        pr_url = pr.get("html_url")

        repo = data.get("repository")
        repo_name = repo.get("full_name")

        slack_data = {
            "message": pr_message,
            "link": pr_url,
            "assigner": assigner["name"],
            "repo_name": repo_name,
            "source": "Opened PR Description",
        }

        # See if someone was mentioned
        self.on_mentions(slack_data)

    def on_pull_request_assigned(self, data):
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
        pr_title = pr.get("title")
        pr_number = pr.get("number")

        repo = data.get("repository")
        repo_name = repo.get("full_name")

        #####################################
        # Formats to slack style
        attachment = {
            "fallback": "PR Assigned: {link}\n{title} #{id}: {message}\nAssigned By: {assigner}\nAssigned To: {user}\nRepo: {repo_name} {branch}".format(
                link=pr_url,
                title=pr_title,
                id=pr_number,
                message=pr_message,
                assigner=assigner["name"],
                user=user,
                repo_name=repo_name,
                branch=pr_branch,
            ),
            "color": "#36a64f",
            # "author_name": "{assigner}".format(assigner=assigner["name"]),
            # "author_link": "http://flickr.com/bobby/",
            # "author_icon": "http://flickr.com/icons/bobby.jpg",
            # "pretext": "Optional text that appears above the attachment block",
            "title": "{title} #{id} has been assigned to you".format(id=pr_number, title=pr_title),
            "title_link": "{link}".format(link=pr_url),
            "text": pr_message,
            "fields": [
                {
                    "title": "Repo",
                    "value": "{repo_name}@{branch}".format(repo_name=repo_name, branch=pr_branch),
                    "short": False,
                },
                {
                    "title": "Assigned By",
                    "value": assigner["name"],
                    "short": False,
                },
            ],
            # "image_url": "http://my-website.com/path/to/image.jpg",
            # "thumb_url": "http://example.com/path/to/thumb.png",
            "footer": "Github PR",
            # "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            # "ts": 123456789
        }

        ##################################
        # Log the event
        self.log_event(attachment["fallback"])

        #################################
        # Send a slack message
        slack_username = user["slack"]

        self.slack.api_call(
            "chat.postMessage",
            channel="@{username}".format(username=slack_username),
            text="",
            attachments=json.dumps([attachment]),
            username="majbot",
        )


def heartbeat(logger, seconds):
    while True:
        logger.info("Hearbeat")
        time.sleep(seconds)


def setup():
    slack_client = SlackClient(env.SLACK["TOKEN"])

    logging.config.dictConfig(env.LOGGING)
    main_logger = logging.getLogger('')

    # Enable the heartbeat
    if env.HEARTBEAT_DURATION >= 1:
        heartbeat_logger = logging.getLogger('heartbeat')
        heartbeat_thread = threading.Thread(target=heartbeat, kwargs={
            "logger": heartbeat_logger,
            "seconds": env.HEARTBEAT_DURATION,
        })
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

    # Start the server
    slack_logger = logging.getLogger('messenger')
    mapping = UserMapping(env.USER_MAPPING)
    events = WebhookEvents(slack_client, mapping, slack_logger)

    github_logger = logging.getLogger('listener')
    application = webhook_server(events, github_logger)

    # Log Status
    main_logger.info('Started')

    return application


if __name__ == "__main__":
    app = setup()
    app.run(port=8080, host="0.0.0.0")
