#!/usr/bin/env python3
# coding=utf-8
######################################################################
#
# $Id: 86ab295a13893bedc328583380980f633ff0ef52 $
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
# Purpose: Generate a SQLite database schema from a Giles engine
#          description.
#
######################################################################

"""Giles backend for SQLite."""

__author__ = "Rob King"
__copyright__ = "Copyright (C) 2011-2014 KoreLogic, Inc. All Rights Reserved."
__credits__ = []
__license__ = "See README.LICENSE."
__version__ = "$Id: 86ab295a13893bedc328583380980f633ff0ef52 $"
__maintainer__ = "Rob King"
__email__ = "rking@korelogic.com"
__status__ = "Alpha"

import datetime
import jinja2

from pkg_resources import resource_string
from giles import expression
from giles.caseless_string import CaselessString as CS
from itertools import chain

######################################################################
#
# Globals used in this module.
#
######################################################################

domains = {}      # Domains for the only_once routines
prefix = "giles"  # Default prefix for object names
indexes = {}      # The indexes on each fact table

######################################################################
#
# Transform a Giles expression into a SQL expression.
#
######################################################################


def generate_expression(value, fact, frame_prefix=None, fact_prefix=None):
    """
    value        - the expression or value to SQLize
    fact        - the fact being matched
    frame_prefix - frame prefix
    fact_prefix - fact prefix
    """

    if type(value) in (float, int):
        return str(value)

    elif type(value) == bool:
        return "1" if value else "0"

    elif type(value) == str:
        return "'%s'" % value.replace("'", "''")

    elif isinstance(value, expression.ThisReferenceNode):
        return '%s%s' % ((fact_prefix + '.') if fact_prefix else '', value.variable)

    elif isinstance(value, expression.LocalReferenceNode):
        return '%s%s' % ((frame_prefix + '.') if frame_prefix else '', value.variable)

    elif isinstance(value, expression.BinaryOpNode):
        return "(%s) %s (%s)" % (generate_expression(value.arg1, fact, frame_prefix, fact_prefix),
                                 value.operation,
                                 generate_expression(value.arg2, fact, frame_prefix, fact_prefix))

    elif isinstance(value, expression.UnaryOpNode):
        return "(%s(%s))" % (value.operation, generate_expression(value.arg1, fact, frame_prefix, fact_prefix))

    elif isinstance(value, expression.IfNode):
        return "(CASE WHEN (%s) THEN (%s) ELSE (%s) END)" % (generate_expression(value.predicate, fact, frame_prefix, fact_prefix),
                                                             generate_expression(value.if_true, fact, frame_prefix, fact_prefix),
                                                             generate_expression(value.if_false, fact, frame_prefix, fact_prefix))

    elif isinstance(value, expression.FunctionNode):
        return "%s(%s)" % (value.external, ",".join(generate_expression(x, fact, frame_prefix, fact_prefix) for x in value.args))

    elif isinstance(value, expression.CastNode):
        kind = {bool: "integer", int: "integer", float: "real", str: "text"}[value.type]
        return "CAST((%s) AS %s)" % (generate_expression(value.expression, fact, frame_prefix, fact_prefix), kind)

    elif isinstance(value, expression.JoinNode):
        tests = []
        equality_tests = []
        inequality_tests = []

        def flatten(node):
            if not isinstance(node, expression.JoinNode):
                tests.append(node)

            else:
                flatten(node.left)
                flatten(node.right)

        flatten(value)

        for test in tests:
            if isinstance(test, expression.BinaryOpNode) and test.operation == "=":
                equality_tests.append(generate_expression(test, fact, frame_prefix, fact_prefix))

            else:
                inequality_tests.append(generate_expression(test, fact, frame_prefix, fact_prefix))

        return " AND ".join(equality_tests + inequality_tests)

    assert False

######################################################################
#
# Generate a predicate for a match. This takes all the constant
# tests against a given match and applies them.
#
######################################################################


