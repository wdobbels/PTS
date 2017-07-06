#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.modeling.upload_status Upload the status page.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition, parse_arguments
from pts.core.tools import filesystem as fs
from pts.modeling.core.environment import GalaxyModelingEnvironment
from pts.modeling.html.generator import HTMLGenerator

# -----------------------------------------------------------------

# Create configuration
definition = ConfigurationDefinition()
definition.add_flag("generate", "first (re)generate the HTML", False)
config = parse_arguments("upload_status", definition)

# -----------------------------------------------------------------

modeling_path = fs.cwd()

# -----------------------------------------------------------------

# Load the modeling environment
environment = GalaxyModelingEnvironment(modeling_path)

# -----------------------------------------------------------------

# Generate the HTML
if config.generate:

    # Generate the HTML
    generator = HTMLGenerator()
    generator.config.path = modeling_path
    generator.run()

# -----------------------------------------------------------------

# -----------------------------------------------------------------
