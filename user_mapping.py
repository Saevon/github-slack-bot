#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import collections


class UserAccount(collections.Mapping):

    VALID_KEYS = [
        "github",
        "name",
        "slack",
        "github_avatar",
        "avatar",
    ]

    def __init__(self, name, github=None, slack=None):
        self.__github = github
        self.__slack = slack

        self.name = name

    @property
    def github(self):
        if self.__github is None:
            return self.name
        return self.__github

    @property
    def slack(self):
        if self.__slack is None:
            return self.name
        return self.__slack

    @property
    def github_avatar(self):
        if self.__github is None:
            raise KeyError

        return "https://github.com/{github}.png".format(
            github=self.__github,
        )

    @property
    def avatar(self):
        return self.github_avatar

    def __getitem__(self, key):
        if key in self.VALID_KEYS:
            return getattr(self, key)
        raise KeyError

    def __iter__(self):
        for key in self.VALID_KEYS:
            yield key

    def __len__(self):
        return len(list(iter(self)))

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return unicode(self)

    ############################
    # Comparison

    def __eq__(self, other):
        return self.name == other.name


class UserMapping(object):

    def __init__(self, default=None):
        self.users = {}
        self.slacks = {}
        self.githubs = {}

        if default is not None:
            for user in default:
                self.add_user(**user)

    def add_user(self, name, github=None, slack=None):
        user = UserAccount(
            name=name,
            github=github,
            slack=slack,
        )

        self.users[user.name.lower()] = user

        self.slacks[user.slack.lower()] = user.name
        self.githubs[user.github.lower()] = user.name

        return user

    def get_user(self, name=None, github=None, slack=None):
        '''
        Finds a user by one of the valid keys
        '''

        # See if we can find the name by its aliases
        if github is not None:
            name = self.githubs.get(github.lower())
        elif slack is not None:
            name = self.slacks.get(slack.lower())

        # See if we know the name now
        if name is None:
            return None

        # Grab the user
        user = self.users.get(name.lower(), None)
        if user is None:
            # In the worst case just return an approximation
            # BUT we don't add the user to our mapping
            user = UserAccount(
                name=name,
                github=github,
                slack=slack,
            )

        return user