def flatten_predicate(when):
    predicates = []

    if isinstance(when, expression.JoinNode):
        predicates += flatten_predicate(when.left)
        predicates += flatten_predicate(when.right)

    elif isinstance(when, expression.BinaryOpNode) and when.type == bool and \
            isinstance(when.arg1, expression.ThisReferenceNode) and len(find_locals(when.arg2)) == 0:
        predicates.append(when)

    return predicates


def generate_predicate_wrapper(fact, when):
    results = generate_predicate(fact, when)
    if len(results) == 0:
        return "1"
    else:
        return " AND ".join(results)


def generate_predicate(fact, when):
    """
    fact - the fact being matched
    when  - the predicate
    """

    tests = flatten_predicate(when)
    tests.sort(key=lambda x: str(x.arg1.variable).lower())

    return [generate_expression(x, fact, None, 'new') for x in tests]

######################################################################
#
# Generate a list of locals used in an expression.
#
######################################################################


def find_locals(value):
    if isinstance(value, expression.LocalReferenceNode):
        return [value.variable]

    elif isinstance(value, expression.BinaryOpNode):
        return find_locals(value.arg1) + find_locals(value.arg2)

    elif isinstance(value, expression.UnaryOpNode):
        return find_locals(value.arg1)

    elif isinstance(value, expression.IfNode):
        return find_locals(value.predicate) + find_locals(value.if_true) + find_locals(value.if_false)

    elif isinstance(value, expression.FunctionNode):
        local_vars = []
        for arg in value.args:
            local_vars += find_locals(arg)
        return local_vars

    elif isinstance(value, expression.CastNode):
        return find_locals(value.expression)

    elif isinstance(value, expression.JoinNode):
        return find_locals(value.left) + find_locals(value.right)

    else:
        return []

######################################################################
#
# Add an index for a table. If an index already exists for that table
# that is a superset of this index, there is no need to generate a new
# index; the longer one will be used. Note that for the purposes of
# determining the superset relation, field order is significant
# (because SQLite's query optimizer will only apply an index if the
# list of indexed fields is in the same order as the fields were
# specified in the query).
#
######################################################################


def add_index(table, fields):
    table = table.lower()

    if len(fields) == 0:
        return

    if table not in indexes:
        indexes[table] = {}

    current = indexes[table]
    for field in fields:
        if field not in current:
            current[field] = {}
        current = current[field]

######################################################################
#
# Generate a join expression. This takes all of the tests against
# a given fact and applies them (optionally excluding the constant
# tests). Equalities are sorted and placed in front of any
# inequalities, which allows for better index usage and query
# optimization.
#
######################################################################


def generate_join(when, fact, frame_prefix=None, fact_prefix=None, include_constants=True):
    result = ""
    equalities = []
    inequalities = []

    if fact_prefix is not None:
        fact_prefix = fact_prefix.lower()

    if frame_prefix is not None:
        frame_prefix = frame_prefix.lower()

    def flatten(n):
        if isinstance(n, expression.JoinNode):
            flatten(n.left)
            flatten(n.right)

        elif isinstance(n, expression.BinaryOpNode) and n.type == bool and isinstance(n.arg1, expression.ThisReferenceNode):
            if type(n.arg2) not in (bool, float, int, str) or include_constants:
                if n.operation == "=":
                    equalities.append(n)

                else:
                    inequalities.append(n)

    flatten(when)

    equalities.sort(key=lambda x: str(x.arg1.variable).lower())
    inequalities.sort(key=lambda x: str(x.arg1.variable).lower())

    equality_predicate = " AND ".join([generate_expression(predicate, fact, frame_prefix, fact_prefix).strip() for predicate in equalities])
    inequality_predicate = " AND ".join(
        [generate_expression(predicate, fact, frame_prefix, fact_prefix).strip() for predicate in inequalities])

    result = equality_predicate + \
        (" AND " if len(equality_predicate.strip()) and len(inequality_predicate.strip()) else "") + inequality_predicate
    if len(result.strip()) == 0:
        return None

    if frame_prefix not in ('new', 'old'):  # Don't add indexes for expressions over immediately-available data (i.e. new/old frames/facts)
        equality_variables = []
        for predicate in equalities:
            equality_variables += find_locals(predicate)

        if len(inequalities) > 0:
            add_index(frame_prefix, equality_variables + find_locals(inequalities[0]))

        elif len(equality_variables) > 0:
            add_index(frame_prefix, equality_variables)

    if fact_prefix not in ('new', 'old'):  # Don't add indexes for expressions over immediately-available data (i.e. new/old frames/facts)
        equality_variables = []
        for predicate in equalities:
            equality_variables.append(predicate.arg1.variable)

        if len(inequalities) > 0:
            add_index(fact_prefix, equality_variables + [inequalities[0].arg1.variable])

        elif len(equality_variables) > 0:
            add_index(fact_prefix, equality_variables)

    return result

