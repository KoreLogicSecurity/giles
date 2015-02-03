#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id: 940adaad860d92313516fc25c783ad0123010d7f $
#
######################################################################
#
# Copyright 2011-2014 KoreLogic, Inc. All Rights Reserved.
#
# This software, having been partly or wholly developed and/or
# sponsored by KoreLogic, Inc., is hereby released under the terms
# and conditions set forth in the project's "README.LICENSE" file.
# For a list of all contributors and sponsors, please refer to the
# project's "README.CREDITS" file.
#
######################################################################
#
# Purpose: The Giles Package
#
######################################################################

"""
__init__.py - package implementation
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2013 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE"
__version__ = "$Id: 940adaad860d92313516fc25c783ad0123010d7f $"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

######################################################################
#
# Version
#
######################################################################

version = 0x30001800


def get_release_number():
    """Return the current release version."""

    return version


def get_release_string():
    """Return the current release version."""
    major = (version >> 28) & 0x0f
    minor = (version >> 20) & 0xff
    patch = (version >> 12) & 0xff
    state = (version >> 10) & 0x03
    build = version & 0x03ff
    if state == 0:
        state_string = "ds"
    elif state == 1:
        state_string = "rc"
    elif state == 2:
        state_string = "sr"
    elif state == 3:
        state_string = "xs"
    if state == 2 and build == 0:
        return '%d.%d.%d' % (major, minor, patch)
    else:
        return '%d.%d.%d.%s%d' % (major, minor, patch, state_string, build)
