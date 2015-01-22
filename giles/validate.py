#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id: 12aa7938934929a1a4ba7bee92bcdceb8c9e391f $
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
# Purpose: Validate data structures against a schema.
#
######################################################################

"""
validate - Validate Arbitrary Datastructures

This module provides a set of combinators that can be used to validate data
structures of arbitrary shape and size. For example:

    >>> validator = Dictionary(
    ...   required = {
    ...     "First" : String(min_length=1, max_length=22),
    ...     "Last"  : String(min_length=1, max_length=22),
    ...   },
    ...   optional = {
    ...     "Middle" : String(min_length=1, max_length=22),
    ...   },
    ...   case_sensitive=False
    ... )
    >>> validator({"first" : "Rob", "LAST" : "King"}) is not None
    True
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2014 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE."
__version__ = "$Id: 12aa7938934929a1a4ba7bee92bcdceb8c9e391f $"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import collections
from giles.caseless_string import CaselessString as CS


class ValidationException(Exception):

    def __init__(self, message="Invalid data", expected=None, actual=None, location="???"):
        super().__init__(message)

        self.message = message
        self.expected = expected
        self.actual = actual
        self.location = location

    def __str__(self):
        return "%s: %s\nExpected: %s\nActual: %s" % (self.location, self.message, self.expected, self.actual)


class Validator:

    """The Validator class is the superclass of all validators."""

    def __call__(self, obj):
        return obj

    def __str__(self):
        return repr(self)


class All(Validator):

    """Validate a structure against multiple predicates, matching all of
    them."""

    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, obj, location="/"):
        for validator in self.validators:
            validator(obj, location)

        return obj

    def __repr__(self):
        return "All(%s)" % ", ".join(str(x) for x in self.validators)


class Any(Validator):

    """Validate a structure against multiple predicates, matching at least one
    of them."""

    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, obj, location="/"):
        exceptions = []
        for validator in self.validators:
            try:
                return validator(obj, location)

            except Exception as e:
                exceptions.append(e)

        raise ValidationException(" and ".join([x.message for x in exceptions]), str(self), obj, location)

    def __repr__(self):
        return "Any(%s)" % ", ".join(str(x) for x in self.validators)


class Boolean(Validator):

    """Validate a structure as a boolean value."""

    def __init__(self, value=None):
        self.value = value

    def __call__(self, obj, location="/"):
        if not isinstance(obj, bool):
            raise ValidationException("Expected a boolean value", bool, type(obj), location)

        if self.value is not None:
            if self.value != obj:
                raise ValidationException("Expected a specific boolean value", self.value, obj, location)

        return obj


class Not(Validator):

    """Validate a structure by specifying what it shouldn't be."""

    def __init__(self, other, message):
        self.other = other
        self.message = message

    def __call__(self, obj, location="/"):
        try:
            self.other(obj, location)

        except:
            return obj

        raise ValidationException(self.message, "Not %s" % self.other, str(obj), location)

    def __repr__(self):
        return "Not(%s)" % self.other


