#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id: 8167f624b26dd2a7fd59f35364aea3a48e650e30 $
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
# Purpose: Compile production systems.
#
######################################################################

"""
giles.py - compile production systems
"""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2013 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE"
__version__ = "$Id: 8167f624b26dd2a7fd59f35364aea3a48e650e30 $"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import argparse
import logging
import re
import sys
import yaml

from giles import forbidden_names
from giles import get_release_string
from giles.expression import BinaryOpNode, DelayedExpression, FunctionNode, JoinNode, Node, Parser, ThisReferenceNode, Tokenizer
from giles.caseless_string import CaselessString as CS
from giles.validate import Any, Boolean, Dictionary, Float, InstanceOf, Integer, List, Notify, String


######################################################################
#
# Report an error.
#
######################################################################

errors = 0


def error(*strings):
    """Print errors to stderr and update the error count."""

    global errors
    errors += 1

    message = " ".join(str(x) for x in strings)
    logging.error(message)

    return message

######################################################################
#
# Load our backend modules.
#
######################################################################

from giles import sqlite_backend

backends = {
    "sqlite": sqlite_backend
}

######################################################################
#
# Rule File Schema
# The rule file must conform to this schema (expressed using the
# validator module) to be considered valid.
#
# The validator reformats its input as well (so really, it's a
# "transforming" validator). This handles turning everything into
# CaselessStrings, for example.
#
# We augment the basic validator with a OutputFactDeclaration
# validator. This looks for the "!output" tag (defined below), which
# means facts of that class should never reuse IDs and those facts
# are exempt from alpha pruning.
#
# We also add the DistinctProductionDeclaration validator. This looks
# for the "!distinct" tag (defined below), which means that the
# produced fact should be a distinct fact (in the context of
# recursive productions).
#
######################################################################


class OutputFact(dict):
    is_output = True


class OutputFactDeclaration(Dictionary):

    def __call__(self, obj, location="/"):
        result = super().__call__(obj, location)
        if isinstance(obj, OutputFact):
            return OutputFact(result)
        return result


class DistinctProduction(dict):
    pass


class DistinctProductionDeclaration(Dictionary):

    def __call__(self, obj, location="/"):
        result = super().__call__(obj, location)
        if isinstance(obj, DistinctProduction):
            return DistinctProduction(result)
        return result

AnyExpression = Any(Integer(allow_bool=True), Float(), String(), InstanceOf(DelayedExpression))
ValidName = Notify("Invalid variable name", expected="A variable name that does not conflict with any Giles or SQL keywords",
                   validator=String(re.compile("(?i)^(?!(" + "|".join(forbidden_names.names) + ")$)[A-Z][A-Z0-9]*$"), case_sensitive=False))
ValidType = String(re.compile("(?i)^(BOOLEAN|INTEGER|REAL|STRING)$"), case_sensitive=False)

ValidInverted = Dictionary(
    case_sensitive=False,

    required={
        "Fact": ValidName,
        "Meaning": String()
    },

    optional={
        "When": InstanceOf(DelayedExpression),
    })

ValidMatch = Dictionary(
    case_sensitive=False,

    required={
        "Fact": ValidName,
        "Meaning": String()
    },

    optional={
        "When": InstanceOf(DelayedExpression),
        "Assign": Dictionary(min_extra=1, case_sensitive=False, extra_keys=ValidName, extra=AnyExpression)
    })

ValidParameter = Dictionary(
    case_sensitive=False,

    required={
        "Default": AnyExpression,
    },

    optional={
        "Dictionary": Boolean(),
        "Lower": AnyExpression,
        "Upper": AnyExpression
    })

ValidProduce = DistinctProductionDeclaration(min_extra=1,
                                             max_extra=1,
                                             case_sensitive=False,
                                             extra_keys=ValidName,
                                             extra=Dictionary(extra_keys=ValidName, extra=AnyExpression, case_sensitive=False))

ValidSuppress = Dictionary(
    case_sensitive=False,

    required={
        "Fact": ValidName
    },

    optional={
        "When": InstanceOf(DelayedExpression)
    })

