#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.evolve.analyse.database Contains functions for analysing the database

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import sqlite3

# Import the relevant PTS classes and modules
from ...core.tools import types
from ...core.basics.map import Map

# -----------------------------------------------------------------

# STATISTICS:
# "rawMax": "Maximum raw score",
# "rawMin": "Minimum raw score",
# "rawAve": "Average of raw scores",
# "rawDev": "Standard deviation of raw scores",
# "rawVar": "Raw scores variance",
# "fitMax": "Maximum fitness",
# "fitMin": "Minimum fitness",
# "fitAve": "Fitness average",

# -----------------------------------------------------------------

def load_database(path):

    """
    This function ...
    :param path: 
    :return: 
    """

    # Connect to the database
    conn = sqlite3.connect(path)

    # Creating rows
    conn.row_factory = sqlite3.Row

    # Create cursor
    c = conn.cursor()

    # Return the cursor
    return c

# -----------------------------------------------------------------

def get_runs(database):

    """
    This function ...
    :param database: 
    :return: 
    """

    if types.is_string_type(database): database = load_database(database)

    # Select
    ret = database.execute("select distinct identify from population")
    runs = ret.fetchall()

    # Return the runs
    return [run[0] for run in runs]

# -----------------------------------------------------------------

def get_generations(database, run_id):

    """
    This function ...
    :param database: 
    :param run_id: 
    :return: 
    """

    if types.is_string_type(database): database = load_database(database)

    # Select multiple generations
    ret = database.execute("select distinct generation from population where identify = ?", [run_id])
    generations = ret.fetchall()

    # Return the generation numbers
    return [gen[0] for gen in generations]

# -----------------------------------------------------------------

def get_individuals(database, run_id, generation, individual_range=None):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation: 
    :param individual_range:
    :return: 
    """

    # Get the cursor
    if types.is_string_type(database): database = load_database(database)

    if individual_range is not None:
        ret = database.execute("""
                             select *  from population
                             where identify = ?
                             and generation = ?
                             and individual between ? and ?
                             """, (run_id, generation, individual_range.min, individual_range.max))
    else:
        ret = database.execute("""
                           select *  from population
                           where identify = ?
                           and generation = ?
                           """, (run_id, generation))

    ret_fetch = ret.fetchall()

    if len(ret_fetch) == 0: raise RuntimeError("No individuals found in the range")

    return ret_fetch

# -----------------------------------------------------------------

def get_scores_named_individuals(database, run_id, generation):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation: 
    :return: 
    """

    scores = dict()

    # Loop over the individuals
    for it in get_individuals(database, run_id, generation):

        # Get name
        name = it["individual"]

        # Get score
        raw = it["raw"]

        # Add the score
        scores[name] = raw

    # Return the scores dictionary
    return scores

# -----------------------------------------------------------------

def get_scores(database, run_id, generation):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation: 
    :return: 
    """

    scores = []

    # Loop over the individuals
    for it in get_individuals(database, run_id, generation):

        # Get score
        raw = it["raw"]

        # Add the score
        scores.append(raw)

    # Return the scores
    return scores

# -----------------------------------------------------------------

def get_fitnesses(database, run_id, generation):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation: 
    :return: 
    """

    fitnesses = []

    # Loop over the individuals
    for it in get_individuals(database, run_id, generation):

        # Get score
        fitness = it["fitness"]

        # Add the score
        fitnesses.append(fitness)

    # Return the scores
    return fitnesses

# -----------------------------------------------------------------

def get_populations(database, run_id, generation_range=None):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation_range:
    :return: 
    """

    # Get the cursor
    if types.is_string_type(database): database = load_database(database)

    # Range of generations is given
    if generation_range is not None: ret = database.execute("select * from statistics where identify = ? and generation between ? and ?", (run_id, generation_range.min, generation_range.max))

    # No range of generations is given
    else: ret = database.execute("select * from statistics where identify = ?", (run_id,))

    # Get
    pop = ret.fetchall()

    # Return the populations
    return pop

# -----------------------------------------------------------------

def get_population(database, run_id, generation):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation: 
    :return: 
    """

    # Get the cursor
    if types.is_string_type(database): database = load_database(database)

    # Get
    ret = database.execute("select * from statistics where identify = ? and generation = ?", (run_id, generation))
    pop = ret.fetchall()

    # Return the population
    return pop[0]

# -----------------------------------------------------------------

def get_statistics(database, run_id, generation):

    """
    This function ...
    :param database: 
    :param run_id: 
    :param generation: 
    :return: 
    """

    # Create mapping
    statistics = Map()

    # Get the population
    pop = get_population(database, run_id, generation)

    # Set stats of raw scores
    statistics.raw = Map()
    statistics.raw.average = pop["rawAve"]
    statistics.raw.min = pop["rawMin"]
    statistics.raw.max = pop["rawMax"]
    statistics.raw.stddev = pop["rawDev"]

    # Set stats of fitnesses
    statistics.fitness = Map()
    statistics.fitness.average = pop["fitAve"]
    statistics.fitness.min = pop["fitMin"]
    statistics.fitness.max = pop["fitMax"]
    #statistics.fitness.stddev = pop["fitDev"]

    # Return the statistics
    return statistics

# -----------------------------------------------------------------
