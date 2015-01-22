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
# Purpose: Run tests.
#
######################################################################

"""
__init__.py - run tests
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2013 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE"
__version__ = "$Id$"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import doctest
import glob
import os
import os.path
import re
import sqlite3
import unittest

from giles.giles import main
from giles import caseless_string
from giles import forbidden_names
from giles import pyre
from giles import validate


class GilesCompilationTestCase(unittest.TestCase):

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.output_path = "{0}.sql".format(self.path)

    def __str__(self):
        return "Compiling example engine {1}".format(str(self.__class__), self.path)

    def runTest(self):
        with self.assertRaises(SystemExit) as cm:
            main("-r", "-c", "-o", self.output_path, self.path)

        self.assertEqual(cm.exception.code, 0, "compilation failed")

        with open(self.output_path, "r") as schema_file:
            schema = schema_file.read()
            schema_file.close()
            self.assertTrue(len(schema) > 0, "compilation produced no output")

            db = sqlite3.connect(":memory:")
            db.create_function("regexp", 2, lambda x, y: re.search(x, y))
            cursor = db.cursor()

            self.assertTrue(cursor.executescript(schema))

            cursor.close()
            db.close()


def test_all():
    suite = unittest.TestSuite()
    suite.addTests(doctest.DocTestSuite(caseless_string))
    suite.addTests(doctest.DocTestSuite(forbidden_names))
    suite.addTests(doctest.DocTestSuite(pyre))
    suite.addTests(doctest.DocTestSuite(validate))

    for example in glob.glob(os.path.join(os.getcwd(), "examples", "*", "*.yml")):
        suite.addTest(GilesCompilationTestCase(example))

    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(test_all())
