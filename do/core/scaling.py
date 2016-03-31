#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.core.scaling Test the scaling of SKIRT on a particular system
#

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import argparse

# Import the relevant PTS classes and modules
from pts.core.test.scaling import ScalingTest
from pts.core.tools import logging, time

# -----------------------------------------------------------------

# Create the command-line parser and a set of subparsers
parser = argparse.ArgumentParser()
parser.add_argument("file", type=str, help="the name of the ski file to use for the scaling test")
parser.add_argument("remote", type=str, help="the name of the remote host")
parser.add_argument("mode", type=str, help="the parallelization mode for the scaling test", choices=["mpi", "hybrid", "threads"])
parser.add_argument("maxnodes", type=float, help="the maximum number of nodes", nargs='?', default=1)
parser.add_argument("minnodes", type=float, help="the minimum number of nodes. In hybrid mode, this also defines the number of threads per process", nargs='?', default=0)
parser.add_argument("--cluster", type=str, help="add the name of the cluster if different from the default")
parser.add_argument("--manual", action="store_true", help="launch and inspect job scripts manually")
parser.add_argument("--keep", action="store_true", help="keep the output generated by the different SKIRT simulations")
parser.add_argument("--debug", action="store_true", help="add this option to enable debug output")
parser.add_argument("--report", action="store_true", help="write a report file")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = os.path.join(os.getcwd(), time.unique_name("scaling") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.start("Starting scaling test procedure ...")

# -----------------------------------------------------------------

# Determine the full path to the ski file
arguments.filepath = os.path.abspath(arguments.file)

# Create a ScalingTest instance initialized with the command-line arguments
test = ScalingTest.from_arguments(arguments)

# Run the scaling test
test.run()

# -----------------------------------------------------------------