######################################################################
#
# Print out a value only when called with it the first time.
# Subsequent times, print out nothing. "Once" is determined by a
# combination of the value to print and the "domain" in which it is
# printing.
#
######################################################################


def only_once(domain, value):
    domain = domain.lower()

    if domain not in domains:
        domains[domain] = {}

    if value not in domains[domain]:
        domains[domain][value] = True
        return value

    return ''

######################################################################
#
# Generate a synthetic assignment for predicates specified over locals
# in later match clauses.
#
######################################################################


def flatten_local_predicates(when):
    predicates = []

    if isinstance(when, expression.JoinNode):
        predicates += flatten_local_predicates(when.left)
        predicates += flatten_local_predicates(when.right)

    elif isinstance(when, expression.BinaryOpNode) and when.type == bool and \
            isinstance(when.arg1, expression.ThisReferenceNode) and len(find_locals(when.arg2)) > 0:
        predicates.append(when)

    return predicates


def immediate_substitute(predicate, used_var, actual):
    if isinstance(predicate, expression.BinaryOpNode):
        if isinstance(predicate.arg1, expression.LocalReferenceNode) and predicate.arg1.variable == used_var:
            predicate.arg1 = actual

        else:
            immediate_substitute(predicate.arg1, used_var, actual)

        if isinstance(predicate.arg2, expression.LocalReferenceNode) and predicate.arg2.variable == used_var:
            predicate.arg2 = actual

        else:
            immediate_substitute(predicate.arg2, used_var, actual)

    elif isinstance(predicate, expression.UnaryOpNode):
        if isinstance(predicate.arg1, expression.LocalReferenceNode) and predicate.arg1.variable == used_var:
            predicate.arg1 = actual

        else:
            immediate_substitute(predicate.arg1, used_var, actual)

    elif isinstance(predicate, expression.IfNode):
        if isinstance(predicate.predicate, expression.LocalReferenceNode) and predicate.predicate.variable == used_var:
            predicate.predicate = actual

        else:
            immediate_substitute(predicate.predicate, used_var, actual)

        if isinstance(predicate.if_true, expression.LocalReferenceNode) and predicate.if_true.variable == used_var:
            predicate.if_true = actual

        else:
            immediate_substitute(predicate.if_true, used_var, actual)

        if isinstance(predicate.if_false, expression.LocalReferenceNode) and predicate.if_false.variable == used_var:
            predicate.if_false = actual

        else:
            immediate_substitute(predicate.if_false, used_var, actual)

    elif isinstance(predicate, expression.FunctionNode):
        for i, arg in enumerate(predicate.args):
            if isinstance(arg, expression.LocalReferenceNode) and arg.variable == used_var:
                predicate.args[i] = actual

            else:
                immediate_substitute(predicate.args[i], used_var, actual)

    elif isinstance(predicate, expression.CastNode):
        if isinstance(predicate.expression, expression.LocalReferenceNode) and predicate.expression.variable == used_var:
            predicate.expression = actual

        else:
            immediate_substitute(predicate.expression, used_var, actual)


