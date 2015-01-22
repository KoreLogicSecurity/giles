#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id: f27124002febf7a45c9611b27a258e913466cf4b $
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
# Purpose: Provide a simple tokenizer and operator precedence parser.
#
######################################################################

"""
pyre - Tokenize and Parse Expressions

Pyre is a Python module that helps create tokenizers, parsers and
interpreters for expressions - that is, collections of operators, operands,
and function calls.

Functionality is split into the Tokenizer and Parser classes. Either one can
be used without the other, but they work quite well together. Tokenizer objects
are iterators over strings that yield tokens, and Parser objects parse streams
of tokens according to easily-defined precedence rules.

Here's a simple example combining the Tokenizer class and the Parser class
to produce a four-function calculator, plus the trigonometric function sin:

Recall that the tokenizer just creates an iterator over the tokens:

    >>> class FourFunctionTokenizer(Tokenizer):
    ...   # The self argument is an iterator, so not very useful - hence the
    ...   # tokenizer argument.
    ...   @syntax_rule(r"\\d+")
    ...   def make_number(self, tokenizer, captures):
    ...     return int(captures[0])
    ...
    ...   @syntax_rule(r"[-+*/]")
    ...   def make_operator(self, tokenizer, captures):
    ...     return OperatorToken(captures[0])
    ...
    ...   @syntax_rule(r"[a-z]+")
    ...   def make_function(self, tokenizer, captures):
    ...     return FunctionToken(captures[0])
    ...
    >>> tokenizer = FourFunctionTokenizer()
    >>> for token in tokenizer.tokenize("1 + (2 * 3)"):
    ...   print(token)
    1
    +
    OPEN_PAREN
    2
    *
    3
    CLOSE_PAREN

The tokenizer handles only a few things specially: parentheses, whitespace,
and newlines.

Whitespace and newlines can be replaced by overridding the newline and whitespace
methods in the subclass. New forms of whitespace, such as comments, can be added
easily by specifying the "skip" flag:

    >>> def make_comment(self, captures):
    ...   pass
    ...
    >>> tokenizer.add_syntax(r"#[^\\n]*", make_comment, skip=True)
    >>> for token in tokenizer.tokenize('''# I'm a comment!
    ...                                    1 + (2 * 3)'''):
    ...   print(token)
    NewlineToken()
    1
    +
    OPEN_PAREN
    2
    *
    3
    CLOSE_PAREN

Now, we create a simple parser that takes as its input the tokens produced by
the tokenizer we defined:

    >>> import math
    >>> class FourFunctionParser(Parser):
    ...   @binary_operator("+", precedence=10)
    ...   def add(self, parser, arg1, arg2):
    ...     return arg1 + arg2
    ...
    ...   @binary_operator("-", precedence=10)
    ...   def sub(self, parser, arg1, arg2):
    ...     return arg1 - arg2
    ...
    ...   @binary_operator("*", precedence=20)
    ...   def mul(self, parser, arg1, arg2):
    ...     return arg1 * arg2
    ...
    ...   @binary_operator("/", precedence=20)
    ...   def div(self, parser, arg1, arg2):
    ...     return arg1 / arg2
    ...
    ...   # Functions are just normal Python functions. They take two additional
    ...   # arguments: self should be accepted but ignored (it is an iterator
    ...   # object), and parser is the parser object. The remaining arguments, if
    ...   # any, are the arguments passed to the function in the expression.
    ...   @defined_function("sin")
    ...   def sin(self, parser, arg1):
    ...     return math.sin(arg1)
    ...
    >>> parser    = FourFunctionParser()
    >>> tokenizer = FourFunctionTokenizer()
    >>> print(parser.parse(tokenizer.tokenize("1 + 2 * 3")))
    7

The default implementation of the parser is stateless (though of course
subclasses need not be):

    >>> print(parser.parse(tokenizer.tokenize("sin(1)")))
    0.8414709848078965

Parentheses are handled appropriately:

    >>> print(parser.parse(tokenizer.tokenize("(1 + 2) * 3")))
    9
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2014 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE"
__version__ = "$Id: f27124002febf7a45c9611b27a258e913466cf4b $"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import re


def syntax_rule(regex, flags=0, skip=False):
    """
    Decorate a function as a syntax rule for the Tokenizer class.

    This decorator can be used to decorate methods of subclasses of the
    Tokenizer class and declaratively add syntax.
    """

    def wrap(func):
        def inner(self, tokenizer, groups):
            return func(self, tokenizer, groups)

        inner.syntax_rule = regex
        inner.syntax_flags = flags
        inner.syntax_skip = skip

        return inner
    return wrap


class UnknownTokenException(Exception):

    """The UnknownTokenException indicates that untokenizable input was found
    and, if available, the input position of the untokenizable input."""

    def __init__(self, token, near=None):
        super().__init__("Unknown input: '%s'%s" % (token, "" if near is None else " near '%s'" % near))


class Token:

    """
    The Parser class expects its input in the form of a stream of Token objects
    and "other" objects. Token objects represent things that the parser cares.

    about - e.g. numbers, parentheses, function names. These are represented by
    different subclasses of the Token class.

    Everything else in the parser's input are "other" objects and can be
    anything. The parser just passes these objects to the user-defined operator
    functions, so it's up to the user to decide how to handle them.
    """

    pass


class OpenParenToken(Token):

    """
    The OpenParenToken is one of the tokens the parser cares about. Parentheses
    are used to group expressions and alter default precedence, and surround
    arguments to functions.

    OpenParenToken objects represent, unsurprisingly, open (or left)
    parentheses.
    """

    def __str__(self):
        return "OPEN_PAREN"


class CloseParenToken(Token):

    """
    The CloseParenToken is one of the tokens the parser cares about.
    Parentheses are used to group expressions and alter default precedence, and
    surround arguments to functions.

    CloseParenToken objects represent, unsurprisingly, close (or right)
    parentheses.
    """

    def __str__(self):
        return "CLOSE_PAREN"


class ArgumentSeparatorToken(Token):

    """
    The ArgumentSeparatorToken class represents a separator between two
    arguments in a function invocation.

    By default, this is a comma.
    """

    def __str__(self):
        return "ARGUMENT_SEPARATOR"


class FunctionToken(Token):

    """
    FunctionToken objects represent function names in input.

    The programmer is responsible for disambiguating these from "normal"
    variable names if such a concept is applicable in the program.
    """

    def __init__(self, name):
        self.name = name


class OperatorToken(Token):

    """
    OperatorToken objects represents operators in input.

    They are handled by the parser according to the defined operator
    types.
    """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class NewlineToken(Token):

    """NewlineToken objects are spat out by the tokenizer whenever a newline is
    encountered, allowing the parser to keep track of where it is in the input,
    if it is so inclined."""

    def __str__(self):
        return "NewlineToken()"

    def __repr__(self):
        return str(self)


class Tokenizer:

    """
    A Tokenizer object implements the iterator protocol, and iterates over a
    string using a defined set of tokenization rules.

    Tokenizers are easily built using the syntax_rule decorator for methods.
    The Tokenizer class provides default rules for whitespace and newlines; these
    can be replaced by defining a whitespace or newline method in a subclass.
    There also exist default rules for parentheses and argument separators - this
    can be changed but probably shouldn't be.

    Rules can be added to the tokenizer after initialization using the add_syntax
    method.
    """

    def __init__(self):
        self.rules = []

        for attr in dir(self):
            obj = getattr(self, attr)
            if hasattr(obj, "syntax_rule"):
                self.add_syntax(obj.syntax_rule, obj, obj.syntax_flags, obj.syntax_skip)

    def tokenize(self, string):
        """Tokenize a string by returning an iterator over that string."""

        class Iterator:

            def __init__(self, tokenizer, rules, string):
                self.rules = rules
                self.string = string
                self.tokenizer = tokenizer

            def __iter__(self):
                return self

            def __next__(self):
                longest_match = None
                longest_callback = None
                longest_length = 0
                longest_skip = False

                if len(self.string) == 0:
                    raise StopIteration()

                for regex, callback, skip in self.rules:
                    match = regex.match(self.string)
                    if match:
                        if len(match.group(0)) > longest_length:
                            longest_match = match
                            longest_callback = callback
                            longest_length = len(match.group(0))
                            longest_skip = skip

                if longest_length == 0:
                    raise UnknownTokenException(self.string)

                result = longest_callback(self.tokenizer, (longest_match.group(0),) + longest_match.groups())
                self.string = self.string[longest_length:]

                if longest_skip:
                    return next(self)

                else:
                    return result

        return Iterator(self, self.rules, string)

    def add_syntax(self, regex, callback, flags=0, skip=False):
        """
        Add a new tokenization rule. If the input matches the given regular
        expression (compiled with the optional flags), the captured groups are
        passed to the given callback, and the result of that callback is the
        token.

        If the skip flag is true, the tokenizer will execute the callback, but not
        return the token; it will instead iterate again. This is useful for things like
        comments and newlines. Note that, since the callback is still called, the
        rule can have side-effects such as updating the input position.
        """

        self.rules.append((re.compile(regex, flags), callback, skip))

    @syntax_rule(r"[ \t\r\v]+", skip=True)
    def whitespace(self, tokenizer, groups):
        pass

    @syntax_rule(r"\n")
    def newline(self, tokenizer, groups):
        return NewlineToken()

    @syntax_rule(r"[()]")
    def parentheses(self, tokenizer, groups):
        return OpenParenToken() if groups[0] == "(" else CloseParenToken()

    @syntax_rule(r"[,]")
    def separator(self, tokenizer, groups):
        return ArgumentSeparatorToken()


class ExtraInputException(Exception):

    """The ExtraInputException indicates that there was extra input after the
    last element of the parsed expression."""

    def __init__(self, extra):
        super().__init__("Extra input after end of expression: '%s'" % extra)
        self.extra = extra


class MissingOperandException(Exception):

    """The MissingOperandException exception indicates that there were missing
    operands to some defined operator."""

    def __init__(self, operator, line):
        super().__init__("Missing operand for '%s' operator on line %d" % (operator, line))
        self.operator = operator


class UnknownOperatorException(Exception):

    """The UnknownOperatorException indicates that the tokenizer passed an
    undefined operator to the parser."""

    def __init__(self, operator, line):
        super().__init__("Unknown operator '%s' on %d" % (operator, line))
        self.operator = operator


class UnknownFunctionException(Exception):

    """The UnknownFunctionException indicates that the tokenizer passed an
    undefined function to the parser."""

    def __init__(self, name, line):
        super().__init__("Unknown function '%s' on line %d" % (name, line))
        self.function = name


class MismatchedParenthesesException(Exception):

    """The MismatchedParenthesesException indicates a mismatched pair of
    parentheses were present in the expression."""

    def __init__(self, line):
        super().__init__("Mismatched parentheses on line %d" % line)


class Operator:

    """The Operator class represents an operator to be evaluated."""

    def __init__(self, name, precedence, associativity):
        self.name = name
        self.precedence = precedence
        self.associativity = associativity

    def __str__(self):
        return "Operator(%s)" % (self.name,)

    def __repr__(self):
        return str(self)


class BinaryOperator(Operator):

    """The BinaryOperator class represents a binary operator to be
    evaluated."""

    def __init__(self, name, precedence, associativity, callback):
        super().__init__(name, precedence, associativity)
        self.callback = callback

    def __str__(self):
        return "BinaryOperator(%s)" % (self.name,)

    def __call__(self, parser, arg1, arg2):
        return self.callback(parser, arg1, arg2)


class UnaryOperator(Operator):

    """The UnaryOperator class represents a unary operator to be evaluated."""

    def __init__(self, name, precedence, associativity, callback):
        super().__init__(name, precedence, associativity)
        self.callback = callback

    def __str__(self):
        return "UnaryOperator(%s)" % (self.name,)

    def __call__(self, parser, arg1):
        return self.callback(parser, arg1)


class Function:

    """The Function class represents a function known to the parser."""

    def __init__(self, name, parser, callback):
        self.parser = parser
        self.callback = callback
        self.name = name

    def __str__(self):
        return "Function(%s)" % (self.name,)

    def __repr__(self):
        return str(self)


class FunctionInvocation:

    def __init__(self, func, line=0):
        self.argcount = 0
        self.line = line
        self.name = func.name
        self.parser = func.parser
        self.callback = func.callback

    def __call__(self, stack):
        args = [self.parser.evaluate(stack, self.line) for i in range(0, self.argcount)]
        args.reverse()
        return self.callback(self.parser, *args)


def defined_function(name=None):
    """
    Decorate a function as a defined function known to the parser.

    This decorator can be used to decorate methods of subclasses of the
    Parser class and declaratively add functions. The name argument can
    be used to rename the function inside expressions.
    """

    def wrap(func):
        def inner(self, parser, *args):
            return func(self, parser, *args)

        inner.defined_function_name = name if name is not None else func.__name__

        return inner
    return wrap


def binary_operator(name, precedence=10, associativity="left"):
    """
    Decorate a function as a binary operator.

    This decorator can be used to decorate methods of subclasses of the
    Parser class and declaratively add new operators.
    """

    def wrap(func):
        def inner(self, parser, arg1, arg2):
            return func(self, parser, arg1, arg2)

        inner.binary_operator_name = name
        inner.binary_operator_precedence = precedence
        inner.binary_operator_associativity = associativity

        return inner
    return wrap


def unary_operator(name, precedence=10, associativity="right"):
    """
    Decorate a function as a unary operator.

    This decorator can be used to decorate methods of subclasses of the
    Parser class and declaratively add new operators.
    """

    def wrap(func):
        def inner(self, parser, arg1):
            return func(self, parser, arg1)

        inner.unary_operator_name = name
        inner.unary_operator_precedence = precedence
        inner.unary_operator_associativity = associativity

        return inner
    return wrap


class Parser:

    """
    A Parser object takes a stream of Token objects (retrieved by iterating
    over a Tokenizer object) and parses them according to the operator
    precedence rules defined for the parser.

    Rules are defined using the binary_operator, unary_operator, and
    defined_function decorators. Rules can be added after initialization
    time by using the add_binary_operator, add_unary_operator, and
    add_function methods.
    """

    def __init__(self):
        self.binary_operators = {}
        self.unary_operators = {}
        self.functions = {}

        for attr in dir(self):
            obj = getattr(self, attr)
            if hasattr(obj, "defined_function_name"):
                self.add_function(obj.defined_function_name, obj)

            elif hasattr(obj, "binary_operator_name"):
                self.add_binary_operator(obj.binary_operator_name, obj.binary_operator_precedence, obj.binary_operator_associativity, obj)

            elif hasattr(obj, "unary_operator_name"):
                self.add_unary_operator(obj.unary_operator_name, obj.unary_operator_precedence, obj.unary_operator_associativity, obj)

    def add_binary_operator(self, name, precedence, associativity, callback):
        """
        Add the named operator with the given precedence and associactivity.

        When the operator is evaluated, its arguments will be passed to
        the callback.
        """

        assert precedence >= 0
        assert associativity in ("left", "right")

        self.binary_operators[name] = BinaryOperator(name, precedence, associativity, callback)

    def add_unary_operator(self, name, precedence, associativity, callback):
        """
        Add the named operator with the given precedence and associactivity.

        When the operator is evaluated, its arguments will be passed to
        the callback.
        """

        assert precedence >= 0
        assert associativity in ("left", "right")

        self.unary_operators[name] = UnaryOperator(name, precedence, associativity, callback)

    def add_function(self, name, callback):
        """Add the named function and associate it with the given callback."""

        self.functions[name] = Function(name, self, callback)

    def parse(self, tokenizer):
        """
        Parse the stream of tokens represented by the tokenizer and return the
        result of evaluating the stream.

        By defining operators that build nodes, "evaluating" can produce
        abstract syntax trees.
        """

        line = 1
        last_token = None
        output = []
        stack = []

        for token in iter(tokenizer):
            if isinstance(token, NewlineToken):
                line = line + 1

            elif isinstance(token, FunctionToken):
                if token.name not in self.functions:
                    raise UnknownFunctionException(token.name, line)

                stack.append(FunctionInvocation(self.functions[token.name], line))

            elif isinstance(token, ArgumentSeparatorToken):
                if last_token is None or isinstance(last_token, Operator) or isinstance(last_token, OpenParenToken):
                    raise MismatchedParenthesesException(line)

                while len(stack) > 0 and not isinstance(stack[-1], OpenParenToken):
                    output.append(stack.pop())

                if len(stack) < 2 or not isinstance(stack[-2], FunctionInvocation):
                    raise MismatchedParenthesesException(line)

                if stack[-2].argcount == 0:
                    stack[-2].argcount += 1

                stack[-2].argcount += 1

            elif isinstance(token, OperatorToken):
                operators = self.binary_operators
                if last_token is None or isinstance(last_token, OperatorToken) or isinstance(last_token, OpenParenToken):
                    operators = self.unary_operators

                if token.name not in operators:
                    raise UnknownOperatorException(token.name, line)

                o1 = operators[token.name]
                while len(stack) > 0 and isinstance(stack[-1], Operator) and \
                        ((o1.associativity == "left" and o1.precedence == stack[-1].precedence) or (o1.precedence < stack[-1].precedence)):
                    output.append(stack.pop())

                stack.append(o1)

            elif isinstance(token, OpenParenToken):
                stack.append(token)

            elif isinstance(token, CloseParenToken):
                if isinstance(last_token, ArgumentSeparatorToken):
                    raise MismatchedParenthesesException(line)

                while len(stack) > 0 and not isinstance(stack[-1], OpenParenToken):
                    output.append(stack.pop())

                if len(stack) == 0:
                    raise MismatchedParenthesesException(line)

                stack.pop()

                if len(stack) > 0 and isinstance(stack[-1], FunctionInvocation):
                    func = stack.pop()
                    if (not isinstance(last_token, OpenParenToken)) and func.argcount == 0:
                        func.argcount = 1
                    output.append(func)

            else:
                if last_token is not None and not (isinstance(last_token, Operator) or isinstance(last_token, Token)):
                    raise ExtraInputException(str(token))
                output.append(token)

            last_token = token

        while len(stack) > 0:
            if isinstance(stack[-1], OpenParenToken) or isinstance(stack[-1], CloseParenToken):
                raise MismatchedParenthesesException(line)

            output.append(stack.pop())

        result = self.evaluate(output, line)
        if len(output) > 0:
            raise ExtraInputException(output)

        return result

    def evaluate(self, stack, line=0):
        """Evaluate the operator or function on the top of the stack."""

        operator = stack.pop()

        if isinstance(operator, UnaryOperator):
            if len(stack) < 1:
                raise MissingOperandException(operator.name, line)

            arg1 = self.evaluate(stack, line)
            return operator(self, arg1)

        elif isinstance(operator, BinaryOperator):
            if len(stack) < 2:
                raise MissingOperandException(operator.name, line)

            arg2 = self.evaluate(stack, line)
            arg1 = self.evaluate(stack, line)
            return operator(self, arg1, arg2)

        elif isinstance(operator, FunctionInvocation):
            return operator(stack)

        else:
            return operator

if __name__ == "__main__":
    import doctest
    doctest.testmod()