ValidRule = Any(
    Dictionary(
        case_sensitive=False,

        optional={
            "Enabled": Boolean(),
            "MatchNone": List(ValidInverted),
            "When": AnyExpression,
            "Metadata": Dictionary(extra_keys=ValidName, extra=List(AnyExpression), case_sensitive=False)
        },

        required={
            "Description": String(),
            "MatchAll": List(ValidMatch),
            "Assert": ValidProduce
        }),

    Dictionary(
        case_sensitive=False,

        optional={
            "Enabled": Boolean(),
            "MatchNone": List(ValidInverted),
            "When": AnyExpression,
            "Metadata": Dictionary(extra_keys=ValidName, extra=List(AnyExpression), case_sensitive=False)
        },

        required={
            "Description": String(),
            "MatchAll": List(ValidMatch),
            "Suppress": ValidSuppress
        }))

ValidFunction = Dictionary(
    case_sensitive=False,

    required={
        "External": String(re.compile(r"^[A-Za-z0-9_]+$")),
        "Parameters": List(ValidType),
        "Returns": ValidType
    })

partial_validator = Dictionary(
    case_sensitive=False,

    optional={
        "Constants": Dictionary(case_sensitive=False,
                                extra_keys=ValidName,
                                extra=AnyExpression),

        "Parameters": Dictionary(case_sensitive=False,
                                 extra_keys=ValidName,
                                 extra=ValidParameter),

        "Description": String(),

        "Functions": Dictionary(min_extra=1,
                                case_sensitive=False,
                                extra_keys=ValidName,
                                extra=ValidFunction),

        "Facts": Dictionary(min_extra=1,
                            case_sensitive=False,
                            extra_keys=ValidName,
                            extra=OutputFactDeclaration(extra=ValidType, extra_keys=ValidName, case_sensitive=False, min_extra=1)),
        "Rules": Dictionary(min_extra=1,
                            case_sensitive=False,
                            extra_keys=ValidName,
                            extra=ValidRule)
    })

validator = Dictionary(
    case_sensitive=False,

    optional={
        "Constants": Dictionary(case_sensitive=False,
                                extra_keys=ValidName,
                                extra=AnyExpression),

        "Parameters": Dictionary(case_sensitive=False,
                                 extra_keys=ValidName,
                                 extra=ValidParameter),

        "Description": String(),

        "Functions": Dictionary(min_extra=1,
                                case_sensitive=False,
                                extra_keys=ValidName,
                                extra=ValidFunction)
    },

    required={
        "Facts": Dictionary(min_extra=1,
                            case_sensitive=False,
                            extra_keys=ValidName,
                            extra=OutputFactDeclaration(extra=ValidType, extra_keys=ValidName, case_sensitive=False, min_extra=1)),
        "Rules": Dictionary(min_extra=1,
                            case_sensitive=False,
                            extra_keys=ValidName,
                            extra=ValidRule)
    })

######################################################################
#
# Load and Validate the Rule File
# We specify custom YAML tags here to decorate various portions of the
# engine description.
#
# The input may be split across multiple modules (rule files).
# An individual rule file might be "incomplete" - it might be
# missing a rule section for example, and define only facts.
# Thus each individual module is run through a "partial" validator
# that just validates the parts of the engine that the module actually
# defines.
#
# Once each of the individual modules has been validated, they are
# merged together and the entire engine is validated using the "full"
# validator, which does require that the mandatory parts of the engine
# exist.
#
######################################################################


