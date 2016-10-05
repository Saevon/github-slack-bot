#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys

import time


def format(*args):
    '''
    Formats each output type, adding a date
    '''
    date = time.strftime("%Y-%m-%d %H:%M:%S")

    # Format each arg to a string
    text = ''
    for arg in args:
        try:
            text += unicode(arg)
        except UnicodeDecodeError:
            text += repr(arg)

    # Combine the final format
    text = "[{date}]: {text}".format(date=date, text=text)

    return text


def log(*args):
    '''
    Logs the data
    '''
    text = format(*args)
    sys.stdout.write(text + "\n")


def warn(*args):
    '''
    Warns the user about potential problems
    '''
    text = format(*args)
    sys.stdout.write(text + "\n")


def error(*args):
    '''
    Reports a problem in the app
    '''
    text = format(*args)
    sys.stderr.write(text + "\n")

