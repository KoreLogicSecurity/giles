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
# Purpose: Provide a case-insensitive string class.
#
######################################################################

"""
This module provides the CaselessString class. A CaselessString works just like
a string, but ignores case for the purposes of hashing and comparisons. The
original casing of the string is preserved, meaning it still pretty-prints
nicely.

Some quick examples:

    >>> CS = CaselessString
    >>> S = CS("HELLO, WORLD!")
    >>> s = CS("hello, world!")
    >>> s == S
    True

    >>> d = {}
    >>> d[s] = "A message"
    >>> d[S]
    'A message'

    >>> S
    CaselessString('HELLO, WORLD!')
    >>> S.lower()
    CaselessString('hello, world!')
    >>> S
    CaselessString('HELLO, WORLD!')

    >>> "hello, world!" == S
    True
    >>> S == "hello, world!"
    True

    >>> s + " " + S
    CaselessString('hello, world! HELLO, WORLD!')
    >>> s + " " + S == "hello, world! HELLO, WORLD!"
    True
    >>> s + " " + S == "HeLlO, WoRlD! hElLo, WoRlD!"
    True

    >>> "h" in CaselessString("Hello, world!")
    True
    >>> "H" in CaselessString("hello, world!")
    True
    >>> "W" in CaselessString("hello, world!")
    True

    >>> "B" < "a"
    True
    >>> CaselessString("B") > CaselessString("a")
    True
    >>> CaselessString("B") < "a"
    False
    >>> "a" < CaselessString("B")
    True

CaselessString also overrides all of the various transforming str methods and
causes them to return a transformed CaselessString. More interestingly, it also
processes their arguments when necessary to remove casing. For example:

    >>> "AbCdE".strip("AB")
    'bCdE'
    >>> CaselessString("AbCdE").strip("AB")
    CaselessString('CdE')

    >>> S = CaselessString("HELLO, THIS IS THE WORLD!")
    >>> S.partition(" tHIs Is thE")
    (CaselessString('HELLO,'), CaselessString(' tHIs Is thE'), CaselessString(' WORLD!'))

    >>> s = "HELLO, THIS IS THE WORLD!"
    >>> s.partition(" THIS IS THE")
    ('HELLO,', ' THIS IS THE', ' WORLD!')

    >>> CaselessString("hello world").split()
    [CaselessString('hello'), CaselessString('world')]

    >>> CaselessString("Hello|This|Is|The|World").rsplit("|", maxsplit=2)
    [CaselessString('Hello|This|Is'), CaselessString('The'), CaselessString('World')]

    >>> "Hello|This|Is|The|World".rsplit("|", maxsplit=2)
    ['Hello|This|Is', 'The', 'World']
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2013-2014 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE"
__version__ = "$Id$"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import re


class CaselessString(str):

    """
    The CaselessString class implements a case-insensitive but case-preserving
    string that in general operates just like a normal string.
    """

    @classmethod
    def _add_methods(cls):
        def add_delegate1(method, delegate):
            def func(self, *args, **kwargs):
                return CaselessString(delegate(self._string, *args, **kwargs))
            setattr(cls, method, func)

        for method in ("capitalize", "casefold", "center", "encode", "expandtabs",
                       "__format__", "format", "format_map", "join", "ljust", "lower",
                       "lstrip", "rjust", "rstrip", "strip", "upper"):
            add_delegate1(method, getattr(str, method))

        def add_delegate2(method, delegate):
            def func(self, sub, start=0, end=None):
                if isinstance(sub, str) and isinstance(start, int) and (end is None or isinstance(end, int)):
                    if end is None:
                        end = len(self._folded)
                    return delegate(self._folded, sub.casefold(), start, end)
                return delegate(self._string, sub, start, end)
            setattr(cls, method, func)

        for method in ("count", "endswith", "find", "index", "rfind", "rindex", "startswith"):
            add_delegate2(method, getattr(str, method))

        def add_delegate3(method, delegate):
            def func(self, chars=None):
                if chars is None:
                    return CaselessString(delegate(self._string, chars))

                if not isinstance(chars, str):
                    return CaselessString(delegate(self._string, chars))

                chars += "".join([c.swapcase() for c in chars])
                return CaselessString(delegate(self._string, chars))
            setattr(cls, method, func)

        for method in ("lstrip", "rstrip", "strip"):
            add_delegate3(method, getattr(str, method))

    def __init__(self, string):
        self._add_methods()
        if isinstance(string, CaselessString):
            self._string = string._string
            self._folded = string._folded

        elif isinstance(string, str):
            self._string = str(string)
            self._folded = string.casefold()

        else:
            raise TypeError("string must be a str or CaselessString")

    def __add__(self, other):
        return CaselessString(self._string + other)

    def __contains__(self, c):
        if isinstance(c, str):
            return c.casefold() in self._folded
        return c in self._folded

    def __eq__(self, other):
        if isinstance(other, str):
            return self._folded == other.casefold()
        return self._string == other

    def __hash__(self):
        return hash(self._folded)

    def __len__(self):
        return len(self._string)

    ####################################################################
    #
    # Note that we don't use total_ordering from functools here because
    # we want to inherit from str, which defines those methods itself
    # and therefore total_ordering won't override them.
    #
    ####################################################################

    def __lt__(self, other):
        if isinstance(other, str):
            return self._folded < other.casefold()
        return self._string < other

    def __le__(self, other):
        if isinstance(other, str):
            return self._folded <= other.casefold()
        return self._string <= other

    def __gt__(self, other):
        if isinstance(other, str):
            return self._folded > other.casefold()
        return self._string > other

    def __ge__(self, other):
        if isinstance(other, str):
            return self._folded >= other.casefold()
        return self._string >= other

    def __mod__(self, other):
        return CaselessString(self._string % other)

    def __mul__(self, count):
        return CaselessString(self._string * count)

    def __ne__(self, other):
        if isinstance(other, str):
            return self._folded != other.casefold()
        return self._string != other

    def __radd__(self, other):
        return CaselessString(other + self._string)

    def __repr__(self):
        return "CaselessString('%s')" % str(self).replace("'", r"\'")

    def __rmod__(self, other):
        return CaselessString(str(other) % self._string)

    def __rmul__(self, other):
        return CaselessString(other * self._string)

    def __str__(self):
        return self._string

    def partition(self, sep):
        if not isinstance(sep, str) or len(sep) == 0:
            return self._string.partition(sep)

        index = self._folded.find(sep.casefold())
        if len(self._string) != len(self._folded) or len(sep) != len(sep.casefold()):
            return CaselessString(self._folded[0:index]), CaselessString(sep.casefold()), \
                CaselessString(self._folded[index + len(sep.casefold()):])

        else:
            return CaselessString(self._string[0:index]), CaselessString(sep), CaselessString(self._string[index + len(sep):])

    def replace(self, old, new, count=None):
        if not isinstance(old, str) or not isinstance(new, str) or (count is not None and not isinstance(count, int)):
            return CaselessString(self._string.replace(old, new, count))

        if count is None:
            count = 0

        return CaselessString(re.sub(re.escape(str(old)), str(new), self._string, count, re.I))

    def rpartition(self, sep):
        if not isinstance(sep, str) or len(sep) == 0:
            return self._string.partition(sep)

        index = self._folded.find(sep.casefold())
        if len(self._string) != len(self._folded) or len(sep) != len(sep.casefold()):
            return CaselessString(self._folded[0:index]), CaselessString(sep.casefold()), \
                CaselessString(self._folded[index + len(sep.casefold()):])

        else:
            return CaselessString(self._string[0:index]), CaselessString(sep), CaselessString(self._string[index + len(sep):])

    def rsplit(self, sep=None, maxsplit=-1):
        result = [CaselessString(x[::-1]) for x in re.split(re.escape(sep[::-1]) if sep is not None else r"\s+",
                                                            self._string[::-1], maxsplit if maxsplit > 0 else 0, flags=re.I) if len(x) > 0]
        result.reverse()
        return result

    def split(self, sep=None, maxsplit=-1):
        return [CaselessString(x) for x in re.split(re.escape(sep)
                if sep is not None else r"\s+", self._string, maxsplit if maxsplit > 0 else 0, flags=re.I) if len(x) > 0]

    def splitlines(self, *args):
        return [CaselessString(x) for x in str.splitlines(self._string, *args)]

    def translate(self, *args):
        return CaselessString(self._string.translate(*args))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
