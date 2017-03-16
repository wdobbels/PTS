#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from pts.core.remote.host import find_host_ids
from pts.modeling.tests.base import possible_free_parameters, default_free_parameters

# -----------------------------------------------------------------

# Create definition
definition = ConfigurationDefinition(write_config=False)

# Optional settings
definition.add_optional("nwavelengths", "positive_integer", "number of wavelengths for the reference simulation", 40)
definition.add_optional("npackages", "positive_integer", "number of photon packages per wavelength for the reference simulation", int(1e4))
definition.add_optional("dust_grid_relative_scale", "real", "smallest scale of the dust grid relative to the pixelscale of the input maps", 10.)
definition.add_optional("dust_grid_min_level", "positive_integer", "level for the dust grid", 0)
definition.add_optional("dust_grid_max_mass_fraction", "positive_real", "max mass fraction for the dust grid", 1e-5)

# Flags
definition.add_flag("transient_heating", "enable transient heating", False)
definition.add_flag("selfabsorption", "enable dust selfabsorption", False)

# For remote execution of reference simulation
#definition.add_optional("host_ids", "string_list", "remote hosts to use for heavy computations (in order of preference)", choices=find_host_ids(schedulers=False))

# Fitting
definition.add_optional("ngenerations", "positive_integer", "number of generations", 5)
definition.add_optional("nsimulations", "positive_integer", "number of simulations per generation", 30)

# Free parameters
definition.add_optional("free_parameters", "string_list", "free parameter labels", choices=possible_free_parameters, default=default_free_parameters)

# Wavelength grid
definition.add_optional("wavelength_range", "quantity_range", "range of wavelengths", "0.1 micron > 2000 micron", convert_default=True)

# Dust grid
definition.add_optional("physical_domain_disk_ellipse_factor", "positive_real", "factor of the disk ellipse region to take as the physical domain of the model", 0.82)

# -----------------------------------------------------------------