def generate_synthetic_assignment(predicate, rule, prev_clause, synthetic_name):
    synthetic_name = CS(synthetic_name)
    if "locals" not in rule:
        rule["locals"] = {}

    if "assignments" not in prev_clause:
        prev_clause["assignments"] = {}

    rule["locals"][synthetic_name] = predicate.type

    used_vars = set(find_locals(predicate))
    for used_var in used_vars.intersection(prev_clause["assignments"]):
        immediate_substitute(predicate, used_var, prev_clause["assignments"][used_var])

    prev_clause["assignments"][synthetic_name] = predicate

######################################################################
#
# Generate the SQL.
#
######################################################################


def generate(new_prefix, filename, description, facts, parameters, rules):
    ####################################################################
    #
    # Reset global state.
    #
    ####################################################################

    global domains
    global prefix
    global indexes

    domains = {}
    prefix = "giles"
    indexes = {}

    ####################################################################
    #
    # Set global options.
    #
    ####################################################################

    prefix = "_" + new_prefix

    ####################################################################
    #
    # Mark as output any fact with an always-true predicate.
    # This saves a lot of time on the alpha pruning phase.
    #
    ####################################################################

    class OutputFact(dict):
        is_output = True

    for rule_clause in rules.values():
        for match in rule_clause["matches"] + rule_clause["inverted_matches"]:
            predicate = generate_predicate(match["fact"], match["when"])
            if len(predicate) == 0:
                facts[CS(match["fact"])] = OutputFact(facts[CS(match["fact"])])

    ####################################################################
    #
    # Optimize any match clauses that have expressions using assignments
    # from earlier match clauses.
    #
    ####################################################################

    synthetic_assignment_count = 0
    for rule_name, rule in rules.items():
        for i, match_clause in enumerate(rule["matches"]):
            if "assignments" in match_clause:
                assignments = set(match_clause["assignments"].keys())
                for j, subsequent_clause in enumerate(chain(rule["matches"][i + 1:], rule["inverted_matches"])):
                    if subsequent_clause["when"] is not None:
                        clauses = flatten_local_predicates(subsequent_clause["when"])
                        for clause in clauses:
                            used_vars = set(find_locals(clause))
                            if used_vars.intersection(assignments):
                                if not isinstance(clause.arg2, expression.LocalReferenceNode):
                                    synthetic_assignment_count += 1
                                    synthetic_name = "synthetic_assignment_%d" % synthetic_assignment_count
                                    prev_clause = rule["matches"][j - 2]
                                    generate_synthetic_assignment(clause.arg2, rule, prev_clause, synthetic_name)
                                    clause.arg2 = expression.LocalReferenceNode(synthetic_name, clause.arg2.type)

    ####################################################################
    #
    # Open the template and run it.
    #
    ####################################################################

    template_file = resource_string(__name__, 'sqlite.jinja').decode('utf-8')
    env = jinja2.Environment(loader=jinja2.FunctionLoader(lambda x: (template_file, 'sqlite.jinja', lambda: template_file)))
    template = env.get_template('sqlite.jinja')

    names = {
        "generate_join": generate_join,
        "generate_expression": generate_expression,
        "generate_predicate": generate_predicate_wrapper,
        "description": description,
        "facts": facts,
        "file": filename,
        "parameters": parameters,
        "only_once": only_once,
        "prefix": prefix,
        "public_prefix": new_prefix,
        "rules": rules,
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
        "time": str(datetime.datetime.now())
    }

    result = template.render(**names)

    ####################################################################
    #
    # Spit out all the automatically-created indexes.
    #
    ####################################################################

    index_number = 0

    def dft(tree, leaf_callback, path=None):
        path = [] if path is None else path
        if len(tree) == 0:
            leaf_callback(path)

        else:
            for k, v in tree.items():
                dft(v, leaf_callback, path + [k])

    def callback(table, path):
        nonlocal index_number
        nonlocal result

        index_number += 1
        result += "\nCREATE INDEX %s_auto_index_%d ON %s(%s);" % (prefix, index_number, table, ",".join(path))

    for table, tree in indexes.items():
        dft(tree, lambda path: callback(table, path))

    return result
