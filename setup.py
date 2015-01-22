#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id$
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
# Purpose: Set up and install Giles.
#
######################################################################

import os
import sys
from setuptools import setup

from giles import get_release_string

if sys.version_info < (3, 4, 0):
    print("Giles requires Python 3.4.0 or later.", file=sys.stderr)
    sys.exit(1)

setup(
    name="giles",
    version=get_release_string(),
    install_requires=['Jinja2>=2.7.3', 'PyYAML>=3.11'],
    license="Affero GNU General Public License",
    author="Rob King",
    author_email="rking@korelogic.com",
    maintainer="Rob King",
    maintainer_email="giles-project@korelogic.com",
    description="Giles is a compiler for production systems.",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    url="http://www.korelogic.com",
    packages=['giles'],
    package_data={'giles': ['*.jinja']},
    test_suite='tests.test_all',
    entry_points={
        'console_scripts': [
            'giles = giles.giles:main'
        ]
    }
)