class Dictionary(Validator):

    """Validate a dictionary."""

    def casefold(self, s):
        if isinstance(s, str) and not self.case_sensitive:
            return CS(s)
        return s

    def __init__(self, required=None, optional=None, extra=None, extra_keys=None, min_extra=None, max_extra=None, case_sensitive=True,
                 allow_dups=False, key_type=str, ordered=False):
        self.case_sensitive = case_sensitive
        self.required = {self.casefold(k): v for k, v in required.items()} if required is not None else {}
        self.optional = {self.casefold(k): v for k, v in optional.items()} if optional is not None else {}
        self.extra = extra
        self.min_extra = min_extra
        self.max_extra = max_extra
        self.extra_keys = extra_keys
        self.allow_duplicates = allow_dups
        self.key_type = key_type
        self.ordered = ordered

    def __call__(self, obj, location="/"):
        if not isinstance(obj, dict):
            raise ValidationException("Expected a dictionary", self, obj, location)

        extra_count = 0
        keys = [self.casefold(x) for x in obj.keys()]
        dummy = {self.casefold(k): v for k, v in obj.items()}

        result = {} if not self.ordered else collections.OrderedDict()
        stringify = CS if not self.case_sensitive else str

        for key in self.required.keys():
            if key not in keys:
                raise ValidationException("Missing required key '%s'" % key, key, None, location)

        for key in keys:
            if not isinstance(key, self.key_type):
                raise ValidationException("Invalid key type", self.key_type, type(key), location)

            if not self.allow_duplicates and keys.count(key) > 1:
                raise ValidationException("Duplicate keys '%s'" % key, None, None, location)

            if not self.extra and key not in self.required.keys() and key not in self.optional.keys():
                raise ValidationException("Disallowed key '%s'" % key, None, key, location)

            if key in self.required.keys():
                result[stringify(key)] = self.required[key](dummy[key], "%s[%s]" % (location, key))

            elif key in self.optional.keys():
                result[stringify(key)] = self.optional[key](dummy[key], "%s[%s]" % (location, key))

            else:
                extra_count += 1

                if self.extra_keys is not None:
                    self.extra_keys(key, "%s[%s]" % (location, key))

                if self.extra is not None:
                    result[stringify(key)] = self.extra(dummy[key], "%s[%s]" % (location, key))

        if self.min_extra is not None and extra_count < self.min_extra:
            raise ValidationException("Expected at least %d extra keys" % self.min_extra, self.min_extra, extra_count, location)

        if self.max_extra is not None and extra_count > self.max_extra:
            raise ValidationException("Expected at most %d extra keys" % self.max_extra, self.max_extra, extra_count, location)

        return result

    def __repr__(self):
        return "Dictionary(required=%s, optional=%s, extra=%s, extra_keys=%s, case_sensitive=%s, allow_duplicates=%s, key_type=%s)" % (
            self.required,
            self.optional,
            self.extra,
            self.extra_keys,
            self.case_sensitive,
            self.allow_duplicates,
            self.key_type)


class Float(Validator):

    """Validate an integer."""

    def __init__(self, value=None, minimum=None, maximum=None, allow_integer=True):
        self.minimum = minimum
        self.maximum = maximum
        self.allow_integer = allow_integer
        self.value = value

    def __call__(self, obj, location="/"):
        if not isinstance(obj, float):
            raise ValidationException("Expected a float", float, type(obj), location)

        if isinstance(obj, int) and not self.allow_integer:
            raise ValidationException("Expceted a float", float, type(obj), location)

        if self.value is not None and obj != self.value:
            raise ValidationException("Expected %g" % self.value, self.value, obj, location)

        if self.minimum is not None and obj < self.minimum:
            raise ValidationException("Expected a float greater than %d" % self.minimum, self.minimum, obj, location)

        if self.maximum is not None and obj > self.maximum:
            raise ValidationException("Expected a float less than %d" % self.maximum, self.maximum, obj, location)

        return obj

    def __repr__(self):
        return "Float(%s, minimum=%s, maximum=%s, allow_integer=%s" % (self.value, self.minimum, self.maximum, self.allow_integer)


class InstanceOf(Validator):

    """Ensure that some object is an instance of a class."""

    def __init__(self, kind):
        self.kind = kind

    def __call__(self, obj, location="/"):
        if not isinstance(obj, self.kind):
            raise ValidationException("Expected an object of type '%s'" % self.kind, self.kind, type(obj), location)

        return obj

    def __repr__(self):
        return "InstanceOf(%s)" % self.kind


