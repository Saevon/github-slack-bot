#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import json

from slackclient import SlackClient


class SlackApi(object):

    def __init__(self, token, logger):
        self.api = SlackClient(token)
        self.logger = logger

    def get_users(self):
        response = self.api.api_call("users.list")

        if not response.get('ok'):
            if response.get('error') == 'invalid_auth':
                self.logger.error('ERROR: Slack Authentication is Invalid')
            else:
                self.logger.error("ERROR: {error}".format(
                    error=response.get('error'),
                ))
            return []

        # retrieve all users so we can find our bot
        users = response.get('members')

        return users

    def find_user(self, username):
        users = self.get_users()
        for user in users:
            if username == user.get("name"):
                return user

    def api_call(self, *args, **kwargs):
        return self.api.api_call(*args, **kwargs)

    def log_event(self, message):
        self.logger.info(message)

    def send_message(self, user, target, text=None, attachment=None):
        # See if we can summarize the attachment
        if attachment is None:
            fallback = ''
        else:
            fallback = attachment.get("fallback", attachment)

        # Log the event
        self.logger.info("{fallback}\n{message}".format(
            message=text,
            fallback=fallback,
        ))

        # Send the message
        self.api.api_call(
            "chat.postMessage",
            channel="@{username}".format(username=target.slack),
            text=text,
            attachments=json.dumps([attachment]),
            icon_url=user.avatar,
            username=user.name,
        )


