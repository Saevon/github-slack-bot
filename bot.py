#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys

import logging
import logging.config
import time
import threading

from github import GithubAPI, webhook_server, find_mentions
from slack import SlackApi
from user_mapping import UserMapping, UserAccount
import env


reload(sys)
sys.setdefaultencoding('utf-8')


class WebhookEvents(object):
    '''
    https://developer.github.com/webhooks/
    '''

    COLORS = {
        "pass": "#36a64f",
        "warn": "#b09000",
        "fail": "#E02020",
    }

    def __init__(self, slack, mapping, logger):
        self.slack = slack
        self.mapping = mapping
        self.logger = logger

    def on_mentions(self, slack_data):
        # Find any mentions
        mentions = find_mentions(slack_data.get("message"))
        for mention in mentions:
            # See if the user is listed
            user = self.mapping.get_user(github=mention)
            if user is None:
                self.logger.error("Unmapped user found: {user}".format(user=mention))

                # Not found, see if its a valid slack user
                if self.slack.find_user(mention) is None:
                    break

                # If it worked create a temporary mapping
                user = UserAccount(
                    name=mention,
                    github=mention,
                    slack=mention,
                )

            # Send individual mentions
            self.on_mention(slack_data, user)

    def on_mention(self, slack_data, mention):
        slack_data = slack_data.copy()
        slack_data["user"] = mention

        branch = slack_data.get("branch", False)
        if branch is False:
            slack_data["branch"] = ""

        #####################################
        # Formats to slack style
        attachment = {
            "fallback": "You've been Mentioned: {link}\nSender: {assigner}\nMentioned User: {user}\nRepo: {repo_name} {branch}\nSource: {source}".format(**slack_data),
            "color": self.COLORS["pass"],
            "title": "You've been mentioned in a {source}".format(**slack_data),
            "title_link": "{link}".format(**slack_data),
            "fields": [
                {
                    "title": "Repo",
                    "value": slack_data["repo_name"],
                    "short": True,
                }
            ],
            "footer": "Github Mention",

            # TODO: Hardcoded slack icon
            "footer_icon": "https://avatars.slack-edge.com/2016-09-30/86125165617_c717ddd0e0e41b6b2597_48.jpg",
        }

        # Not all things have a branch
        if branch is not False:
            attachment["fields"].append({
                "title": "Branch",
                "value": slack_data["branch"],
                "short": True,
            })

        #################################
        # Send a slack message
        self.slack.send_message(
            user=slack_data["assigner"],
            target=mention,
            text=slack_data["message"],
            attachment=attachment,
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
            "assigner": assigner,
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
            "assigner": assigner,
            "repo_name": repo_name,
            "source": "PR Comment",
        }

        # See if someone was mentioned
        self.on_mentions(slack_data)

    def on_pull_request_review_submitted(self, data):
        ###############################
        # Pulls our github info
        review = data.get("review")
        reviewer = self.mapping.get_user(
            github=review.get("user").get("login")
        )
        status = review.get("state")
        message = review.get("body")
        review_url = review.get("html_url")

        pr = data.get("pull_request")
        pr_message = pr.get("body")
        pr_branch = pr.get("head").get("ref")
        pr_url = pr.get("html_url")
        pr_title = pr.get("title")
        pr_number = pr.get("number")
        user = self.mapping.get_user(
            github=pr.get("user").get("login")
        )

        repo = pr.get("head").get("repo")
        repo_name = repo.get("full_name")

        #####################################
        # Filter out self comments
        if reviewer == user:
            return

        #####################################
        # Formats to slack style
        status_color = self.COLORS["warn"]
        status_message = "Updated"
        if status == "changes_requested":
            status_color = self.COLORS["fail"]
            status_message = "Changes Requested"
        elif status == "approved":
            status_color = self.COLORS["pass"]
            status_message = "Approved"
        elif status == "commented":
            status_color = self.COLORS["warn"]
            status_message = "Reviewed"

            # Sometimes this even fires if the user commented on a single line of code
            # In those cases the body is null
            # We want to ignore those, as another event should handle them
            if message is None:
                return

        attachment = {
            "fallback": "PR {status}: {link}\n{title} #{id}:\Review: {message}\nReviewer: {reviewer}\nRepo: {repo_name} {branch}".format(
                link=pr_url,
                title=pr_title,
                id=pr_number,
                reviewer=reviewer,
                user=user,
                repo_name=repo_name,
                branch=pr_branch,
                status=status_message,
                message=message,
            ),
            "color": status_color,
            "title": "PR {status} ({title} #{id})".format(
                id=pr_number,
                title=pr_title,
                status=status_message,
            ),
            "title_link": "{link}".format(link=review_url),
            "text": message,
            "fields": [
                {
                    "title": "Pull Request",
                    "value": "{repo_name}@{branch}".format(repo_name=repo_name, branch=pr_branch),
                    "short": True,
                },
                {
                    "title": "Repo",
                    "value": "{repo_name}@{branch}".format(repo_name=repo_name, branch=pr_branch),
                    "short": True,
                },
            ],
            "footer": "Github PR {status}".format(status=status_message),

            # TODO: Hardcoded slack icon
            "footer_icon": "https://avatars.slack-edge.com/2016-09-30/86125165617_c717ddd0e0e41b6b2597_48.jpg",
        }

        #################################
        # Send a slack message
        self.slack.send_message(
            user=reviewer,
            target=user,
            text="",
            attachment=attachment,
        )



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
            "assigner": assigner,
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
            "assigner": assigner,
            "repo_name": repo_name,
            "source": "Opened PR Description",
        }

        # See if someone was mentioned
        self.on_mentions(slack_data)

    def on_pull_request_review_requested(self, data):
        ###############################
        # Pulls our github info
        user = self.mapping.get_user(
            github=data.get("requested_reviewer").get("login")
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
            "fallback": "PR Review Requested: {link}\n{title} #{id}: {message}\nAssigned By: {assigner}\nAssigned To: {user}\nRepo: {repo_name} {branch}".format(
                link=pr_url,
                title=pr_title,
                id=pr_number,
                message=pr_message,
                assigner=assigner,
                user=user,
                repo_name=repo_name,
                branch=pr_branch,
            ),
            "color": self.COLORS["pass"],
            "title": "{title} #{id} needs a review".format(id=pr_number, title=pr_title),
            "title_link": "{link}".format(link=pr_url),
            "text": pr_message,
            "fields": [
                {
                    "title": "Repo",
                    "value": "{repo_name}@{branch}".format(repo_name=repo_name, branch=pr_branch),
                    "short": True,
                },
                {
                    "title": "Assigned By",
                    "value": assigner.name,
                    "short": True,
                },
            ],
            "footer": "Github PR Review Request",

            # TODO: Hardcoded slack icon
            "footer_icon": "https://avatars.slack-edge.com/2016-09-30/86125165617_c717ddd0e0e41b6b2597_48.jpg",
        }

        #################################
        # Send a slack message
        self.slack.send_message(
            user=assigner,
            target=user,
            text="",
            attachment=attachment,
        )

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
                assigner=assigner,
                user=user,
                repo_name=repo_name,
                branch=pr_branch,
            ),
            "color": self.COLORS["pass"],
            "title": "{title} #{id} has been assigned to you".format(id=pr_number, title=pr_title),
            "title_link": "{link}".format(link=pr_url),
            "text": pr_message,
            "fields": [
                {
                    "title": "Repo",
                    "value": "{repo_name}@{branch}".format(repo_name=repo_name, branch=pr_branch),
                    "short": True,
                },
                {
                    "title": "Assigned By",
                    "value": assigner.name,
                    "short": True,
                },
            ],
            "footer": "Github PR Assigned",

            # TODO: Hardcoded slack icon
            "footer_icon": "https://avatars.slack-edge.com/2016-09-30/86125165617_c717ddd0e0e41b6b2597_48.jpg",
        }

        #################################
        # Send a slack message
        self.slack.send_message(
            user=assigner,
            target=user,
            text="",
            attachment=attachment,
        )


def heartbeat(logger, seconds):
    while True:
        logger.info("Hearbeat")
        time.sleep(seconds)


def setup():
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
    slack_client = SlackApi(env.SLACK["TOKEN"], slack_logger)
    events = WebhookEvents(slack_client, mapping, slack_logger)

    github_logger = logging.getLogger('listener')
    application = webhook_server(events, github_logger)

    # Log Status
    main_logger.info('Started')

    return application


if __name__ == "__main__":
    app = setup()
    app.run(port=8080, host="0.0.0.0")