def main(*args):
    ######################################################################
    #
    # Globals
    #
    ######################################################################

    constants = {}       # Defined constants, indexed by name
    distincts = set([])  # Facts that are produced in distinct productions
    functions = {}       # Defined external functions, indexed by name
    parameters = {}      # Defined parameters, indexed by name
    rules = {}           # Defined rules, indexed by name
    facts = {            # Defined facts, indexed by name
        CS("InitialFact"): {
            CS("InitializationTime"): int
        }
    }

    ######################################################################
    #
    # Process our arguments.
    #
    ######################################################################

    arg_parser = argparse.ArgumentParser(description="Compile a correlation engine/production system to a schema",
                                         epilog="Available backends: " + (" ".join(backends.keys())))
    arg_parser.add_argument('-v', '--version', action="version", version="Giles {0}".format(get_release_string()))
    arg_parser.add_argument('-b', '--backend', dest='backend', default="sqlite",
                            help="generate a schema using this backend", metavar="BACKEND", choices=backends.keys())
    arg_parser.add_argument('-c', '--allow-cycles', dest='check_cycles', default=True,
                            action='store_const', const=False, help="allow cycles in the rule set")
    arg_parser.add_argument('-r', '--allow-regexp', dest='allow_regexp', default=False,
                            action='store_const', const=True, help="allow regexp operator in expressions")
    arg_parser.add_argument('-p', '--prefix',
                            type=lambda x: error("Invalid prefix:", x) if not re.match("(?i)^[A-Z][A-Za-z0-9]*$", x) else x,
                            dest='prefix', default="giles", help="prefix all generated database objects with this string")
    arg_parser.add_argument('-o', '--output-file', type=argparse.FileType('w'), dest='schema_file', metavar="OUTPUT",
                            default="-", help="destination schema file")
    arg_parser.add_argument('files', type=argparse.FileType('r'), help="rule file(s) to compile", metavar="FILE", nargs='+')
    arguments = arg_parser.parse_args(args if len(args) else None)

    ######################################################################
    #
    # Expression Evaluator
    #
    ######################################################################

    def build_function_node(name, clause):
        def inner(*args):
            # The + 1 is because the function gets called with the parser object as its first argument.
            if len(args) != len(clause[CS("Parameters")]) + 1:
                raise Exception("Invalid number of arguments to function '%s'" % name)

            # The 1: is because the function gets called with the parser object as its first arg.
            if [type(x) if not isinstance(x, Node) else x.type for x in args[1:]] != clause[CS("Parameters")]:
                raise Exception("Invalid type(s) for argument(s) to function '%s'" % name)

            return FunctionNode(name, clause[CS("External")], clause[CS("Returns")], args[1:])

        return inner

    def evaluate(value, variables=None, this=None):
        """
        Evaluate an expression, taking constants and facts from the global
        namespace.

        The variables and this arguments are used within rules and
        matches for local variables and the current fact.
        """

        if isinstance(value, DelayedExpression):
            tokenizer = Tokenizer(constants, {} if variables is None else variables, this)
            parser = Parser(constants, {} if variables is None else variables, this, arguments.allow_regexp)

            for name, clause in functions.items():
                parser.add_function(str(name.lower()), build_function_node(name, clause))

            return parser.parse(tokenizer.tokenize(value.expression))

        else:
            return value

    ######################################################################
    #
    # Build the input document.
    #
    ######################################################################

    yaml.add_constructor("!expr", lambda x, y: DelayedExpression(str(y.value)))
    yaml.add_constructor("!output", lambda x, y: OutputFact(x.construct_mapping(y)))
    yaml.add_constructor("!distinct", lambda x, y: DistinctProduction(x.construct_mapping(y)))

    document = {}
    try:
        description = ""

        document = {
            CS("Constants"): {},
            CS("Parameters"): {},
            CS("Functions"): {},
            CS("Facts"): {},
            CS("Rules"): {}
        }

        for input_file in arguments.files:
            temp = partial_validator(yaml.load(input_file))
            for key, value in document.items():
                if key in temp:
                    value.update(temp[key])

            if CS("Description") in temp:
                description = "\n".join([description, temp[CS("Description")]])

            input_file.close()

        for key in [k for k, v in document.items() if len(v) == 0]:  # Clear out any empty sections.
            del document[key]

        document[CS("Description")] = description
        document = validator(document)

    except Exception as e:
        sys.stderr.write("Could not load rule file: %s\n" % e)
        sys.exit(1)

    ######################################################################
    #
    # Link SQL Functions
    #
    ######################################################################

    if CS("Functions") in document:
        for name, clause in document[CS("Functions")].items():
            try:
                functions[CS(name)] = clause
                functions[CS(name)][CS("Parameters")] = [
                    {"boolean": bool, "integer": int, "real": float, "string": str}[x.lower()] for x in clause[CS("Parameters")]]
                functions[CS(name)][CS("Returns")] = {"boolean": bool, "integer": int, "real": float, "string": str}[
                    clause[CS("Returns")].lower()]

            except Exception as e:
                del functions[CS(name)]
                error("Error processing function declarations:", e)

    ######################################################################
    #
    # Evaluate Constants
    #
    ######################################################################

    if CS("Constants") in document:
        for name, value in document[CS("Constants")].items():
            try:
                constants[name] = evaluate(value)

                if type(constants[name]) not in (bool, float, int, str):
                    raise Exception("Invalid constant '%s': not a constant initializer" % name)

            except Exception as e:
                del constants[name]
                error("Error processing constants:", e)

    ######################################################################
    #
    # Load Facts
    #
    ######################################################################

    facts[CS("InitialFact")] = OutputFact(facts[CS("InitialFact")])
    for name, fields in document[CS("Facts")].items():
        facts[name] = {k: {"boolean": bool, "integer": int, "real": float, "string": str}[v] for k, v in fields.items()}
        if isinstance(fields, OutputFact):
            facts[name] = OutputFact(facts[name])

    ######################################################################
    #
    # Evaluate Parameters
    #
    ######################################################################

    if CS("Parameters") in document:
        for name, value in document[CS("Parameters")].items():
            try:
                if CS(name) in facts:
                    raise Exception("Collision between parameter '%s' and an identically-named fact" % name)

                parameters[name] = {}
                parameters[name]["default"] = evaluate(value[CS("Default")])

                if type(parameters[name]["default"]) not in (bool, float, int, str):
                    raise Exception("Invalid parameter '%s': not a constant initializer" % name)

                if type(parameters[name]["default"]) in (float, int):
                    if CS("Lower") not in value:
                        raise Exception("Invalid parameter '%s': no lower limit specified" % name)

                    if CS("Upper") not in value:
                        raise Exception("Invalid parameter '%s': no upper limit specified" % name)

                    if not isinstance(value[CS("Upper")], type(value[CS("Lower")])) or \
                            not isinstance(value[CS("Upper")], type(parameters[name]["default"])):
                        raise Exception("Invalid parameter '%s': types of default and limits do not agree" % name)

                    if value[CS("Upper")] < value[CS("Lower")]:
                        raise Exception("Invalid parameter '%s': limits out of order" % name)

                    parameters[name]["lower"] = evaluate(value[CS("Lower")])
                    parameters[name]["upper"] = evaluate(value[CS("Upper")])

                    if parameters[name]["default"] < parameters[name]["lower"] or parameters[name]["default"] > parameters[name]["upper"]:
                        raise Exception("Invalid parameter '%s': default value is outside of specified limits" % name)

                else:
                    if CS("Lower") in value or CS("Upper") in value:
                        raise Exception("Invalid parameter '%s': cannot specify limits on non-numeric types" % name)

                    parameters[name]["lower"] = None
                    parameters[name]["upper"] = None

                facts[CS(name)] = {}
                facts[CS(name)][CS("Value")] = type(parameters[name]["default"])

                if CS("Dictionary") in value and value[CS("Dictionary")]:
                    parameters[name]["dictionary"] = True
                    facts[CS(name)][CS("Key")] = str

                else:
                    parameters[name]["dictionary"] = False

            except Exception as e:
                del parameters[name]
                if name in facts:
                    del facts[name]

                error("Error processing parameters:", e)

    ######################################################################
    #
    # Load Rules
    #
    ######################################################################

    for rule_name, rule_clause in document[CS("Rules")].items():
        try:
            ##################################################################
            #
            # Check to see if the rule is enabled.
            #
            ##################################################################

            if CS("Enabled") in rule_clause:
                if not rule_clause[CS("Enabled")]:
                    continue

            ##################################################################
            #
            # Open the local scope and track matches.
            #
            ##################################################################

            local_vars = {}
            matches = []
            inverted_matches = []

            ##################################################################
            #
            # Load the description and metadata.
            #
            ##################################################################

            description = rule_clause[CS("Description")]
            metadata = rule_clause[CS("Metadata")] if CS("Metadata") in rule_clause else {}

            ##################################################################
            #
            # Check each match for validity.
            #
            ##################################################################

            for match_clause in rule_clause[CS("MatchAll")]:
                match = {}

                fact = match_clause[CS("Fact")]
                if fact not in facts:
                    raise Exception("Unknown fact '%s'" % fact)
                match["fact"] = fact

                match["meaning"] = match_clause[CS("meaning")] if CS("meaning") in match_clause else None

                match["when"] = evaluate(match_clause[CS("when")], local_vars, facts[fact]) if CS("when") in match_clause else None
                if match["when"] is not None:
                    if not isinstance(match["when"], JoinNode):
                        if not isinstance(match["when"], BinaryOpNode) or not isinstance(match["when"].arg1, ThisReferenceNode):
                            raise Exception("Predicate of match is not a joinable predicate (%s)" % match["when"])

                match["assignments"] = {}
                if CS("Assign") in match_clause:
                    for assignment, value in match_clause[CS("Assign")].items():
                        if assignment in local_vars:
                            raise Exception("Duplicate assignment to '%s'" % assignment)

                        value = evaluate(value, local_vars, facts[fact])
                        match["assignments"][assignment] = value
                        local_vars[assignment] = type(value) if not isinstance(value, Node) else value.type

                matches.append(match)

            ##################################################################
            #
            # Check each inverted match for validity.
            #
            ##################################################################

            if CS("MatchNone") in rule_clause:
                for match_clause in rule_clause[CS("MatchNone")]:
                    match = {}

                    fact = match_clause[CS("Fact")]
                    if fact not in facts:
                        raise Exception("Unknown fact '%s'" % fact)
                    match["fact"] = fact

                    match["meaning"] = match_clause[CS("meaning")] if CS("meaning") in match_clause else None

                    match["when"] = evaluate(match_clause[CS("when")], local_vars, facts[fact]) if CS("when") in match_clause else None
                    if match["when"] is not None:
                        if not isinstance(match["when"], JoinNode):
                            if not isinstance(match["when"], BinaryOpNode) or not isinstance(match["when"].arg1, ThisReferenceNode):
                                    raise Exception("Predicate of match is not a joinable predicate")

                    inverted_matches.append(match)

            ##################################################################
            #
            # Check the production clause for validity.
            #
            ##################################################################

            final_predicate = True
            if CS("When") in rule_clause:
                final_predicate = evaluate(rule_clause[CS("When")], local_vars)
                final_type = final_predicate.type if isinstance(final_predicate, Node) else type(final_predicate)
                if final_type is not bool:
                    raise Exception("Rule final predicates must be of boolean type.")

            if CS("Assert") in rule_clause:
                produced_fields = {}
                produced_fact = None
                distinct = isinstance(rule_clause[CS("Assert")], DistinctProduction)

                for produced_fact, fields in rule_clause[CS("Assert")].items():
                    if produced_fact not in facts:
                        raise Exception("Unknown fact '%s'" % produced_fact)

                    if produced_fact in parameters:
                        raise Exception("Parameter facts cannot be produced")

                    produced_fields = {CS(k): None for k in facts[produced_fact].keys()}

                    for assignment, value in fields.items():
                        if assignment not in facts[produced_fact]:
                            raise Exception("Unknown field '%s' in production clause" % assignment)

                        produced_fields[assignment] = evaluate(value, local_vars)

                        assigned_type = produced_fields[assignment].type if isinstance(
                            produced_fields[assignment], Node) else type(produced_fields[assignment])
                        if assigned_type != facts[produced_fact][assignment]:
                            raise Exception("Result of expression and field type do not agree in production of '%s'" % assignment)

                    for k, v in produced_fields.items():
                        if v is None:
                            raise Exception("Field '%s' unassigned in production" % k)

                if distinct:
                    if len(facts[produced_fact]) <= 0:
                        raise Exception("Only facts with fields may be distinctly produced")

                    distincts.add(produced_fact)

                rules[rule_name] = {
                    "locals": local_vars,
                    "matches": matches,
                    "inverted_matches": inverted_matches,
                    "description": description,
                    "distinct": distinct,
                    "final_predicate": final_predicate,
                    "produced_fact": produced_fact,
                    "produced_fields": produced_fields,
                    "metadata": metadata
                }

            ##################################################################
            #
            # Check the suppression clause for validity.
            #
            ##################################################################

            else:
                suppressed_fact = rule_clause[CS("Suppress")][CS("Fact")]
                if suppressed_fact not in facts:
                    raise Exception("Unknown fact '%s'" % suppressed_fact)

                if suppressed_fact in parameters:
                    raise Exception("Parameter facts cannot be suppressed")

                suppressed_when = evaluate(rule_clause[CS("Suppress")][CS("When")], local_vars, facts[suppressed_fact])

                rules[rule_name] = {
                    "locals": local_vars,
                    "matches": matches,
                    "inverted_matches": inverted_matches,
                    "description": description,
                    "final_predicate": final_predicate,
                    "suppressed_fact": suppressed_fact,
                    "suppressed_when": suppressed_when,
                    "metadata": metadata
                }

        except Exception as e:
            error("Error processing rule '%s': %s" % (rule_name, e))

    ######################################################################
    #
    # Make sure we actually have some rules defined. This is mostly
    # taken care of by the schema validation, but not entirely - we could
    # have explicitly disabled every rule.
    #
    ######################################################################

    if len(rules) == 0:
        error("At least one rule must be defined and active.")

    ######################################################################
    #
    # Check to ensure no suppression of distinct productions is happening.
    # We can't allow this because it could lead to infinite loops.
    #
    ######################################################################

    for rule_name, rule_clause in rules.items():
        if "suppressed_fact" in rule_clause and rule_clause["suppressed_fact"] in distincts:
            error("Rule %s attempts to suppress facts of type '%s', which are produced distinctly by some rule(s)." %
                  (rule_name, rule_clause["suppressed_fact"]))

    ######################################################################
    #
    # Build a list of all facts that are produced but not matched; these
    # are implicitly marked as !output.
    #
    ######################################################################

    only_produced = set([])
    for rule_name, rule_clause in rules.items():
        if "produced_fact" in rule_clause:
            only_produced.add(rule_clause["produced_fact"])

        if "suppressed_fact" in rule_clause:
            only_produced.add(rule_clause["suppressed_fact"])

    for rule_name, rule_clause in rules.items():
        for match_clause in rule_clause["matches"]:
            only_produced.discard(match_clause["fact"])

        for match_clause in rule_clause["inverted_matches"]:
            only_produced.discard(match_clause["fact"])

    for fact in only_produced:
        facts[CS(fact)] = OutputFact(facts[CS(fact)])

    ######################################################################
    #
    # Check for cycles.
    # This is necessary because cycles can result in infinitely recursive
    # productions or retractions. By default, many database engines don't
    # support recursive triggers, which would lead to undefined behavior;
    # on those databases that can support them or support them in their
    # default configurations, this test can be disabled with the proviso
    # that the user can shoot him- or herself in the foot.
    #
    # This is implemented using Van Rossum's algorithm, which is
    # particularly elegant when implemented in Python (unsurprisingly).
    #
    ######################################################################

    if arguments.check_cycles:
        def find_cycle(nodes, edges):
            todo = set(nodes)

            while len(todo) > 0:
                node = todo.pop()
                stack = [node]

                while len(stack) > 0:
                    top = stack[-1]
                    for node in edges(top):
                        if node in stack:
                            return stack[stack.index(node):]

                        if node in todo:
                            stack.append(node)
                            todo.remove(node)
                            break

                    else:
                        node = stack.pop()

            return None

        def find_reachable(rule):
            produced = rules[rule]["produced_fact"] if "produced_fact" in rules[rule] else rules[rule]["suppressed_fact"]
            reachable = set([])

            for other_rule, rule_clause in rules.items():
                if produced in [x["fact"] for x in rule_clause["matches"] + rule_clause["inverted_matches"]]:
                    reachable.add(other_rule)

            return reachable

        cycle = find_cycle(rules.keys(), find_reachable)
        if cycle is not None:
            error("A cycle exists in the rule set: %s" % " -> ".join(cycle))

    ######################################################################
    #
    # Pass them to the backend if we encountered no errors.
    #
    ######################################################################

    if errors > 0:
        sys.exit(1)

    try:
        description = document[CS("Description")] if CS("Description") in document else ""
        arguments.schema_file.write(backends[arguments.backend].generate(arguments.prefix, ",".join(x.name for x in arguments.files),
                                                                         description, facts, parameters, rules))
        arguments.schema_file.close()
        sys.exit(0)

    except Exception as e:
        sys.stderr.write("Compilation failed: %s" % e)
        sys.exit(1)
