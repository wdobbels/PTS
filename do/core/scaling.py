#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package do.scaling Test the scaling of SKIRT on a particular system
#

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import os.path
import argparse

# Import the relevant PTS classes and modules
from pts.core.test import ScalingTest

# -----------------------------------------------------------------

# Create the command-line parser and a set of subparsers
parser = argparse.ArgumentParser()
parser.add_argument('system', type=str, help='a name identifying the system')
parser.add_argument('simulation', type=str, help='the name of the simulation to use for the test')
parser.add_argument('mode', type=str, help='the mode for the scaling test', choices=['mpi', 'hybrid', 'threads'])
parser.add_argument('maxnodes', type=float, help='the maximum number of nodes', nargs='?', default=1)
parser.add_argument('minnodes', type=float, help='the minimum number of nodes. In hybrid mode, this also defines the number of threads per process', nargs='?', default=0)
parser.add_argument('--man', action='store_true', help='launch and inspect job scripts manually')
parser.add_argument('--keep', action='store_true', help='keep the output generated by the different SKIRT jobs')
parser.add_argument('--progress', action='store_true', help='after a job finished, extract the progress of the different processes')
parser.add_argument('--timeline', action='store_true', help='after a job finished, extract the timeline information')
parser.add_argument('--weak', action='store_true', help='test weak scaling instead of strong scaling')

# Parse the command line arguments
args = parser.parse_args()

# Set the command-line options
system = args.system
simulation = args.simulation
mode = args.mode
maxnodes = args.maxnodes
minnodes = args.minnodes
manual = args.man
keepoutput = args.keep
extractprogress = args.progress
extracttimeline = args.timeline
weak = args.weak

# -----------------------------------------------------------------

# Set the path for the scaling test
scalingname = "SKIRTscaling"
scalingpath = os.path.join(os.getenv("HOME"), scalingname)

# -----------------------------------------------------------------

# Run the test
test = ScalingTest(scalingpath, simulation, system, mode)
test.run(maxnodes, minnodes, manual, keepoutput, extractprogress, extracttimeline, weak)

# -----------------------------------------------------------------