class Integer(Validator):

    """Validate an integer."""

    def __init__(self, value=None, minimum=None, maximum=None, allow_bool=False):
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.allow_bool = allow_bool

    def __call__(self, obj, location="/"):
        if not isinstance(obj, int):
            raise ValidationException("Expected an integer", int, type(obj), location)

        if isinstance(obj, bool) and not self.allow_bool:
            raise ValidationException("Expected an integer", int, type(obj), location)

        if self.value is not None and obj != self.value:
            raise ValidationException("Expected %d" % self.value, self.value, obj, location)

        if self.minimum is not None and obj < self.minimum:
            raise ValidationException("Expected an integer greater than %d" % self.minimum, self.minimum, obj, location)

        if self.maximum is not None and obj > self.maximum:
            raise ValidationException("Expected an integer less than %d" % self.maximum, self.maximum, obj, location)

        return obj

    def __repr__(self):
        return "Integer(%s, minimum=%s, maximum=%s, allow_bool=%s" % (self.value, self.minimum, self.maximum, self.allow_bool)


class List(Validator):

    """Validate a list."""

    def __init__(self, members, min_length=None, max_length=None):
        self.min_length = min_length
        self.max_length = max_length
        self.members = members

    def __call__(self, obj, location="/"):
        if not isinstance(obj, list):
            raise ValidationException("Expected a list", self, type(obj), location)

        if self.min_length is not None and len(obj) < self.min_length:
            raise ValidationException("Expected a list of at least length %d" % self.min_length, self.min_length, len(obj), location)

        if self.max_length is not None and len(obj) < self.max_length:
            raise ValidationException("Expected a list of at most length %d" % self.max_length, self.max_length, len(obj), location)

        result = []
        for i in range(0, len(obj)):
            result.append(self.members(obj[i], "%s[%s]" % (location, i)))

        return result

    def __repr__(self):
        return "List(%s, min_length=%s, max_length=%s)" % (self.members, self.min_length, self.max_length)


class Notify(Validator):

    """If a validator fails, provide a different message."""

    def __init__(self, message, validator, expected=None, actual=None):
        self.message = message
        self.validator = validator
        self.expected = expected
        self.actual = actual

    def __call__(self, obj, location="/"):
        try:
            return self.validator(obj, location)

        except Exception as e:
            e.message = self.message
            e.expected = self.expected if self.expected is not None else e.expected
            e.actual = self.actual if self.actual is not None else e.actual
            raise e

    def __repr__(self):
        return repr(self.validator)


class String(Validator):

    """Validate a string."""

    def __init__(self, pattern=None, min_length=None, max_length=None, case_sensitive=True):
        self.pattern = pattern
        self.min_length = min_length
        self.max_length = max_length
        self.case_sensitive = case_sensitive
        self.pretty_pattern = pattern if isinstance(pattern, str) else pattern.pattern if pattern is not None else ""

    def __call__(self, obj, location="/"):
        if not isinstance(obj, str):
            raise ValidationException("Expected a string", str, type(obj), location)

        if self.pattern is not None:
            if isinstance(self.pattern, str):
                if self.case_sensitive:
                    if self.pattern.casefold() != obj.casefold():
                        raise ValidationException("Expected '%s'" % self.pretty_pattern, self.pattern, obj, location)

                elif self.pattern != obj:
                    raise ValidationException("Expected '%s'" % self.pretty_pattern, self.pattern, obj, location)

            else:
                if not self.pattern.match(obj):
                    raise ValidationException("Expected '%s'" % self.pretty_pattern, self.pattern.pattern, obj, location)

        if self.min_length is not None and len(obj) < self.min_length:
            raise ValidationException("Expected a string of at least '%d' characters", self.min_length, len(obj), location)

        if self.max_length is not None and len(obj) > self.max_length:
            raise ValidationException("Expected a string of at most '%d' characters", self.max_length, len(obj), location)

        return obj if self.case_sensitive else CS(obj)

    def __repr__(self):
        return "String(pattern=%s, min_length=%s, max_length=%s, case_sensitive=%s)" % \
            (self.pattern, self.min_length, self.max_length, self.case_sensitive)
