#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id: 9ab794bf5f885e816d25fd2cfea01342ed14cc84 $
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
# Purpose: Parse expressions for Giles predicates and productions.
#
######################################################################

"""
expression.py - Parse expressions for Giles predicates and productions.
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2014 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE"
__version__ = "$Id: 9ab794bf5f885e816d25fd2cfea01342ed14cc84 $"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import re

from giles import pyre
from giles.caseless_string import CaselessString as CS

######################################################################
#
# The DefaultOperationsMixin is a mixin class that provides all of the
# basic arithmetic/logic operations via the special method names
# defined by the Python data model.
#
# The basic theory of operation here is that upon evaluation of an
# expression, the parser applies normal Python operators for the
# various operations (+, -, /, etc). For numbers and strings and
# such, this just works. For Giles datatypes, these methods are
# invoked and produce combining nodes which end up building up the
# syntax tree (and folding constants automatically).
#
# It's actually pretty elegant when you think about it.
#
######################################################################


class DefaultOperationsMixin:

    def __lt__(self, other):
        return BinaryOpNode("<", self, other, bool)

    def __le__(self, other):
        return BinaryOpNode("<=", self, other, bool)

    def __eq__(self, other):
        return BinaryOpNode("=", self, other, bool)

    def __ne__(self, other):
        return BinaryOpNode("!=", self, other, bool)

    def __gt__(self, other):
        return BinaryOpNode(">", self, other, bool)

    def __ge__(self, other):
        return BinaryOpNode(">=", self, other, bool)

    def __add__(self, other):
        return BinaryOpNode("+", self, other)

    def __sub__(self, other):
        return BinaryOpNode("-", self, other)

    def __mul__(self, other):
        return BinaryOpNode("*", self, other)

    def __truediv__(self, other):
        return BinaryOpNode("/", self, other)

    def __mod__(self, other):
        return BinaryOpNode("%", self, other)

    def __radd__(self, other):
        return BinaryOpNode("+", other, self)

    def __rsub__(self, other):
        return BinaryOpNode("-", other, self)

    def __rmul__(self, other):
        return BinaryOpNode("*", other, self)

    def __rtruediv__(self, other):
        return BinaryOpNode("/", other, self)

    def __rmod__(self, other):
        return BinaryOpNode("%", other, self)

    def __neg__(self):
        return UnaryOpNode("neg", self)

    def __pos__(self):
        return self

######################################################################
#
# The Node class is the basic class of the abstract syntax tree
# generated for an expression - expressions are trees whose internal
# nodes are (subclasses of) Nodes and whose leaves are either Nodes or
# normal Python constants.
#
# Nodes carry a type with them in their "type" member. What's
# important to understand is that all nodes have a type, even if
# they're abstract - this information is used by the type-checker.
#
# It's important to understand that Nodes are only built if one or
# more of their consituent parts can't be entirely determined at
# compile-time. In other words, having even a single Node by
# definition means that an expression is not constant.
#
######################################################################


class Node:

    def __init__(self):
        self.type = None

    def __repr__(self):
        return str(self)

######################################################################
#
# A LocalReferenceNode represents a reference to a local variable in
# an expression that will be resolved at runtime.
#
######################################################################


class LocalReferenceNode(Node, DefaultOperationsMixin):

    def __init__(self, variable, type):
        self.type = type
        self.variable = variable

    def __str__(self):
        return "Locals.%s" % self.variable

######################################################################
#
# A ThisReferenceNode represents a reference to a field in the event
# currently being matched.
#
######################################################################


class ThisReferenceNode(Node, DefaultOperationsMixin):

    def __init__(self, variable, type):
        self.type = type
        self.variable = variable

    def __str__(self):
        return "This.%s" % self.variable

######################################################################
#
# A BinaryOpNode represents a binary operator and its operands.
# It can either have a passed-in type, or it will take the type of
# its arguments (this works because Giles's type system does not do
# implicit type casting or promotion, so both operands will always be
# of the same type). We allow a passed-in type because, for example,
# the comparison operators take in arbitrary types but return bools.
#
######################################################################


class BinaryOpNode(Node, DefaultOperationsMixin):

    def __init__(self, operation, arg1, arg2, kind=None, readable_name=None):
        self.operation = operation
        self.name = readable_name if readable_name is not None else operation
        self.arg1 = arg1
        self.arg2 = arg2
        self.type = type(arg1) if type(arg1) in (bool, float, int, str) else arg1.type

        if kind is not None:
            self.type = kind

    def __str__(self):
        arg1 = self.arg1
        arg2 = self.arg2
        if isinstance(self.arg1, str):
            arg1 = "'%s'" % arg1.replace("'", "''")

        if isinstance(self.arg2, str):
            arg2 = "'%s'" % arg2.replace("'", "''")

        return "(%s %s %s)" % (arg1, self.name, arg2)

######################################################################
#
# A UnaryOpNode represents a unary operator and its operand.
#
######################################################################


class UnaryOpNode(Node, DefaultOperationsMixin):

    def __init__(self, operation, arg1, readable_name=None):
        self.operation = operation
        self.name = readable_name if readable_name is not None else operation
        self.arg1 = arg1
        self.type = type(arg1) if type(arg1) in (bool, float, int, str) else arg1.type

    def __str__(self):
        arg1 = self.arg1
        if isinstance(self.arg1, str):
            arg1 = "'%s'" % arg1.replace("'", "''")

        return "(%s %s)" % (self.name, arg1)

######################################################################
#
# An IfNode represents the ternary-if operation. This is produced by
# the "if" function in an expression.
#
######################################################################


class IfNode(Node, DefaultOperationsMixin):

    def __init__(self, predicate, if_true, if_false):
        self.predicate = predicate
        self.if_true = if_true
        self.if_false = if_false
        self.type = type(if_true) if type(if_true) in (bool, float, int, str) else if_true.type

    def __str__(self):
        return "if(%s, %s, %s)" % (self.predicate, self.if_true, self.if_false)

######################################################################
#
# A CastNode represents a cast of a value to a different (or, I
# suppose, the same) data type.
#
######################################################################


class CastNode(Node, DefaultOperationsMixin):

    def __init__(self, expression, cast_to):
        self.expression = expression
        self.type = cast_to

    def __str__(self):
        return "cast(%s -> %s)" % (self.expression, self.type)

######################################################################
#
# A JoinNode represents a conjunction of two boolean predicates on
# variables. JoinNodes represent joins in the runtime production
# system - so they're not just normal boolean conjunctions.
#
# Both children of a JoinNode must be boolean expressions, and the
# left-hand operand of each expression must be a single variable.
# The JoinNode is then used at runtime to produce the join statement
# between those two variables.
#
######################################################################


class JoinNode(Node, DefaultOperationsMixin):

    def __init__(self, arg1, arg2):
        self.left = arg1
        self.right = arg2
        self.type = bool

    def __str__(self):
        return "%s AND %s" % (self.left, self.right)

######################################################################
#
# A FunctionNode represents an invocation of a SQL function inside
# an expression.
#
######################################################################


class FunctionNode(Node, DefaultOperationsMixin):

    def __init__(self, name, external, returns, args):
        self.name = name
        self.external = external
        self.type = returns
        self.args = list(args)

    def __str__(self):
        return "%s%s" % (self.name, self.args)

######################################################################
#
# The Tokenizer is an instance of a normal Pyre tokenizer, with
# definitions for all of the tokens in the Giles language.
#
# The Tokenizer performs variable resolution at tokenization time,
# which allows for more aggressive constant folding and a cleaner code
# path later.
#
# This subclass of the Tokenizer object is not reentrant - you need
# to create a new Tokenizer object for every expression.
#
######################################################################


class Tokenizer(pyre.Tokenizer):

    def __init__(self, constants=None, variables=None, this=None):
        """
        Create a new Tokenizer.

        constants  - the currently defined constants
        variables  - the current local rule scope
        this       - the current matched event
        """

        super().__init__()

        self.constants = constants if constants is not None else {}
        self.variables = variables if variables is not None else {}
        self.this = this if this is not None else {}

    @pyre.syntax_rule(r"(!?~|[=!<>]=?|&&|[|][|]|[-+*/%.])", flags=re.I)
    def make_operator(self, tokenizer, captures):
        return pyre.OperatorToken(CS(captures[0]))

    @pyre.syntax_rule(r"Constants[.]([A-Za-z][A-Za-z0-9]*)", flags=re.I)
    def make_constant_reference(self, tokenizer, captures):
        if CS(captures[1]) not in self.constants:
            raise Exception("Unknown constant: '%s'" % captures[0])

        return self.constants[CS(captures[1])]

    @pyre.syntax_rule(r"This[.]([A-Za-z][A-Za-z0-9]*)", flags=re.I)
    def make_this_reference(self, tokenizer, captures):
        if CS(captures[1]) not in tokenizer.this:
            raise Exception("Unknown field: '%s'" % captures[0])

        return ThisReferenceNode(CS(captures[1]), tokenizer.this[CS(captures[1])])

    @pyre.syntax_rule(r"Locals[.]([A-Za-z][A-Za-z0-9]*)", flags=re.I)
    def make_locals_reference(self, tokenizer, captures):
        if CS(captures[1]) not in tokenizer.variables:
            raise Exception("Unknown variable: '%s'" % captures[0])

        return LocalReferenceNode(CS(captures[1]), tokenizer.variables[CS(captures[1])])

    @pyre.syntax_rule(r"[a-z][a-z0-9_]*", flags=re.I)
    def make_function(self, tokenizer, captures):
        if captures[0].lower() in ("and", "not", "like", "unlike"):
            return pyre.OperatorToken(CS(captures[0]))

        return pyre.FunctionToken(CS(captures[0]))

    @pyre.syntax_rule(r"(true|false)", flags=re.I)
    def make_boolean(self, tokenizer, captures):
        return captures[0].lower() == "true"

    @pyre.syntax_rule(r"\d+[.]\d+(e[-]?\d+)?", flags=re.I)
    def make_real(self, tokenizer, captures):
        return float(captures[0])

    @pyre.syntax_rule(r"\d+")
    def make_int(self, tokenizer, captures):
        return int(captures[0])

    @pyre.syntax_rule(r"'([^']*)'")
    def make_single_quoted_string(self, tokenizer, captures):
        return captures[1]

    @pyre.syntax_rule(r'"([^"]*)"')
    def make_double_quoted_string(self, tokenizer, captures):
        return captures[1]

    @pyre.syntax_rule(r"[$][a-f0-9]{2}", flags=re.I)
    def make_character_reference(self, tokenizer, captures):
        return chr(int(captures[0][1:], 16))

    @pyre.syntax_rule(r"#[^\n]*", skip=True)
    def make_comment(self, tokenizer, captures):
        pass

######################################################################
#
# The type_check function is a method decorator that can be applied to
# parser rules. The decorator's arguments are tuples, and each tuple
# represents a valid combination of arguments. For example, the
# decoration of the "+" operator might look like this:
#
#  @type_check((float, float), (int, int))
#
# Meaning that it takes two floats or two ints as an argument.
#
# For single-operand or single-argument functions, a single type
# argument may be passed.
#
######################################################################


def type_check(*combinations):
    def wrap(func):
        def inner(self, parser, *args):
            name = None
            if hasattr(func, 'binary_operator_name'):
                name = "operator '%s'" % func.binary_operator_name

            elif hasattr(func, 'unary_operator_name'):
                name = "operator '%s'" % func.unary_operator_name

            elif hasattr(func, 'defined_function_name'):
                name = "function '%s'" % func.defined_function_name

            else:
                assert False

            types = tuple([arg.type if isinstance(arg, Node) else type(arg) for arg in args])
            if len(types) == 1:
                types = types[0]

            if types not in combinations:
                if type(types) is not list:
                    types = [types]
                raise Exception("Invalid types for function/operator '%s': %s" % (name, " and ".join([str(x) for x in types])))

            return func(self, parser, *args)

        for attribute in ('binary_operator_name', 'binary_operator_precedence', 'binary_operator_associativity',
                          'unary_operator_name', 'unary_operator_precedence', 'unary_operator_associativity',
                          'defined_function_name'):
            if hasattr(func, attribute):
                setattr(inner, attribute, getattr(func, attribute))

        return inner
    return wrap

######################################################################
#
# Here's where the magic happens. This parser (a normal Pyre parser)
# defines all of the semantics of the Giles expression language.
# Expressions are passed into the parser and it builds up abstract
# syntax trees which are returned to the compiler.
#
# See the comments above to see how the parser builds the abstract
# syntax tree as a side-effect of evaluating the expression.
#
######################################################################


class Parser(pyre.Parser):

    def __init__(self, constants=None, variables=None, this=None, allow_regexp=False):
        """
        Create a new parser.

        constants    - the currently defined constants
        variables    - the current local rule scope
        this         - the current matched event
        allow_regexp - allow regular expression operations
        """

        super().__init__()

        self.constants = constants if constants is not None else {}
        self.variables = variables if variables is not None else {}
        self.this = this if this is not None else {}
        self.allow_regexp = allow_regexp

    @type_check((float, float), (int, int))
    @pyre.binary_operator("+", precedence=10)
    def operator_add(self, parser, arg1, arg2):
        return arg1 + arg2

    @type_check((float, float), (int, int))
    @pyre.binary_operator("-", precedence=10)
    def operator_sub(self, parser, arg1, arg2):
        return arg1 - arg2

    @type_check((float, float), (int, int))
    @pyre.binary_operator("*", precedence=20)
    def operator_mul(self, parser, arg1, arg2):
        return arg1 * arg2

    @type_check((float, float), (int, int))
    @pyre.binary_operator("/", precedence=20)
    def operator_div(self, parser, arg1, arg2):
        return arg1 / arg2

    @type_check((int, int))
    @pyre.binary_operator("%", precedence=20)
    def operator_mod(self, parser, arg1, arg2):
        return arg1 % arg2

    @type_check((bool, bool), (float, float), (int, int), (str, str))
    @pyre.binary_operator("==", precedence=5)
    def operator_equ(self, parser, arg1, arg2):
        return arg1 == arg2

    @type_check((bool, bool), (float, float), (int, int), (str, str))
    @pyre.binary_operator("<=", precedence=5)
    def operator_lte(self, parser, arg1, arg2):
        return arg1 <= arg2

    @type_check((bool, bool), (float, float), (int, int), (str, str))
    @pyre.binary_operator(">=", precedence=5)
    def operator_gte(self, parser, arg1, arg2):
        return arg1 >= arg2

    @type_check((bool, bool), (float, float), (int, int), (str, str))
    @pyre.binary_operator("!=", precedence=5)
    def operator_neq(self, parser, arg1, arg2):
        return arg1 != arg2

    @type_check((bool, bool), (float, float), (int, int), (str, str))
    @pyre.binary_operator("<", precedence=5)
    def operator_lt(self, parser, arg1, arg2):
        return arg1 < arg2

    @type_check((bool, bool), (float, float), (int, int), (str, str))
    @pyre.binary_operator(">", precedence=5)
    def operator_gt(self, parser, arg1, arg2):
        return arg1 > arg2

    @type_check((bool, bool))
    @pyre.binary_operator("||", precedence=30)
    def operator_or(self, parser, arg1, arg2):
        if type(arg1) == bool and type(arg2) == bool:
            return arg1 or arg2

        return BinaryOpNode("OR", arg1, arg2)

    @type_check((bool, bool))
    @pyre.binary_operator("&&", precedence=40)
    def operator_and(self, parser, arg1, arg2):
        if type(arg1) == bool and type(arg2) == bool:
            return arg1 and arg2

        return BinaryOpNode("AND", arg1, arg2)

    @type_check((str, str))
    @pyre.binary_operator("~", precedence=5)
    def operator_regexp(self, parser, arg1, arg2):
        if not self.allow_regexp:
            raise Exception("regular expressions in expressions are disabled")

        if type(arg2) == str:
            try:
                re.compile(arg2)

            except Exception as e:
                raise Exception("Invalid regular expression: '%s'" % e)

        if type(arg1) == str and type(arg2) == str:
            try:
                return re.match(arg2, arg1) is not None

            except Exception as e:
                raise Exception("Invalid regular expression: '%s'" % e)

        else:
            return BinaryOpNode("REGEXP", arg1, arg2, bool)

    @type_check((str, str))
    @pyre.binary_operator("!~", precedence=5)
    def operator_notregexp(self, parser, arg1, arg2):
        if not self.allow_regexp:
            raise Exception("regular expressions in expressions are disabled")

        if type(arg2) == str:
            try:
                re.compile(arg2)

            except Exception as e:
                raise Exception("Invalid regular expression: '%s'" % e)

        if type(arg1) == str and type(arg2) == str:
            try:
                return re.match(arg2, arg1) is None

            except Exception as e:
                raise Exception("Invalid regular expression: '%s'" % e)

        else:
            return BinaryOpNode("NOT REGEXP", arg1, arg2, bool)

    @type_check((str, str))
    @pyre.binary_operator("like", precedence=5)
    def operator_like(self, parser, arg1, arg2):
        if type(arg1) == str and type(arg2) == str:
            pattern = re.escape(arg2)
            pattern = pattern.replace(r"\%", "%")
            pattern = pattern.replace(r"\_", "_")
            pattern = pattern.replace("%", ".*")
            pattern = pattern.replace("_", ".")

            return re.match("^" + pattern + "$", arg1) is not None

        else:
            return BinaryOpNode("LIKE", arg1, arg2, bool)

    @type_check((str, str))
    @pyre.binary_operator("unlike", precedence=5)
    def operator_unlike(self, parser, arg1, arg2):
        if type(arg1) == str and type(arg2) == str:
            pattern = re.escape(arg2)
            pattern = pattern.replace(r"\%", "%")
            pattern = pattern.replace(r"\_", "_")
            pattern = pattern.replace("%", ".*")
            pattern = pattern.replace("_", ".")

            return re.match("^" + pattern + "$", arg1) is None

        else:
            return BinaryOpNode("NOT LIKE", arg1, arg2, bool)

    @type_check((bool, bool))
    @pyre.binary_operator("and", precedence=0)
    def operator_join(self, parser, arg1, arg2):
        if parser.this is None:
            raise Exception("Logical conjunctions of conditions are valid only in match predicates")

        return JoinNode(arg1, arg2)

    @type_check((str, str))
    @pyre.binary_operator(".", precedence=20)
    def operator_concat(self, parser, arg1, arg2):
        if type(arg1) == str and type(arg2) == str:
            return arg1 + arg2

        return BinaryOpNode("||", arg1, arg2, readable_name=".")

    @type_check(float, int)
    @pyre.unary_operator("+", precedence=98)
    def operator_pos(self, parser, arg1):
        return +arg1

    @type_check(float, int)
    @pyre.unary_operator("-", precedence=98)
    def operator_neg(self, parser, arg1):
        return -arg1

    @type_check(bool)
    @pyre.unary_operator("not", precedence=98)
    def operator_not(self, parser, arg1):
        if type(arg1) == bool:
            return not arg1

        return UnaryOpNode("NOT", arg1)

    @type_check(bool)
    @pyre.defined_function("string_of_bool")
    def function_string_of_bool(self, parser, arg1):
        return str(arg1) if type(arg1) == bool else CastNode(arg1, str)

    @type_check(float)
    @pyre.defined_function("string_of_real")
    def function_string_of_real(self, parser, arg1):
        return str(arg1) if type(arg1) == float else CastNode(arg1, str)

    @type_check(int)
    @pyre.defined_function("string_of_int")
    def function_string_of_int(self, parser, arg1):
        return str(arg1) if type(arg1) == int else CastNode(arg1, str)

    @type_check(int)
    @pyre.defined_function("real_of_int")
    def function_real_of_int(self, parser, arg1):
        return float(arg1) if type(arg1) == int else CastNode(arg1, float)

    @type_check(float)
    @pyre.defined_function("int_of_real")
    def function_int_of_real(self, parser, arg1):
        return int(arg1) if type(arg1) == float else CastNode(arg1, int)

    @type_check(str)
    @pyre.defined_function("int_of_string")
    def function_int_of_string(self, parser, arg1):
        return int(arg1) if type(arg1) == str else CastNode(arg1, int)

    @type_check((bool, bool, bool), (bool, float, float), (bool, int, int), (bool, str, str))
    @pyre.defined_function("if")
    def function_if(self, parser, predicate, if_true, if_false):
        if type(predicate) == bool:
            return if_true if predicate else if_false

        return IfNode(predicate, if_true, if_false)

######################################################################
#
# DelayedExpressions are expressions that are read in from the
# input file but not yet evaluated. Evaluation is delayed because
# expressions might contain references to things that haven't yet been
# defined (constants, etc).
#
# Expressions are marked with the tag "!expr" in the rule file.
#
######################################################################


class DelayedExpression:

    """An expression to be evaluated."""

    def __init__(self, expression):
        if not isinstance(expression, str):
            raise Exception("Invalid expression: not a string")

        self.expression = expression

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.expression
