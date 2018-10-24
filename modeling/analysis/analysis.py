#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.analysis.analysis Contains the Analysis class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from collections import OrderedDict

# Import the relevant PTS classes and modules
from ...core.tools.utils import lazyproperty, memoize_method
from .component import AnalysisRunComponent
from ...core.basics.configurable import InteractiveConfigurable
from ...core.basics.log import log
from ...core.tools import formatting as fmt
from ...core.tools.stringify import tostr
from ...core.basics.configuration import ConfigurationDefinition
from ...core.plot.wavelengthgrid import plot_wavelength_grid
from ...core.plot.grids import make_grid_plot
from ...core.tools import filesystem as fs
from ...core.tools import introspection
from ..core.environment import load_modeling_environment
from .absorption.absorption import AbsorptionAnalyser
from ..config.analyse_absorption import definition as analyse_absorption_definition
from ...core.plot.sed import plot_seds, SEDPlotter, plot_sed
from ...core.config.plot_seds import definition as plot_seds_definition
from ..config.evaluate_analysis import definition as evaluate_analysis_definition
from ...core.plot.attenuation import plot_attenuation_curve, plot_attenuation_curves
from ..config.analyse_cell_heating import definition as analyse_cell_heating_definition
from ..config.analyse_projected_heating import definition as analyse_projected_heating_definition
from ..config.analyse_spectral_heating import definition as analyse_spectral_heating_definition
from ..config.analyse_images import definition as analyse_images_definition
from ..config.analyse_fluxes import definition as analyse_fluxes_definition
from ..config.analyse_residuals import definition as analyse_residuals_definition
from .heating.cell import CellDustHeatingAnalyser
from .heating.projected import ProjectedDustHeatingAnalyser
from .heating.spectral import SpectralDustHeatingAnalyser
from .images import ImagesAnalyser
from .fluxes import FluxesAnalyser
from .residuals import ResidualAnalyser
from ..config.analyse_properties import definition as analyse_properties_definition
from .properties import PropertiesAnalyser
from ..config.analyse_cell_energy import definition as analyse_cell_energy_definition
from ..config.analyse_projected_energy import definition as analyse_projected_energy_definition
from .energy.cell import CellEnergyAnalyser
from .energy.projected import ProjectedEnergyAnalyser
from ...magic.tools.plotting import plot_frame, plot_frame_contours, plot_datacube, plot_curve, plot_curves, plot_scatters_astrofrog, plot_scatter_astrofrog
from ...core.filter.filter import Filter, parse_filter
from ...core.tools import types
from ...magic.plot.imagegrid import StandardImageGridPlotter, ResidualImageGridPlotter
from .evaluation import AnalysisModelEvaluator
from ...core.tools import sequences
from .correlations import CorrelationsAnalyser
from ..misc.examination import ModelExamination
from ..config.analyse_correlations import definition as analyse_correlations_definition
from ..config.analyse_sfr import definition as analyse_sfr_definition
from .sfr import SFRAnalyser
from ...core.units.parsing import parse_unit as u
from ...core.data.sed import SED
from ...magic.core.dataset import StaticDataSet
from ...core.basics.distribution import Distribution
from ...core.basics.plot import MPLFigure
from ...core.units.parsing import parse_quantity as q
from ...core.units.quantity import PhotometricQuantity
from ...core.data.sed import ObservedSED
from ..fitting.modelanalyser import FluxDifferencesTable
from ...core.tools.parsing import lazy_broad_band_filter_list
from ...magic.core.frame import Frame
from ...magic.core.mask import Mask
from ...magic.tools.plotting import plot_map, plot_map_offset
from ...core.basics.curve import WavelengthCurve
from ...core.plot.distribution import plot_distribution
from ...magic.core.list import uniformize
from ...core.basics.scatter import Scatter2D

from .properties import bol_map_name, intr_stellar_map_name, obs_stellar_map_name, diffuse_dust_map_name, dust_map_name
from .properties import scattered_map_name, absorbed_diffuse_map_name, fabs_diffuse_map_name, fabs_map_name, stellar_mass_map_name, ssfr_map_name
from .properties import attenuated_map_name, direct_map_name, sfr_map_name, i1_map_name, intr_i1_map_name, fuv_map_name
from .properties import intr_fuv_map_name, dust_mass_map_name, stellar_lum_map_name, intr_dust_map_name
from .properties import diffuse_mass_map_name, mass_map_name, earth_name, faceon_name, edgeon_name

# -----------------------------------------------------------------

# Define names of maps to show
#total_map_names = (bol_map_name, intr_stellar_map_name, obs_stellar_map_name, dust_map_name, dust_with_internal_map_name, scattered_map_name, absorbed_map_name, absorbed_with_internal_map_name, attenuated_map_name, direct_map_name,)
total_map_names = (bol_map_name, intr_stellar_map_name, obs_stellar_map_name, diffuse_dust_map_name, dust_map_name, scattered_map_name, absorbed_diffuse_map_name, fabs_diffuse_map_name, fabs_map_name, attenuated_map_name, direct_map_name, sfr_map_name, stellar_mass_map_name,ssfr_map_name,)
bulge_map_names = (bol_map_name, direct_map_name, i1_map_name, intr_i1_map_name, dust_map_name,)
disk_map_names = (bol_map_name, direct_map_name, i1_map_name, intr_i1_map_name, dust_map_name,)
old_map_names = (bol_map_name, direct_map_name, i1_map_name, intr_i1_map_name, dust_map_name,)
young_map_names = (bol_map_name, direct_map_name, fuv_map_name, intr_fuv_map_name, dust_map_name,)
sfr_map_names = (bol_map_name, direct_map_name, fuv_map_name, intr_fuv_map_name, sfr_map_name, dust_mass_map_name, stellar_lum_map_name, intr_dust_map_name, dust_map_name)
unevolved_map_names = (bol_map_name, direct_map_name, fuv_map_name, intr_fuv_map_name, sfr_map_name, dust_map_name,)
#dust_map_names = (mass_map_name, total_mass_map_name,) #lum_map_name, total_lum_map_name,)
dust_map_names = (diffuse_mass_map_name, mass_map_name,)

# -----------------------------------------------------------------

# Standard commands
_help_command_name = "help"
_history_command_name = "history"
_status_command_name = "status"

# Other commands
_show_command_name = "show"
_properties_command_name = "properties"
_output_command_name = "output"
_data_command_name = "data"
_model_command_name = "model"

# Plot commands
_plot_command_name = "plot"
_wavelengths_command_name = "wavelengths"
_dustgrid_command_name = "grid"
_sed_command_name = "sed"
_attenuation_command_name = "attenuation"
_map_command_name = "map"
_images_command_name = "images"
_cubes_command_name = "cubes"
_paper_command_name = "paper"

# Evaluate
_evaluate_command_name = "evaluate"

# Analysis
_absorption_command_name = "absorption"
_heating_command_name = "heating"
_energy_command_name = "energy"
_sfr_command_name = "sfr"
_correlations_command_name = "correlations"
_fluxes_command_name = "fluxes"
_residuals_command_name = "residuals"

# -----------------------------------------------------------------

_bulge_name = "bulge"
_disk_name = "disk"

_total_name = "total"
_old_bulge_name = "old_bulge"
_old_disk_name = "old_disk"
_old_name = "old"
_young_name = "young"
_sfr_name = "sfr"
_sfr_intrinsic_name = "sfr_intrinsic"
_unevolved_name = "unevolved"

_stellar_name = "stellar"
_dust_name = "dust"

_contributions_name = "contributions"
_components_name = "components"

_absorption_name = "absorption"

# -----------------------------------------------------------------

# Show subcommands
show_commands = OrderedDict()
show_commands.description = "show analysis results"

# Properties
show_commands[_properties_command_name] = ("show_properties", False, "show the model properties", None)

# Simulation output and data
show_commands[_output_command_name] = ("show_output", False, "show the simulation output", None)
show_commands[_data_command_name] = ("show_data", False, "show the simulation data available for the model", None)

# -----------------------------------------------------------------

map_name = "map"
difference_name = "difference"
distribution_name = "distribution"
curve_name = "curve"

plot_heating_commands = OrderedDict()
plot_heating_commands.description = "make plots of the heating fraction"
plot_heating_commands[map_name] = ("plot_heating_map_command", True, "plot map of the heating fraction", None)
plot_heating_commands[difference_name] = ("plot_heating_difference_command", True, "plot difference between heating fraction maps", None)
plot_heating_commands[distribution_name] = ("plot_heating_distribution_command", True, "plot distribution of heating fractions", None)
plot_heating_commands[curve_name] = ("plot_heating_curve_command", True, "plot curve of spectral heating", None)

plot_absorption_commands = OrderedDict()
plot_absorption_commands.description = "make plots of the absorbed energy"
plot_absorption_commands[map_name] = ("plot_absorption_map_command", True, "plot map of the absorbed energy", None)

# Plot subcommands
plot_commands = OrderedDict()
plot_commands.description = "plot other stuff"
plot_commands[_wavelengths_command_name] = ("plot_wavelengths_command", True, "plot the wavelength grid", None)
plot_commands[_dustgrid_command_name] = ("plot_grid_command", True, "plot the dust grid", None)
plot_commands[_residuals_command_name] = ("plot_residuals_command", True, "plot the observed, modeled and residual images", None)
plot_commands[_images_command_name] = ("plot_images_command", True, "plot the simulated images", None)
plot_commands[_fluxes_command_name] = ("plot_fluxes_command", True, "plot the mock fluxes", None)
plot_commands[_cubes_command_name] = ("plot_cubes_command", True, "plot the simulated datacubes", None)
plot_commands[_paper_command_name] = ("plot_paper_command", True, "make plots for the RT modeling paper", None)
plot_commands[_heating_command_name] = plot_heating_commands
plot_commands[_absorption_command_name] = plot_absorption_commands

# -----------------------------------------------------------------

# SED subcommands
sed_commands = OrderedDict()
sed_commands.description = "plot SEDs"

## TOTAL
sed_commands[_total_name] = ("plot_total_sed_command", True, "plot the SED of the total simulation", None)
sed_commands[_stellar_name] = ("plot_stellar_sed_command", True, "plot the stellar SED(s)", None)
sed_commands[_dust_name] = ("plot_dust_sed_command", True, "plot the dust SED(s)", None)

## CONTRIBUTIONS
sed_commands[_contributions_name] = ("plot_contribution_seds_command", True, "plot the contributions to the total SED(s)", None)
sed_commands[_components_name] = ("plot_component_seds_command", True, "plot the SED(s) for different components", None)

## COMPONENTS
sed_commands[_old_bulge_name] = ("plot_old_bulge_sed_command", True, "plot the SED of the old stellar bulge", None)
sed_commands[_old_disk_name] = ("plot_old_disk_sed_command", True, "plot the SED of the old stellar disk", None)
sed_commands[_old_name] = ("plot_old_sed_command", True, "plot the SED of the old stars", None)
sed_commands[_young_name] = ("plot_young_sed_command", True, "plot the SED of the young stars", None)
sed_commands[_sfr_name] = ("plot_sfr_sed_command", True, "plot the SED of the star formation regions", None)
sed_commands[_sfr_intrinsic_name] = ("plot_sfr_intrinsic_sed_command", True, "plot the intrinsic (stellar and dust) SED of the star formation regions", None)
sed_commands[_unevolved_name] = ("plot_unevolved_sed_command", True, "plot the SED of the unevolved stellar population (young + sfr)", None)
sed_commands[_absorption_name] = ("plot_absorption_sed_command", True, "plot absorption SEDs", None)

# -----------------------------------------------------------------

# Attenuation subcommands
attenuation_commands = OrderedDict()
attenuation_commands.description = "plot attenuation curves"
attenuation_commands[_total_name] = ("plot_total_attenuation_command", True, "plot the attenuation curve of the model", None)
attenuation_commands[_components_name] = ("plot_component_attenuation_command", True, "plot the attenuation curves of the different components", None)
attenuation_commands[_old_bulge_name] = ("plot_old_bulge_attenuation_command", True, "plot the attenuation curve of the old stellar bulge", None)
attenuation_commands[_old_disk_name] = ("plot_old_disk_attenuation_command", True, "plot the attenuation curve of the old stellar disk", None)
attenuation_commands[_old_name] = ("plot_old_attenuation_command", True, "plot the attenuation curve of the old stars", None)
attenuation_commands[_young_name] = ("plot_young_attenuation_command", True, "plot the attenuation curve of the young stars", None)
attenuation_commands[_sfr_name] = ("plot_sfr_attenuation_command", True, "plot the attenuation curve of the star formation regions", None)
# BUT WHAT IS THE *INTRINSIC* SFR ATTENUATION CURVE? (by INTERNAL DUST)
attenuation_commands[_unevolved_name] = ("plot_unevolved_attenuation_command", True, "plot the attenuation curve of the unevolved stellar population (young + sfr)", None)

# -----------------------------------------------------------------

# Map subcommands
map_commands = OrderedDict()
map_commands.description = "plot a map"
map_commands[_total_name] = ("show_total_map_command", True, "show a map of the total model", None)
map_commands[_bulge_name] = ("show_bulge_map_command", True, "show a map of the old stellar bulge component", None)
map_commands[_disk_name] = ("show_disk_map_command", True, "show a map of the old stellar disk component", None)
map_commands[_old_name] = ("show_old_map_command", True, "show a map of the old stellar component", None)
map_commands[_young_name] = ("show_young_map_command", True, "show a map of the young stellar component", None)
map_commands[_sfr_name] = ("show_sfr_map_command", True, "show a map of the SFR component", None)
map_commands[_unevolved_name] = ("show_unevolved_map_command", True, "show a map of the unevolved stellar component", None)
map_commands[_dust_name] = ("show_dust_map_command", True, "show a map of the dust component", None)

# -----------------------------------------------------------------

_cell_name = "cell"
_projected_name = "projected"
_spectral_name = "spectral"

# -----------------------------------------------------------------

# Heating subcommands
heating_commands = OrderedDict()
heating_commands.description = "analyse dust heating contributions"

# Cell and projected
heating_commands[_cell_name] = ("analyse_cell_heating_command", True, "analyse the cell heating", None)
heating_commands[_projected_name] = ("analyse_projected_heating_command", True, "analyse the projected heating", None)
heating_commands[_spectral_name] = ("analyse_spectral_heating_command", True, "analyse the spectral heating", None)

# -----------------------------------------------------------------

# Energy subcommands
energy_commands = OrderedDict()
energy_commands.description = "analyse the energy budget in the galaxy"

# Cell and projected
energy_commands[_cell_name] = ("analyse_cell_energy_command", True, "analyse the cell energy budget", None)
energy_commands[_projected_name] = ("analyse_projected_energy_command", True, "analyse the projected energy budget", None)

# -----------------------------------------------------------------

# Define commands
commands = OrderedDict()

# Standard commands
commands[_help_command_name] = ("show_help", False, "show help", None)
commands[_history_command_name] = ("show_history_command", True, "show history of executed commands", None)
commands[_status_command_name] = ("show_status_command", True, "show analysis status", None)

# Show stuff
commands[_show_command_name] = show_commands

# Examine the model
commands[_model_command_name] = ("examine_model", False, "examine the radiative transfer model", None)

# Plot stuff
commands[_sed_command_name] = sed_commands
commands[_attenuation_command_name] = attenuation_commands
commands[_map_command_name] = map_commands
commands[_plot_command_name] = plot_commands

# Evaluate
commands[_evaluate_command_name] = ("evaluate_command", True, "evaluate the analysis model", None)

# Analysis
commands[_properties_command_name] = ("analyse_properties_command", True, "analyse the model properties", None)
commands[_absorption_command_name] = ("analyse_absorption_command", True, "analyse the dust absorption", None)
commands[_heating_command_name] = heating_commands
commands[_energy_command_name] = energy_commands
commands[_sfr_command_name] = ("analyse_sfr_command", True, "analyse the star formation rates", None)
commands[_correlations_command_name] = ("analyse_correlations_command", True, "analyse the correlations", None)
commands[_images_command_name] = ("analyse_images_command", True, "analyse the simulation images", None)
commands[_fluxes_command_name] = ("analyse_fluxes_command", True, "analyse the simulation fluxes", None)
commands[_residuals_command_name] = ("analyse_residuals_command", True, "analyse the image residuals", None)

# -----------------------------------------------------------------

orientations = (earth_name, faceon_name, edgeon_name)
default_orientations = (earth_name,)

# -----------------------------------------------------------------

observed_name = "observed"
stellar_name = "stellar"
intrinsic_name = "intrinsic"

# -----------------------------------------------------------------

default_observed_intrinsic = (observed_name, intrinsic_name)
observed_intrinsic_choices = default_observed_intrinsic

default_observed_stellar_intrinsic = (observed_name, intrinsic_name)
observed_stellar_intrinsic_choices = [observed_name, stellar_name, intrinsic_name]

# -----------------------------------------------------------------

#default_contributions = ("total",)

# -----------------------------------------------------------------

grid_orientations = ["xy", "xz", "yz", "xyz"]

# -----------------------------------------------------------------

clipped_name = "clipped"
truncated_name = "truncated"
asymptotic_sed = "asymptotic"

default_sed_references = (clipped_name, truncated_name)
sed_reference_descriptions = dict()
sed_reference_descriptions[clipped_name] = "Observed clipped fluxes"
sed_reference_descriptions[truncated_name] = "Observed truncated fluxes"
sed_reference_descriptions[asymptotic_sed] = "Observed asymptotic fluxes"

# -----------------------------------------------------------------

bulge = "bulge"
disk = "disk"
old = "old"
young = "young"
sfr = "sfr"
unevolved = "unevolved"
total = "total"

# Make lists
components = [bulge, disk, old, young, sfr, unevolved, total]
default_components = [total, old, young, sfr]

# -----------------------------------------------------------------

# Photometric quantity
flux_name = "flux"
luminosity_name = "luminosity"
photometric_quantity_names = [flux_name, luminosity_name]
default_photometric_quantity_name = flux_name

# Spectral style
wavelength_style_name = "wavelength"
frequency_style_name = "frequency"
neutral_style_name = "neutral"
spectral_style_names = [wavelength_style_name, frequency_style_name, neutral_style_name]
default_spectral_style = wavelength_style_name

# -----------------------------------------------------------------

all_name = "all"
diffuse_name = "diffuse"
internal_name = "internal"
dust_contributions = [all_name, diffuse_name, internal_name]

# -----------------------------------------------------------------

cells_name = "cells"
cells_edgeon_name = "cells_edgeon"
midplane_name = "midplane"

# -----------------------------------------------------------------

default_plotting_format = "pdf"

# -----------------------------------------------------------------

from ..core.model import contributions, total_contribution, direct_contribution, scattered_contribution, dust_contribution, transparent_contribution
from ..core.model import dust_direct_contribution, dust_scattered_contribution
default_contributions = [total_contribution, direct_contribution, scattered_contribution, dust_contribution, transparent_contribution]

# -----------------------------------------------------------------

absorption_name = "absorption"
emission_name = "emission"
differences_name = "differences"

# -----------------------------------------------------------------

salim_name = "salim"
ke_name = "ke"
mappings_name = "mappings"
mappings_ke_name = "mappings_ke"

# -----------------------------------------------------------------

class Analysis(AnalysisRunComponent, InteractiveConfigurable):

    """
    This class ...
    """

    _commands = commands
    _log_section = "ANALYSIS"

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param args:
        :param kwargs:
        """

        # Call the constructor of the base class
        InteractiveConfigurable.__init__(self, no_config=True)
        AnalysisRunComponent.__init__(self, *args, **kwargs)

    # -----------------------------------------------------------------

    @property
    def do_commands(self):
        return self.config.commands is not None and len(self.config.commands) > 0

    # -----------------------------------------------------------------

    @property
    def do_interactive(self):
        return self.config.interactive

    # -----------------------------------------------------------------

    def _run(self, **kwargs):

        """
        Thisf unction ...
        :param kwargs:
        :return:
        """

        # 2. Run commands
        if self.do_commands: self.run_commands()

        # 3. Interactive
        if self.do_interactive: self.interactive()

        # 4. Show
        self.show()

        # 5. Write the history
        if self.has_commands: self.write_history()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        #super(Analysis, self).setup(**kwargs)
        AnalysisRunComponent.setup(self, **kwargs)
        InteractiveConfigurable.setup(self, **kwargs)

    # -----------------------------------------------------------------
    # PHOTOMETRIC UNITS
    # -----------------------------------------------------------------

    @lazyproperty
    def wavelength_lum_unit(self):
        return u("W/micron")

    # -----------------------------------------------------------------

    @lazyproperty
    def frequency_lum_unit(self):
        return u("W/Hz")

    # -----------------------------------------------------------------

    @lazyproperty
    def neutral_lum_unit(self):
        return u("Lsun", density=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def wavelength_flux_unit(self):
        return u("W/m2/micron")

    # -----------------------------------------------------------------

    @lazyproperty
    def frequency_flux_unit(self):
        return u("Jy")

    # -----------------------------------------------------------------

    @lazyproperty
    def neutral_flux_unit(self):
        return u("W/m2", density=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def luminosity_units(self):
        return {wavelength_style_name: self.wavelength_lum_unit, frequency_style_name: self.frequency_lum_unit, neutral_style_name: self.neutral_lum_unit}

    # -----------------------------------------------------------------

    @lazyproperty
    def flux_units(self):
        return {wavelength_style_name: self.wavelength_flux_unit, frequency_style_name: self.frequency_flux_unit, neutral_style_name: self.neutral_flux_unit}

    # -----------------------------------------------------------------

    @lazyproperty
    def photometric_units(self):
        return {luminosity_name: self.luminosity_units, flux_name: self.flux_units}

    # -----------------------------------------------------------------

    @property
    def simulations(self):
        return self.model.simulations

    # -----------------------------------------------------------------

    @property
    def parameter_values(self):
        return self.model.parameter_values

    # -----------------------------------------------------------------

    @property
    def free_parameter_values(self):
        return self.model.free_parameter_values

    # -----------------------------------------------------------------

    @property
    def other_parameter_values(self):
        return self.model.other_parameter_values

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values(self):
        return self.model.derived_parameter_values

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_total(self):
        return self.model.derived_parameter_values_total

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_bulge(self):
        return self.model.derived_parameter_values_bulge

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_disk(self):
        return self.model.derived_parameter_values_disk

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_old(self):
        return self.model.derived_parameter_values_old

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_young(self):
        return self.model.derived_parameter_values_young

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_sfr(self):
        return self.model.derived_parameter_values_sfr

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_unevolved(self):
        return self.model.derived_parameter_values_unevolved

    # -----------------------------------------------------------------

    @property
    def derived_parameter_values_dust(self):
        return self.model.derived_parameter_values_dust

    # -----------------------------------------------------------------

    @property
    def generation_name(self):
        return self.analysis_run.generation_name

    # -----------------------------------------------------------------

    @property
    def simulation_name(self):
        return self.analysis_run.simulation_name

    # -----------------------------------------------------------------

    @property
    def chi_squared(self):
        return self.analysis_run.chi_squared

    # -----------------------------------------------------------------

    @property
    def fitting_run_name(self):
        return self.analysis_run.fitting_run_name

    # -----------------------------------------------------------------

    @property
    def fitting_run(self):
        return self.analysis_run.fitting_run

    # -----------------------------------------------------------------

    @property
    def from_fitting(self):
        return self.analysis_run.from_fitting

    # -----------------------------------------------------------------

    @property
    def wavelength_grid(self):
        return self.analysis_run.wavelength_grid

    # -----------------------------------------------------------------

    @property
    def dust_grid(self):
        return self.analysis_run.dust_grid

    # -----------------------------------------------------------------

    @lazyproperty
    def show_status_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def show_status_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.show_status_definition, **kwargs)

        # Show
        self.show_status()

    # -----------------------------------------------------------------

    def show_status(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing status ...")

    # -----------------------------------------------------------------

    def show_properties(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Showing the model properties ...")

        # Show the model name
        print("")
        print(fmt.yellow + fmt.underlined + "Model name" + fmt.reset + ": " + self.model_name)
        if self.generation_name is not None: print(fmt.yellow + fmt.underlined + "Generation name" + fmt.reset + ": " + self.generation_name)
        if self.simulation_name is not None: print(fmt.yellow + fmt.underlined + "Simulation name" + fmt.reset + ": " + self.simulation_name)
        if self.chi_squared is not None: print(fmt.yellow + fmt.underlined + "Chi-squared" + fmt.reset + ": " + tostr(self.chi_squared))
        print("")

        # Show the free parameter values
        print(fmt.cyan + fmt.underlined + "Free parameter values:" + fmt.reset)
        print("")
        for label in self.free_parameter_values: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.free_parameter_values[label]))
        print("")

        # Show the other parameter values
        print(fmt.cyan + fmt.underlined + "Other parameter values:" + fmt.reset)
        print("")
        for label in self.other_parameter_values: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.other_parameter_values[label]))
        print("")

        # Derived parameter values of total model
        print(fmt.cyan + fmt.underlined + "Derived parameter values of total model:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_total: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_total[label]))
        print("")

        # Derived parameter values of bulge
        print(fmt.cyan + fmt.underlined + "Derived parameter values of old bulge stellar component:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_bulge: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_bulge[label]))
        print("")

        # Derived parameter values of disk
        print(fmt.cyan + fmt.underlined + "Derived parameter values of old disk stellar component:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_disk: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_disk[label]))
        print("")

        # Derived parameter values of old component
        print(fmt.cyan + fmt.underlined + "Derived parameter values of old stellar component:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_old: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_old[label]))
        print("")

        # Derived parameter values of young component
        print(fmt.cyan + fmt.underlined + "Derived parameter values of young stellar component:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_young: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_young[label]))
        print("")

        # Derived parameter values of SF component
        print(fmt.cyan + fmt.underlined + "Derived parameter values of SFR component:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_sfr: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_sfr[label]))
        print("")

        # Derived parameter values of unevolved components
        print(fmt.cyan + fmt.underlined + "Derived parameter values of unevolved stars:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_unevolved: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_unevolved[label]))
        print("")

        # Derived parameter values of dust component
        print(fmt.cyan + fmt.underlined + "Derived parameter values of dust component:" + fmt.reset)
        print("")
        for label in self.derived_parameter_values_dust: print(" - " + fmt.bold + label + fmt.reset + ": " + tostr(self.derived_parameter_values_dust[label]))
        print("")

    # -----------------------------------------------------------------

    def show_output(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Debugging
        log.debug("Showing the simulation output ...")

        # TOTAL
        print(fmt.blue + fmt.underlined + "TOTAL" + fmt.reset + ":")
        print("")
        self.total_output.show(line_prefix="  ", dense=True)
        print("")

        # BULGE
        print(fmt.blue + fmt.underlined + "BULGE" + fmt.reset + ":")
        print("")
        self.bulge_output.show(line_prefix="   ", dense=True)
        print("")

        # DISK
        print(fmt.blue + fmt.underlined + "DISK" + fmt.reset + ":")
        print("")
        self.disk_output.show(line_prefix="   ", dense=True)
        print("")

        # OLD
        print(fmt.blue + fmt.underlined + "OLD" + fmt.reset + ":")
        print("")
        self.old_output.show(line_prefix="   ", dense=True)
        print("")

        # YOUNG
        print(fmt.blue + fmt.underlined + "YOUNG" + fmt.reset + ":")
        print("")
        self.young_output.show(line_prefix="   ", dense=True)
        print("")

        # SFR
        print(fmt.blue + fmt.underlined + "SFR" + fmt.reset + ":")
        print("")
        self.sfr_output.show(line_prefix="   ", dense=True)
        print("")

        # UNEVOLVED
        print(fmt.blue + fmt.underlined + "UNEVOLVED" + fmt.reset + ":")
        print("")
        self.unevolved_output.show(line_prefix="   ", dense=True)
        print("")

    # -----------------------------------------------------------------

    def show_data(self, **kwargs):

        """
        This function ...
        """

        # Debugging
        log.debug("Showing the available model data ...")

        # TOTAL
        print(fmt.blue + fmt.underlined + "TOTAL" + fmt.reset + ":")
        print("")
        self.total_data.show(line_prefix="  ", check_valid=False, dense=True)
        print("")

        # BULGE
        print(fmt.blue + fmt.underlined + "BULGE" + fmt.reset + ":")
        print("")
        self.bulge_data.show(line_prefix="   ", check_valid=False, dense=True)
        print("")

        # DISK
        print(fmt.blue + fmt.underlined + "DISK" + fmt.reset + ":")
        print("")
        self.disk_data.show(line_prefix="   ", check_valid=False, dense=True)
        print("")

        # OLD
        print(fmt.blue + fmt.underlined + "OLD" + fmt.reset + ":")
        print("")
        self.old_data.show(line_prefix="   ", check_valid=False, dense=True)
        print("")

        # YOUNG
        print(fmt.blue + fmt.underlined + "YOUNG" + fmt.reset + ":")
        print("")
        self.young_data.show(line_prefix="   ", check_valid=False, dense=True)
        print("")

        # SFR
        print(fmt.blue + fmt.underlined + "SFR" + fmt.reset + ":")
        print("")
        self.sfr_data.show(line_prefix="   ", check_valid=False, dense=True)
        print("")

        # UNEVOLVED
        print(fmt.blue + fmt.underlined + "UNEVOLVED" + fmt.reset + ":")
        print("")
        self.unevolved_data.show(line_prefix="   ", check_valid=False, dense=True)
        print("")

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_wavelengths_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_wavelengths_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_wavelengths_definition)

        # Plot the wavelengths
        self.plot_wavelengths(**config)

    # -----------------------------------------------------------------

    def plot_wavelengths(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Plot the wavelength grid
        plot_wavelength_grid(self.wavelength_grid, "wavelengths", **kwargs)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_grid_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        definition.add_required("orientation", "string", "plotting viewpoint", choices=grid_orientations)
        definition.add_optional("path", "string", "path for the plot file")
        return definition

    # -----------------------------------------------------------------

    def plot_grid_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_grid_definition)

        # Get the path
        orientation = config.pop("orientation")
        path = config.pop("path")

        # Plot
        self.plot_grid(orientation, path=path)

    # -----------------------------------------------------------------

    def plot_grid(self, orientation, path=None, show=None):

        """
        This function ...
        :param orientation:
        :param path:
        :param show:
        :return:
        """

        # Debugging
        log.debug("Plotting the dust grid from orientation '" + orientation + "' ...")

        # Determine filepath
        if path is None:
            show = True
            path = fs.join(introspection.pts_temp_dir, "grid_" + orientation + ".pdf")

        # Determine grid filepath
        if orientation == "xy": grid_path = self.model.grid_xy_filepath
        elif orientation == "xz": grid_path = self.model.grid_xz_filepath
        elif orientation == "yz": grid_path = self.model.grid_yz_filepath
        elif orientation == "xyz": grid_path = self.model.grid_xyz_filepath
        else: raise ValueError("Invalid orientation: '" + orientation + "'")

        # Plot
        make_grid_plot(grid_path, path)

        # Open the plot?
        if show: fs.open_file(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def modeling_environment(self):
        return load_modeling_environment(self.config.path)

    # -----------------------------------------------------------------

    @property
    def clipped_sed(self):
        return self.modeling_environment.observed_sed

    # -----------------------------------------------------------------

    @property
    def truncated_sed(self):
        return self.modeling_environment.truncated_sed

    # -----------------------------------------------------------------

    @property
    def asymptotic_sed(self):
        return self.modeling_environment.asymptotic_sed

    # -----------------------------------------------------------------

    @memoize_method
    def get_reference_sed(self, label, additional_error=None, filters=None):

        """
        This function ...
        :param label:
        :param additional_error:
        :param filters:
        :return:
        """

        # Get sed
        if label == clipped_name: sed = self.clipped_sed
        elif label == truncated_name: sed = self.truncated_sed
        elif label == asymptotic_sed: sed = self.asymptotic_sed
        else: raise ValueError("Invalid reference SED name")

        # Add relative error?
        if additional_error is not None:
            sed = sed.copy()
            sed.add_or_set_relative_error(additional_error)

        # Subset of filters?
        if filters is not None: sed = sed.for_filters(filters)

        # Return
        return sed

    # -----------------------------------------------------------------

    def get_reference_seds(self, additional_error=None, references=default_sed_references):

        """
        This function ...
        :param additional_error:
        :param references:
        :return:
        """

        # Debugging
        log.debug("Loading the observed SEDs ...")

        # Create dictionary
        seds = OrderedDict()

        # Add observed SEDs
        for label in references:

            # Get sed
            sed = self.get_reference_sed(label, additional_error=additional_error)

            # Add
            description = sed_reference_descriptions[label]
            seds[description] = sed

        # Return the seds
        return seds

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_total_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("orientations", "string_list", "instrument orientation", default_orientations, choices=orientations)
        definition.add_flag("add_references", "add reference SEDs", False)
        definition.add_optional("additional_error", "percentage", "additional percentual error for the observed flux points")
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_total_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_total_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_total_sed(orientations=config.orientations, add_references=config.add_references,
                            additional_error=config.additional_error, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    def plot_total_sed(self, orientations=default_orientations, add_references=False, additional_error=None, path=None,
                       show_file=False, title=None, format=default_plotting_format, unit=None):

        """
        This function ...
        :param orientations:
        :param add_references:
        :param additional_error:
        :param path:
        :param show_file:
        :param title:
        :param format:
        :param unit:
        :return:
        """

        # Debugging
        log.debug("Plotting total SED(s) ...")

        # Create SED plotter
        plotter = SEDPlotter()

        # Set unit
        if unit is not None: plotter.config.unit = unit
        plotter.config.distance = self.galaxy_distance

        # Add references?
        if add_references: plotter.add_seds(self.get_reference_seds(additional_error=additional_error))

        # Add orientations
        for orientation in orientations:

            if orientation == earth_name: plotter.add_sed(self.model.observed_total_sed, earth_name)
            elif orientation == faceon_name: plotter.add_sed(self.model.faceon_observed_total_sed, faceon_name, residuals=False)
            elif orientation == edgeon_name: plotter.add_sed(self.model.edgeon_observed_total_sed, edgeon_name, residuals=False)
            else: raise ValueError("Invalid orientation: '" + orientation + "'")

        # Set filepath, if plot is to be shown as file
        if path is None and show_file:
            if format is None: raise ValueError("Format has to be specified")
            path = fs.join(introspection.pts_temp_dir, "total_seds." + format)

        # Run the plotter
        plotter.run(title=title, output=path)

        # Show file
        if show_file: fs.open_file(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_stellar_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_required("observed_intrinsic", "string_tuple", "plot observed stellar SED, intrinsic stellar SED, or both", choices=observed_intrinsic_choices)
        definition.add_positional_optional("components", "string_list", "components", [total], choices=components)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_stellar_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_stellar_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_stellar_sed(config.observed_intrinsic, components=config.components, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    def plot_stellar_sed(self, observed_intrinsic, components, path=None, title=None, show_file=False,
                         format=default_plotting_format, unit=None):

        """
        This function ...
        :param observed_intrinsic:
        :param components:
        :param path:
        :param title:
        :param show_file:
        :param format:
        :param unit:
        :return:
        """

        # Debugging
        log.debug("Plotting stellar SED(s) ...")

        # Create SED plotter
        plotter = SEDPlotter()

        # Set unit
        if unit is not None: plotter.config.unit = unit
        plotter.config.distance = self.galaxy_distance

        # Add references?
        # if add_references: plotter.add_seds(self.get_reference_seds(additional_error=additional_error))

        # Either observed of intrinsic
        if len(observed_intrinsic) == 1:

            oi = observed_intrinsic[0]

            # Loop over the components
            for component in components:

                # Set residuals flag
                residuals = component == total and oi == observed_name
                sed = self.model.get_stellar_sed(component, oi)
                name = component

                # Add SED to plotter
                plotter.add_sed(sed, name, residuals=residuals)

        # Both observed and intrinsic
        else:

            # ALLOW this for multiple components?

            # Loop over the components
            for component in components:
                for oi in observed_intrinsic:

                    # Set residuals flag
                    residuals = component == total and oi == observed_name

                    # Get the SED
                    sed = self.model.get_stellar_sed(component, oi)

                    # Add
                    plotter.add_sed(sed, component + " " + oi, residuals=residuals)

        # Set filepath, if plot is to be shown as file
        if path is None and show_file:
            if format is None: raise ValueError("Format has to be specified")
            path = fs.join(introspection.pts_temp_dir, "stellar_seds." + format)

        # Run the plotter
        plotter.run(title=title, output=path)

        # Show file
        if show_file: fs.open_file(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_dust_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("components", "string_list", "components", default_components, choices=components)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_dust_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_dust_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_dust_sed(config.components, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    def plot_dust_sed(self, components, title=None, path=None, show_file=False, format=default_plotting_format, unit=None):

        """
        This function ...
        :param components:
        :param title:
        :param path:
        :param show_file:
        :param format:
        :param unit:
        :return:
        """

        # Debugging
        log.debug("Plotting dust SED(s) ...")

        # Create SED plotter
        plotter = SEDPlotter()

        # Set unit
        if unit is not None: plotter.config.unit = unit
        plotter.config.distance = self.galaxy_distance

        # Add references?
        # if add_references: plotter.add_seds(self.get_reference_seds(additional_error=additional_error))

        # Loop over the components
        for component in components:

            # Get the SED
            sed = self.model.get_dust_sed(component)

            # Add
            plotter.add_sed(sed, component, residuals=False)

        # Set filepath, if plot is to be shown as file
        if path is None and show_file:
            if format is None: raise ValueError("Format has to be specified")
            path = fs.join(introspection.pts_temp_dir, "dust_seds." + format)

        # Run the plotter
        plotter.run(title=title, output=path)

        # Show file
        if show_file: fs.open_file(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_contribution_seds_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("contributions", "string_list", "contributions", default_contributions, choices=contributions)
        definition.add_optional("component", "string", "component", total, choices=components)
        definition.import_settings(plot_seds_definition)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_contribution_seds_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_contribution_seds_definition, **kwargs)
        contributions = config.pop("contributions")

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_contribution_seds(contributions, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    def get_sed_contribution(self, contribution, component=total):

        """
        This function ...
        :param contribution:
        :param component:
        :return:
        """

        # Get the simulations
        simulations = self.simulations[component]

        # Return the SED
        if contribution == total_contribution: return simulations.observed_sed
        elif contribution == direct_contribution:
            if simulations.has_full_sed: return simulations.observed_sed_direct
            else: return None
        elif contribution == scattered_contribution:
            if simulations.has_full_sed: return simulations.observed_sed_scattered
            else: return None
        elif contribution == dust_contribution:
            if simulations.has_full_sed: return simulations.observed_sed_dust
            else: return None
        elif contribution == dust_direct_contribution:
            if simulations.has_full_sed: return simulations.observed_sed_dust_direct
            else: return None
        elif contribution == dust_scattered_contribution:
            if simulations.has_full_sed: return simulations.observed_sed_dust_scattered
            else: return None
        elif contribution == transparent_contribution:
            if simulations.has_full_sed: return simulations.observed_sed_transparent
            else: return None
        else: raise ValueError("Invalid contribution: '" + contribution + "'")

    # -----------------------------------------------------------------

    def plot_contribution_seds(self, contributions, path=None, title=None, show_file=False, format=default_plotting_format,
                               component=total, unit=None):

        """
        This function ...
        :param contributions:
        :param path:
        :param title:
        :param show_file:
        :param format:
        :param component:
        :param unit:
        :return:
        """

        # Debugging
        log.debug("Plotting contribution SEDs ...")

        # Create SED plotter
        #plotter = SEDPlotter(kwargs) # **kwargs DOESN'T WORK? (e.g. with min_flux)
        plotter = SEDPlotter()

        # Set unit
        if unit is not None: plotter.config.unit = unit
        plotter.config.distance = self.galaxy_distance

        # Loop over the contributions
        for contribution in contributions:

            # Get the contribution SED
            sed = self.get_sed_contribution(contribution, component=component)
            if sed is None:
                log.warning("No '" + contribution + "' SED can be obtained for the '" + component + "' component: skipping ...")
                continue

            # Add
            residuals = contribution == total_contribution and component == total
            plotter.add_sed(sed, contribution, residuals=residuals)

        # Set filepath, if plot is to be shown as file
        if path is None and show_file:
            if format is None: raise ValueError("Format has to be specified")
            path = fs.join(introspection.pts_temp_dir, "contribution_seds." + format)

        # Run the plotter
        plotter.run(title=title, output=path)

        # Show file
        if show_file: fs.open_file(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_component_seds_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_positional_optional("components", "string_list", "components", default_components, choices=components)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_component_seds_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_component_seds_definition, **kwargs)

        # Get
        components = config.pop("components")

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_component_seds(components, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    def get_simulation_sed(self, component):

        """
        This function ...
        :param component:
        :return:
        """

        # Return the SED
        return self.simulations[component].observed_sed

    # -----------------------------------------------------------------

    def get_component_sed(self, component, dust_absorption=True, dust_emission=True):

        """
        This function ...
        :param component:
        :param dust_absorption:
        :param dust_emission:
        :return:
        """

        # Simulation SEDs
        if dust_emission:

            # Simulation SED
            if dust_absorption: return self.get_simulation_sed(component)

            # No dust absorption but dust emission, WEEEIRD
            else: raise NotImplementedError("This SED does not make physically sense")

        # No dust emission
        else:

            # With absorption
            if dust_absorption: return self.model.get_observed_stellar_sed(component)

            # No absorption: intrinsic
            else: return self.model.get_intrinsic_stellar_sed(component)

    # -----------------------------------------------------------------

    def get_observed_stellar_or_intrinsic_sed(self, component, observed_stellar_intrinsic):

        """
        This function ...
        :param component:
        :param observed_stellar_intrinsic:
        :return:
        """

        # Set flags
        if observed_stellar_intrinsic == observed_name: dust_absorption = dust_emission = True
        elif observed_stellar_intrinsic == intrinsic_name: dust_absorption = dust_emission = False
        elif observed_stellar_intrinsic == stellar_name:
            dust_absorption = True
            dust_emission = False
        else: raise ValueError("Invalid option for 'observed_stellar_or_intrinsic'")

        # Return
        return self.get_component_sed(component, dust_absorption=dust_absorption, dust_emission=dust_emission)

    # -----------------------------------------------------------------

    def plot_component_seds(self, components, path=None, title=None, show_file=False, format=default_plotting_format, unit=None):

        """
        This function ...
        :param components:
        :param path:
        :param title:
        :param show_file:
        :param format:
        :param unit:
        :return:
        """

        # Debugging
        log.debug("Plotting component SEDs ...")

        # Create SED plotter
        #plotter = SEDPlotter(kwargs)
        plotter = SEDPlotter()

        # Set unit
        if unit is not None: plotter.config.unit = unit
        plotter.config.distance = self.galaxy_distance

        # Add references?
        #if add_references: plotter.add_seds(self.get_reference_seds(additional_error=additional_error))

        # Loop over the components
        for component in components:

            # Get the SED
            sed = self.get_component_sed(component)

            # Add to plot
            residuals = component == total
            plotter.add_sed(sed, component, residuals=residuals)

        # Set filepath, if plot is to be shown as file
        if path is None and show_file:
            if format is None: raise ValueError("Format has to be specified")
            path = fs.join(introspection.pts_temp_dir, "component_seds." + format)

        # Run the plotter
        plotter.run(title=title, output=path)

        # Show file
        if show_file: fs.open_file(path)

    # -----------------------------------------------------------------

    def plot_component_sed(self, component, observed_stellar_intrinsic, unit=None, path=None):

        """
        This function ...
        :param component:
        :param observed_stellar_intrinsic:
        :param unit:
        :param path:
        :return:
        """

        # Either observed or intrinsic
        if len(observed_stellar_intrinsic) == 1:

            # Get the SED
            sed = self.get_observed_stellar_or_intrinsic_sed(component, observed_stellar_intrinsic[0])

            # Plot
            plot_sed(sed, unit=unit, distance=self.galaxy_distance, path=path)

        # Both
        else:

            seds = OrderedDict()
            for osi in observed_stellar_intrinsic: seds[osi] = self.get_observed_stellar_or_intrinsic_sed(component, osi)
            plot_seds(seds, residuals=False, unit=unit, distance=self.galaxy_distance, path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_old_bulge_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_positional_optional("observed_stellar_intrinsic", "string_tuple", "plot observed SED (simulation), observed SED (stellar), intrinsic SED (stellar), or multiple", default_observed_stellar_intrinsic, choices=observed_stellar_intrinsic_choices)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_old_bulge_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_old_bulge_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot component
        self.plot_component_sed(bulge, config.observed_stellar_intrinsic, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_old_disk_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_positional_optional("observed_stellar_intrinsic", "string_tuple", "plot observed SED (simulation), observed SED (stellar), intrinsic SED (stellar), or multiple", default_observed_stellar_intrinsic, choices=observed_stellar_intrinsic_choices)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_old_disk_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_old_disk_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot component
        self.plot_component_sed(disk, config.observed_stellar_intrinsic, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_old_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("observed_stellar_intrinsic", "string_tuple", "plot observed SED (simulation), observed SED (stellar), intrinsic SED (stellar), or multiple", default_observed_stellar_intrinsic, choices=observed_stellar_intrinsic_choices)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_old_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_old_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot component
        self.plot_component_sed(old, config.observed_stellar_intrinsic, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_young_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_positional_optional("observed_stellar_intrinsic", "string_tuple", "plot observed SED (simulation), observed SED (stellar), intrinsic SED (stellar), or multiple", default_observed_stellar_intrinsic, choices=observed_stellar_intrinsic_choices)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_young_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_young_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_component_sed(young, config.observed_stellar_intrinsic, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_sfr_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_positional_optional("observed_stellar_intrinsic", "string_tuple", "plot observed SED (simulation), observed SED (stellar), intrinsic SED (stellar), or multiple", default_observed_stellar_intrinsic, choices=observed_stellar_intrinsic_choices)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_sfr_sed_command(self, command, **kwargs):

        """
        This function ...
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_sfr_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_component_sed(sfr, config.observed_stellar_intrinsic, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_sfr_intrinsic_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_sfr_intrinsic_sed_command(self, command, **kwargs):

        """
        This functino ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_sfr_intrinsic_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_sfr_intrinsic_sed(unit=unit, path=config.path)

    # -----------------------------------------------------------------

    def plot_sfr_intrinsic_sed(self, unit=None, path=None):

        """
        This function ...
        :param unit:
        :param path:
        :return:
        """

        # Get stellar SEDs
        observed_stellar = self.model.get_stellar_sed(sfr, observed_name)
        intrinsic_stellar = self.model.get_stellar_sed(sfr, intrinsic_name)

        # Get intrinsic SEDs
        transparent_stellar = self.model.intrinsic_transparent_sfr_stellar_sed
        dust = self.model.intrinsic_sfr_dust_sed

        # Plot
        seds = OrderedDict()
        seds["observed stellar"] = observed_stellar
        seds["intrinsic"] = intrinsic_stellar
        seds["intrinsic (transparent) stellar"] = transparent_stellar
        seds["intrinsic dust"] = dust

        #print(observed_stellar)
        #print(intrinsic_stellar)
        #print(transparent_stellar)
        #print(dust)

        # Plot
        plot_seds(seds, unit=unit, distance=self.galaxy_distance, path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_unevolved_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)
        
        # Add options
        definition.add_positional_optional("observed_stellar_intrinsic", "string_tuple", "plot observed SED (simulation), observed SED (stellar), intrinsic SED (stellar), or multiple", default_observed_stellar_intrinsic, choices=observed_stellar_intrinsic_choices)
        definition.add_optional("quantity", "string", "flux or luminosity", default_photometric_quantity_name, choices=photometric_quantity_names)
        definition.add_optional("spectral", "string", "spectral style", default_spectral_style, choices=spectral_style_names)
        
        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_unevolved_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get the config
        config = self.get_config_from_command(command, self.plot_unevolved_sed_definition, **kwargs)

        # Get photometric unit
        unit = self.photometric_units[config.quantity][config.spectral]

        # Plot
        self.plot_component_sed(unevolved, config.observed_stellar_intrinsic, unit=unit, path=config.path)

    # -----------------------------------------------------------------

    @property
    def absorption_path(self):
        return self.analysis_run.absorption_path

    # -----------------------------------------------------------------

    @lazyproperty
    def total_absorption_cells_sed_filepath(self):
        total_filename = "total_curve_absorption.dat"
        return fs.get_filepath(self.absorption_path, total_filename, error_message="total spectral absorption SED file is not present: run absorption analysis first")

    # -----------------------------------------------------------------

    @lazyproperty
    def total_absorption_cells_sed(self):
        return SED.from_file(self.total_absorption_cells_sed_filepath)

    # -----------------------------------------------------------------

    @lazyproperty
    def unevolved_absorption_cells_sed_filepath(self):
        unevolved_filename = "unevolved_curve_absorption.dat"
        return fs.get_filepath(self.absorption_path, unevolved_filename, error_message="unevolved spectral absorption SED file is not present: run absorption analysis first")

    # -----------------------------------------------------------------

    @lazyproperty
    def unevolved_absorption_cells_sed(self):
        return SED.from_file(self.unevolved_absorption_cells_sed_filepath)

    # -----------------------------------------------------------------

    def plot_seds(self, **kwargs):
        plot_seds(kwargs, distance=self.galaxy_distance)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_absorption_sed_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Component
        definition.add_positional_optional("component", "string", "component", total, choices=components)

        # Path
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_absorption_sed_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_absorption_sed_definition, **kwargs)

        # Total?
        if config.component == total: self.plot_absorption_sed_total(path=config.path)

        # Bulge
        elif config.component == bulge: self.plot_absorption_sed_bulge(path=config.path)

        # Disk
        elif config.component == disk: self.plot_absorption_sed_disk(path=config.path)

        # Old
        elif config.component == old: self.plot_absorption_sed_old(path=config.path)

        # Young
        elif config.component == young: self.plot_absorption_sed_young(path=config.path)

        # SFR
        elif config.component == sfr: self.plot_absorption_sed_sfr(path=config.path)

        # Unevolved
        elif config.component == unevolved: self.plot_absorption_sed_unevolved(path=config.path)

        # Invalid
        else: raise ValueError("Invalid component '" + config.component + "'")

    # -----------------------------------------------------------------

    def plot_absorption_sed_total(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for the total model ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("total"), path=path)

    # -----------------------------------------------------------------

    def plot_absorption_sed_bulge(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for old bulge component ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("bulge"), path=path)

    # -----------------------------------------------------------------

    def plot_absorption_sed_disk(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for old disk component ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("disk"), path=path)

    # -----------------------------------------------------------------

    def plot_absorption_sed_old(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for old stars ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("old"), path=path)

    # -----------------------------------------------------------------

    def plot_absorption_sed_young(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for young stars ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("young"), path=path)

    # -----------------------------------------------------------------

    def plot_absorption_sed_sfr(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for star formation regions ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("sfr"), path=path)

    # -----------------------------------------------------------------

    def plot_absorption_sed_unevolved(self, path=None):

        """
        Thisfunction ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting absorption for unevolved stars ...")

        # Plot
        plot_sed(self.get_dust_absorption_sed("unevolved"), path=path)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_total_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_total_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_total_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve, total)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_component_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        definition.add_positional_optional("components", "string_list", "components", default_components, choices=components)
        return definition

    # -----------------------------------------------------------------

    def plot_component_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_component_attenuation_definition, **kwargs)

        # GetAbsorbed bolometric luminosity
        components = config.pop("components")

        # Plot
        self.plot_component_attenuation(components)

    # -----------------------------------------------------------------

    def get_component_attenuation_curve(self, component):

        """
        This function ...
        :param component:
        :return:
        """

        # Return
        return self.simulations[component].attenuation_curve

    # -----------------------------------------------------------------

    def plot_component_attenuation(self, components):

        """
        This function ...
        :param components:
        :return:
        """

        # Initialize
        curves = OrderedDict()

        # Add components
        for component in components:

            # Get curve
            curve = self.get_component_attenuation_curve(component)

            # Add
            curves[component] = curve

        # Plot
        plot_attenuation_curves(curves)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_old_bulge_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_old_bulge_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_old_bulge_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve_old_bulge, bulge)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_old_disk_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_old_disk_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_old_disk_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve_old_disk, disk)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_old_attenuation_definition(self):

        """
        Thisf unction ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_old_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_old_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve_old, old)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_young_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_young_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_young_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve_young, young)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_sfr_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_sfr_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_sfr_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve_sfr, sfr)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_unevolved_attenuation_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        return definition

    # -----------------------------------------------------------------

    def plot_unevolved_attenuation_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_unevolved_attenuation_definition, **kwargs)

        # Plot
        plot_attenuation_curve(self.model.attenuation_curve_unevolved, unevolved)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_residuals_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Filters
        definition.add_optional("filters", "lazy_broad_band_filter_list", "filters for which to plot images", default="FUV,NUV,I1,MIPS 24mu,Pacs160,SPIRE350", convert_default=True)

        # Save to path
        definition.add_optional("path", "new_path", "save plot to file")

        # Dark mode
        definition.add_flag("dark", "plot in dark mode")

        # Other options
        definition.add_optional("zoom", "positive_real", "zoom from the normal galaxy truncation", 0.7)
        definition.add_optional("scale_xy_ratio", "positive_real", "scale the xy ratio to make plot panes more or less square", 1.)
        definition.add_optional("scale_xy_exponent", "positive_real", "exponent for the xy ratio to make plot panes more or less square", 0.7)
        definition.add_flag("mask", "mask the model image pixels that are invalid in the observed images", True)

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_residuals_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_residuals_definition, **kwargs)

        # Plot residuals
        self.plot_residuals(config.filters, path=config.path, dark=config.dark, zoom=config.zoom,
                            scale_xy_ratio=config.scale_xy_ratio, scale_xy_exponent=config.scale_xy_exponent,
                            mask_simulated=config.mask)

    # -----------------------------------------------------------------

    def plot_residuals(self, filters, path=None, dark=False, zoom=1., scale_xy_ratio=1., scale_xy_exponent=1., mask_simulated=False):

        """
        Thisn function ...
        :param filters:
        :param path:
        :param dark:
        :param zoom:
        :param scale_xy_ratio:
        :param scale_xy_exponent:
        :param mask_simulated:
        :return:
        """

        from pts.magic.plot.imagegrid import plot_residuals_aplpy

        # Get images
        observations = self.get_observed_images(filters)
        models = self.get_simulated_images(filters)
        residuals = self.get_residual_images(filters)
        #distributions = self.get_residual_distributions(filters)

        # Get center and radius
        center = self.galaxy_center
        radius = self.truncation_radius * zoom
        xy_ratio = (self.truncation_box_axial_ratio * scale_xy_ratio)**scale_xy_exponent

        #print(xy_ratio)

        # Plot
        plot_residuals_aplpy(observations, models, residuals, center=center, radius=radius, filepath=path, dark=dark,
                             xy_ratio=xy_ratio, distance=self.galaxy_distance, mask_simulated=mask_simulated)

    # -----------------------------------------------------------------
    # OBSERVED
    # -----------------------------------------------------------------

    def get_observed_images(self, filters):
        return self.static_photometry_dataset.get_frames_for_filters(filters)

    # -----------------------------------------------------------------
    # SIMULATED (MOCK)
    # -----------------------------------------------------------------

    @property
    def simulated_images_path(self):
        return self.analysis_run.images_path

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_images_dataset(self):
        return StaticDataSet.from_directory(self.simulated_images_path)

    # -----------------------------------------------------------------

    def get_simulated_images(self, filters):
        return self.simulated_images_dataset.get_frames_for_filters(filters)

    # -----------------------------------------------------------------
    # RESIDUALS
    # -----------------------------------------------------------------

    @property
    def residual_images_path(self):
        return fs.join(self.analysis_run.residuals_path, "maps")

    # -----------------------------------------------------------------

    @lazyproperty
    def residual_images_dataset(self):
        return StaticDataSet.from_directory(self.residual_images_path)

    # -----------------------------------------------------------------

    def get_residual_images(self, filters):
        return self.residual_images_dataset.get_frames_for_filters(filters)

    # -----------------------------------------------------------------
    # DISTRIBUTIONS
    # -----------------------------------------------------------------

    @lazyproperty
    def residual_distributions_path(self):
        return fs.join(self.analysis_run.residuals_path, "distributions")

    # -----------------------------------------------------------------

    def get_residual_distributions(self, filters):
        distributions = []
        for fltr in filters:
            filepath = fs.join(self.residual_distributions_path, str(fltr) + ".dat")
            if not fs.is_file(filepath): distribution = None
            else: distribution = Distribution.from_file(filepath)
            distributions.append(distribution)
        return distributions

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_images_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("orientation", "string", "orientation of the images", earth_name, choices=orientations)
        definition.add_optional("filters", "lazy_broad_band_filter_list", "filters for which to plot images", default="FUV,NUV,I1,MIPS 24mu,Pacs160,SPIRE350", convert_default=True)
        definition.add_flag("residuals", "show residuals", True)
        definition.add_flag("distributions", "show residual distributions", True)
        definition.add_flag("from_evaluation", "use the images created in the evaluation step", None)
        definition.add_flag("spectral_convolution", "use spectral convolution to create images", False)
        definition.add_flag("proper", "use the proper mock observed images if present", True)
        definition.add_flag("only_from_evaluation", "only use filters for which an image was made in the evaluation")
        definition.add_flag("sort_filters", "sort the filters on wavelength", True)

        # Path
        definition.add_optional("path", "new_path", "path for the plot file")

        # Return
        return definition

    # -----------------------------------------------------------------

    def plot_images_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_images_definition, **kwargs)

        # Get list of filters
        if config.only_from_evaluation:
            config.from_evaluation = True
            if config.proper: filters = sequences.intersection(config.filters, self.analysis_run.evaluation_proper_image_filters)
            else: filters = sequences.intersection(config.filters, self.analysis_run.evaluation_image_filters)
        else: filters = config.filters

        # Sort the filters on wavelength
        if config.sort_filters: filters = sequences.sorted_by_attribute(filters, "wavelength")

        # Earth
        if config.orientation == earth_name: self.plot_earth_images(filters, residuals=config.residuals,
                                                                    distributions=config.distributions, from_evaluation=config.from_evaluation,
                                                                    spectral_convolution=config.spectral_convolution, proper=config.proper, path=config.path)

        # Face-on
        elif config.orientation == faceon_name: self.plot_faceon_images(filters, spectral_convolution=config.spectral_convolution, path=config.path)

        # Edge-on
        elif config.orientation == edgeon_name: self.plot_edgeon_images(filters, spectral_convolution=config.spectral_convolution, path=config.path)

        # Invalid
        else: raise ValueError("Invalid orientation: '" + config.orientation + "'")

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_fluxes_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_flag("add_observed", "add the observed fluxes", True)
        definition.add_flag("add_simulated", "add the simulated SED")
        definition.add_flag("only_residuals", "only show the fluxes for the residuals")
        definition.add_flag("simulation_residuals", "show the residuals of the simulation to the observed fluxes", True)
        definition.add_optional("additional_error", "percentage", "additional percentual error for the observed flux points")

        # Filters
        definition.add_flag("use_fitting_filters", "limit the mock and observed SEDs to filters that were used for the fitting")

        # Save plot file
        definition.add_optional("path", "new_path", "plot file path")

        # Return
        return definition

    # -----------------------------------------------------------------

    @property
    def fluxes_path(self):
        return self.analysis_run.fluxes_path

    # -----------------------------------------------------------------

    @property
    def mock_fluxes_path(self):
        return fs.join(self.fluxes_path, "fluxes.dat")

    # -----------------------------------------------------------------

    @property
    def has_mock_fluxes(self):
        return fs.is_file(self.mock_fluxes_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def mock_fluxes(self):
        if not self.has_mock_fluxes: raise IOError("The mock fluxes are not (yet) present: run the fluxes analysis first")
        return ObservedSED.from_file(self.mock_fluxes_path)

    # -----------------------------------------------------------------

    @property
    def flux_differences_path(self):
        return fs.join(self.fluxes_path, "differences.dat")

    # -----------------------------------------------------------------

    @property
    def has_flux_differences(self):
        return fs.is_file(self.flux_differences_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def flux_differences(self):
        if not self.has_flux_differences: raise IOError("The flux differences are not (yet) present: run the fluxes analysis first")
        return FluxDifferencesTable.from_file(self.flux_differences_path)

    # -----------------------------------------------------------------

    def plot_fluxes_command(self, command, **kwargs):

        """
        This function ....
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_fluxes_definition, **kwargs)

        # Plot
        self.plot_fluxes(add_observed=config.add_observed, add_simulated=config.add_simulated,
                         only_residuals=config.only_residuals, simulation_residuals=config.simulation_residuals,
                         additional_error=config.additional_error, use_fitting_filters=config.use_fitting_filters,
                         path=config.path)

    # -----------------------------------------------------------------

    def plot_fluxes(self, add_observed=True, add_simulated=False, only_residuals=False, simulation_residuals=True,
                    additional_error=None, use_fitting_filters=False, path=None):

        """
        This function ...
        :param add_observed
        :param add_simulated:
        :param only_residuals:
        :param simulation_residuals:
        :param additional_error:
        :param use_fitting_filters:
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting the mock fluxes ...")

        # Set the filters
        if use_fitting_filters: use_filters = tuple(self.fitting_run.fitting_filters) # list is not hashable for the memoized get_reference_sed function
        else: use_filters = None

        # Get the mock fluxes
        if use_filters is not None: mock_fluxes = self.mock_fluxes.for_filters(use_filters)
        else: mock_fluxes = self.mock_fluxes

        # Set SEDs
        seds = OrderedDict()
        if add_observed: seds["Observation"] = self.get_reference_sed(clipped_name, additional_error=additional_error, filters=use_filters)
        seds["Mock"] = mock_fluxes
        if add_simulated: seds["Simulation"] = self.get_simulation_sed("total")

        # Show chi squared
        ndifferences = self.flux_differences.get_column_nnotmasked("Chi squared term")
        nfree_parameters = 3
        ndof = ndifferences - nfree_parameters - 1
        chi_squared = self.flux_differences.get_column_sum("Chi squared term") / ndof

        # Debugging
        log.debug("The (reduced) chi squared value is " + str(chi_squared))

        # Set options
        plot_options = dict()
        plot_options["Mock"] = {"only_residuals": only_residuals, "as_reference": False}
        plot_options["Simulation"] = {"residuals": simulation_residuals, "residual_color": "darkgrey"}

        # Plot
        plot_seds(seds, path=path, options=plot_options, residual_reference="observations", smooth_residuals=True)

    # -----------------------------------------------------------------

    @property
    def earth_cube(self):
        return self.model.total_bolometric_luminosity_cube_earth

    # -----------------------------------------------------------------

    @property
    def faceon_cube(self):
        return self.model.total_bolometric_luminosity_cube_faceon

    # -----------------------------------------------------------------

    @property
    def edgeon_cube(self):
        return self.model.total_bolometric_luminosity_cube_edgeon

    # -----------------------------------------------------------------

    @memoize_method
    def get_earth_image(self, filter_or_wavelength, from_evaluation=None, spectral_convolution=False, proper=True):

        """
        This function ...
        :param filter_or_wavelength:
        :param from_evaluation:
        :param spectral_convolution:
        :param proper:
        :return:
        """

        # Filter?
        if isinstance(filter_or_wavelength, Filter):

            # From evaluation
            if from_evaluation is None:

                if proper:
                    if self.analysis_run.has_evaluation_proper_image_for_filter(filter_or_wavelength): from_evaluation = True
                    else: from_evaluation = False
                else:
                    if self.analysis_run.has_evaluation_image_for_filter(filter_or_wavelength): from_evaluation = True
                    else: from_evaluation = False

            # From evaluation
            if from_evaluation:

                if proper: return self.analysis_run.get_evaluation_proper_image_for_filter(filter_or_wavelength)
                else: return self.analysis_run.get_evaluation_image_for_filter(filter_or_wavelength)

            # Not from evaluation
            else: return self.earth_cube.frame_for_filter(filter_or_wavelength, convolve=spectral_convolution)

        # Wavelength
        elif types.is_length_quantity(filter_or_wavelength):

            # Checks
            if spectral_convolution: raise ValueError("Spectral convolution cannot be applied when a wavelength is passed")
            if from_evaluation: raise ValueError("Cannot get image for a particular wavelength from evaluation output")

            # Return the frame for this wavelength
            return self.earth_cube.get_frame_for_wavelength(filter_or_wavelength)

        # Invalid
        else: raise ValueError("Invalid argument")

    # -----------------------------------------------------------------

    def has_residual_image_from_evaluation(self, fltr, proper=True):

        """
        Thisf unction ...
        :param fltr:
        :param proper:
        :return:
        """

        if proper: return self.analysis_run.has_evaluation_proper_residuals_for_filter(fltr)
        else: return self.analysis_run.has_evaluation_residuals_for_filter(fltr)

    # -----------------------------------------------------------------

    def get_residual_image_from_evaluation(self, fltr, proper=True):

        """
        This function ...
        :param fltr:
        :param proper:
        :return:
        """

        if proper: return self.analysis_run.get_evaluation_proper_residuals_for_filter(fltr)
        else: return self.analysis_run.get_evaluation_residuals_for_filter(fltr)

    # -----------------------------------------------------------------

    def has_residual_distribution_from_evaluation(self, fltr, proper=True):

        """
        This function ...
        :param fltr:
        :param proper:
        :return:
        """

        if proper: return self.analysis_run.has_evaluation_proper_residuals_distribution_for_filter(fltr)
        else: return self.analysis_run.has_evaluation_residuals_distribution_for_filter(fltr)

    # -----------------------------------------------------------------

    def get_residual_distribution_from_evaluation(self, fltr, proper=True):

        """
        This function ...
        :param fltr:
        :param proper:
        :return:
        """

        if proper: return self.analysis_run.get_evaluation_proper_residuals_distribution_for_filter(fltr)
        else: return self.analysis_run.get_evaluation_residuals_distribution_for_filter(fltr)

    # -----------------------------------------------------------------

    @memoize_method
    def get_faceon_image(self, filter_or_wavelength, spectral_convolution=False):

        """
        This fnuction ...
        :param filter_or_wavelength:
        :param spectral_convolution:
        :return:
        """

        # Filter?
        if isinstance(filter_or_wavelength, Filter): return self.faceon_cube.frame_for_filter(filter_or_wavelength, convolve=spectral_convolution)

        # Wavelength
        elif types.is_length_quantity(filter_or_wavelength):
            if spectral_convolution: raise ValueError("Spectral convolution cannot be applied when a wavelength is passed")
            return self.faceon_cube.get_frame_for_wavelength(filter_or_wavelength)

        # Invalid
        else: raise ValueError("Invalid argument")

    # -----------------------------------------------------------------

    @memoize_method
    def get_edgeon_image(self, filter_or_wavelength, spectral_convolution=False):

        """
        This function ...
        :param filter_or_wavelength:
        :param spectral_convolution:
        :return:
        """

        # Filter?
        if isinstance(filter_or_wavelength, Filter): return self.edgeon_cube.frame_for_filter(filter_or_wavelength, convolve=spectral_convolution)

        # Wavelength
        elif types.is_length_quantity(filter_or_wavelength):
            if spectral_convolution: raise ValueError("Spectral convolution cannot be applied when a wavelength is passed")
            return self.edgeon_cube.get_frame_for_wavelength(filter_or_wavelength)

        # Invalid
        else: raise ValueError("Invalid argument")

    # -----------------------------------------------------------------

    def plot_earth_images(self, filters, residuals=True, distributions=True, from_evaluation=None,
                          spectral_convolution=False, proper=True, path=None):

        """
        Thisf unction ...
        :param filters:
        :param residuals:
        :param distributions:
        :param from_evaluation:
        :param spectral_convolution:
        :param proper:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Plotting the observed and model images in the earth projection ...")

        # Create the plotter
        plotter = ResidualImageGridPlotter()

        # Set options
        plotter.config.distributions = distributions

        # Set the output filepath
        plotter.config.path = path

        # Loop over the filters
        for fltr in filters:

            # Define the image name
            image_name = str(fltr)

            # Get the frame
            observation = self.get_photometry_frame_for_filter(fltr)

            # Replace zeroes and negatives
            observation.replace_zeroes_by_nans()
            observation.replace_negatives_by_nans()

            # Add the frame to the plotter
            plotter.add_observation(image_name, observation)

            # Get modeled frame
            modeled = self.get_earth_image(fltr, from_evaluation=from_evaluation, spectral_convolution=spectral_convolution, proper=proper)

            # Replace zeroes and negatives
            modeled.replace_zeroes_by_nans()
            modeled.replace_negatives_by_nans()

            # Add the mock image to the plotter
            plotter.add_model(image_name, modeled)

            # Add residuals if present
            if residuals and self.has_residual_image_from_evaluation(fltr, proper=proper):
                residuals = self.get_residual_image_from_evaluation(fltr, proper=proper)
                plotter.add_residuals(image_name, residuals)

            # Add residuals distribution if present
            if distributions and self.has_residual_distribution_from_evaluation(fltr, proper=proper):
                distribution = self.get_residual_distribution_from_evaluation(fltr, proper=proper)
                plotter.add_distribution(image_name, distribution)

        # Run the plotter
        plotter.run()

    # -----------------------------------------------------------------

    def plot_faceon_images(self, filters, spectral_convolution=False, path=None):

        """
        This function ...
        :param filters:
        :param spectral_convolution:
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting the model images in the face-on projection ...")

        # Create the plotter
        plotter = StandardImageGridPlotter()

        # Set the output filepath
        plotter.config.path = path

        # Loop over the filters
        for fltr in filters:

            # Determine name
            image_name = str(fltr)

            # Get frame
            frame = self.get_faceon_image(fltr)

            # Replace zeroes and negatives
            frame.replace_zeroes_by_nans()
            frame.replace_negatives_by_nans()

            # Add the mock image to the plotter
            plotter.add_image(image_name, frame)

            # Run the plotter
        plotter.run()

    # -----------------------------------------------------------------

    def plot_edgeon_images(self, filters, spectral_convolution=False, path=None):

        """
        This function ...
        :param filters:
        :param spectral_convolution:
        :param path:
        :return:
        """

        # Inform the user
        log.info("Plotting the model images in the edge-on projection ...")

        # Create the plotter
        plotter = StandardImageGridPlotter()

        # Set the output filepath
        plotter.config.path = path

        # Loop over the filters
        for fltr in filters:

            # Determine name
            image_name = str(fltr)

            # Get frame
            frame = self.get_edgeon_image(fltr)

            # Replace zeroes and negatives
            frame.replace_zeroes_by_nans()
            frame.replace_negatives_by_nans()

            # Add the mock image to the plotter
            plotter.add_image(image_name, frame)

            # Run the plotter
        plotter.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_cubes_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("orientation", "string", "orientation of the datacube")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_cubes_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_cubes_definition, **kwargs)

        # Earth
        if config.orientation == earth_name: self.plot_earth_cube()

        # Face-on
        elif config.orientation == faceon_name: self.plot_faceon_cube()

        # Edge-on
        elif config.orientation == edgeon_name: self.plot_edgeon_cube()

        # Invalid
        else: raise ValueError("Invalid orientation: '" + config.orientation + "'")

    # -----------------------------------------------------------------

    def plot_earth_cube(self):

        """
        This function ...
        :return:
        """

        #from ...magic.tools import plotting
        #from ...magic.core.datacube import DataCube

        # Get simulation prefix
        #prefix = self.get_simulation_prefix(simulation_name)

        # Get the wavelength grid
        #wavelength_grid = self.get_wavelength_grid(simulation_name)

        # Load the datacube
        #datacube = DataCube.from_file(path, wavelength_grid)

        # Plot
        plot_datacube(datacube, title=instr_name, share_normalization=share_normalization, show_axes=False)

    # -----------------------------------------------------------------

    def plot_faceon_cube(self):

        """
        Thisn function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def plot_edgeon_cube(self):

        """
        Thisn function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @lazyproperty
    def total_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "total")

    # -----------------------------------------------------------------

    @property
    def has_total_absorption(self):
        return not fs.is_empty(self.total_absorption_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def bulge_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "bulge")

    # -----------------------------------------------------------------

    @property
    def has_bulge_absorption(self):
        return not fs.is_empty(self.bulge_absorption_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def disk_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "disk")

    # -----------------------------------------------------------------

    @property
    def has_disk_absorption(self):
        return not fs.is_empty(self.disk_absorption_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def old_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "old")

    # -----------------------------------------------------------------

    @property
    def has_old_absorption(self):
        return not fs.is_empty(self.old_absorption_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def young_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "young")

    # -----------------------------------------------------------------

    @property
    def has_young_absorption(self):
        return not fs.is_empty(self.young_absorption_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def sfr_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "sfr")

    # -----------------------------------------------------------------

    @property
    def has_sfr_absorption(self):
        return not fs.is_empty(self.sfr_absorption_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def unevolved_absorption_path(self):
        return fs.create_directory_in(self.absorption_path, "unevolved")

    # -----------------------------------------------------------------

    @property
    def has_unevolved_absorption(self):
        return not fs.is_empty(self.unevolved_absorption_path)

    # -----------------------------------------------------------------

    def get_absorption_path(self, component):

        """
        This function ...
        :param component:
        :return:
        """

        if component == total: return self.total_absorption_path
        elif component == bulge: return self.bulge_absorption_path
        elif component == disk: return self.disk_absorption_path
        elif component == old: return self.old_absorption_path
        elif component == young: return self.young_absorption_path
        elif component == sfr: return self.sfr_absorption_path
        elif component == unevolved: return self.unevolved_absorption_path
        else: raise ValueError("Invalid component name: '" + component + "'")

    # -----------------------------------------------------------------

    @memoize_method
    def get_dust_absorption_sed(self, component, dust_contribution=all_name):

        """
        This function ...
        :param component:
        :param dust_contribution:
        :return:
        """

        # Get directory path
        dirpath = self.get_absorption_path(component)
        if fs.is_empty(dirpath): raise IOError("The absorption data for the '" + component + "' simulation is not (yet) present: run the absorption analysis first")

        # Get filepath
        # For Simple absorption situations, it does not matter whether you want the diffuse, or all absorption (there is only diffuse)
        if dust_contribution == all_name:
            filepath = fs.join(dirpath, "absorption_all.dat")
            simple_filepath = fs.join(dirpath, "absorption.dat")
        elif dust_contribution == diffuse_name:
            filepath = fs.join(dirpath, "absorption_diffuse.dat")
            simple_filepath = fs.join(dirpath, "absorption.dat")
        elif dust_contribution == internal_name:
            filepath = fs.join(dirpath, "absorption_internal.dat")
            simple_filepath = None
        else: raise ValueError("Invalid dust contribution '" + dust_contribution + "': must be 'all', 'diffuse', or 'internal'")

        # Load the SED
        if fs.is_file(filepath): sed = SED.from_file(filepath)
        elif fs.is_file(simple_filepath): sed = SED.from_file(simple_filepath)
        else: raise IOError("Absorption SED file is missing")

        # Return
        return sed

    # -----------------------------------------------------------------

    @memoize_method
    def get_dust_emission_sed(self, component, dust_contribution=all_name):

        """
        This function ...
        :param component:
        :param dust_contribution:
        :return:
        """

        # Get directory path
        dirpath = self.get_absorption_path(component)
        if fs.is_empty(dirpath): raise IOError("The absorption data for the '" + component + "' simulation is not (yet) present: run the absorption analysis first")

        # Get filepath
        # For Simple absorption situations, it does not matter whether you want the diffuse, or all absorption (there is only diffuse)
        if dust_contribution == all_name:
            filepath = fs.join(dirpath, "emission_all.dat")
            simple_filepath = fs.join(dirpath, "emission.dat")
        elif dust_contribution == diffuse_name:
            filepath = fs.join(dirpath, "emission_diffuse.dat")
            simple_filepath = fs.join(dirpath, "emission.dat")
        elif dust_contribution == internal_name:
            filepath = fs.join(dirpath, "emission_internal.dat")
            simple_filepath = None
        else: raise ValueError("Invalid dust contribution '" + dust_contribution + "': must be 'all', 'diffuse', or 'internal'")

        # Load the SED
        if fs.is_file(filepath): sed = SED.from_file(filepath)
        elif fs.is_file(simple_filepath): sed = SED.from_file(simple_filepath)
        else: raise IOError("Emission SED file is missing")

        # Return
        return sed

    # -----------------------------------------------------------------

    @memoize_method
    def get_observed_stellar_sed(self, component, dust_contribution=all_name):

        """
        This function ...
        :param component:
        :param dust_contribution:
        :return:
        """

        # Get directory path
        dirpath = self.get_absorption_path(component)
        if fs.is_empty(dirpath): raise IOError("The absorption data for the '" + component + "' simulation is not (yet) present: run the absorption analysis first")

        # Get filepath
        # For Simple absorption situations, it does not matter whether you want the diffuse, or all absorption (there is only diffuse)
        if dust_contribution == all_name:
            filepath = fs.join(dirpath, "observed_stellar_all.dat")
            simple_filepath = fs.join(dirpath, "observed_stellar.dat")
        elif dust_contribution == diffuse_name:
            filepath = fs.join(dirpath, "observed_stellar_diffuse.dat")
            simple_filepath = fs.join(dirpath, "observed_stellar.dat")
        elif dust_contribution == internal_name:
            filepath = fs.join(dirpath, "observed_stellar_internal.dat")
            simple_filepath = None
        else: raise ValueError("Invalid dust contribution '" + dust_contribution + "': must be 'all', 'diffuse', or 'internal'")

        # Load the SED
        if fs.is_file(filepath): sed = SED.from_file(filepath)
        elif fs.is_file(simple_filepath): sed = SED.from_file(simple_filepath)
        else: raise IOError("Observed stellar SED file is missing")

        # Return sed
        return sed

    # -----------------------------------------------------------------

    def get_scattered_sed(self, component):

        """
        This function ...
        :param component:
        :return:
        """

        # Get the simulations
        simulations = self.simulations[component]

        # Return
        return simulations.observed_sed_scattered if simulations.has_full_sed else None

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_paper_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Which plot
        definition.add_required("which", "positive_integer", "index of the plot to make")

        # Path for plot file
        definition.add_optional("path", "new_path", "save plot to file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_paper_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_paper_definition, **kwargs)

        # Plot #1: SEDs
        if config.which == 1: self.plot_paper1(path=config.path)

        # Plot #2: HEATING
        elif config.which == 2: self.plot_paper2(path=config.path)

        # Plot #3: SPECTRAL HEATING
        elif config.which == 3: self.plot_paper3(path=config.path)

        # Plot #4: CORRELATION BETWEEN PIXEL sSFR and FUNEV VALUES
        elif config.which == 4: self.plot_paper4(path=config.path)

        # Invalid
        else: raise ValueError("Invalid plot index: " + str(config.which))

    # -----------------------------------------------------------------

    def plot_paper1(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Creating the paper SEDs plot ...")

        # Set limits
        unit = u("Lsun", density=True)
        min_wavelength = q("0.05 micron")
        max_wavelength = q("2000 micron")
        #min_flux = q("1e-13.5 W/m2", density=True)
        #max_flux = q("1e-10 W/m2", density=True)
        #min_flux = q("10**6.5 Lsun", density=True) # doesn't parse because is splitted at **
        #max_flux = q("10**11 Lsun", density=True) # doesn't parse because is splitted at **
        min_flux = PhotometricQuantity(10**6.5, unit)
        max_flux = PhotometricQuantity(10**10, unit)

        # Create figure
        figsize = (20,6,)
        figure = MPLFigure(size=figsize)

        # Create 2 plots
        main_plots, residual_plots = figure.create_row_of_sed_plots(2, nresiduals=[1,0])

        # Plot first panel
        seds1 = OrderedDict()

        # Define seperate filter tuples
        fitting_filters = tuple(self.fitting_run.fitting_filters)
        hfi_and_2mass_filters = tuple(self.hfi_filters + self.jhk_filters)

        # Set options
        plot_options1 = dict()
        plot_options1["Total"] = {"residuals": True, "residual_color": "darkgrey"}
        plot_options1["Old"] = {"residuals": False}
        plot_options1["Young"] = {"residuals": False}
        plot_options1["Ionizing"] = {"residuals": False}
        plot_options1["Mock fluxes"] = {"only_residuals": True, "as_reference": False}
        plot_options1["Observation (other)"] = {"as_reference": False, "color": "g", "join_residuals": "Observation (fitting)"}
        plot_options1["Summed"] = {"ghost": True}
        #plot_options1["Summed_nosfr"] = {"ghost": True, "residuals": False}
        #plot_options1["Summed_nosfr_mir"] = {"ghost": True, "residuals": False, "linestyle": ":", "color": "deeppink"}

        # Add component simulation SEDs
        total_sed = self.get_simulation_sed(total)
        old_sed = self.get_simulation_sed(old)
        young_sed = self.get_simulation_sed(young)
        sfr_sed = self.get_simulation_sed(sfr)
        #summed_sed = old_sed + young_sed + sfr_sed
        #summed_sed_no_sfr = old_sed + young_sed
        #summed_sed_no_sfr_mir = summed_sed_no_sfr.splice(min_wavelength=q("15 micron"), max_wavelength=q("150 micron"))

        # Add simulated SEDs
        seds1["Total"] = total_sed
        seds1["Old"] = old_sed
        seds1["Young"] = young_sed
        seds1["Ionizing"] = sfr_sed
        #seds1["Summed"] = summed_sed
        #seds1["Summed_nosfr"] = summed_sed_no_sfr
        #seds1["Summed_nosfr_mir"] = summed_sed_no_sfr_mir

        # Add mock fluxes
        seds1["Mock fluxes"] = self.mock_fluxes

        # Add observed fluxes
        seds1["Observation (fitting)"] = self.get_reference_sed(clipped_name, additional_error=0.1, filters=fitting_filters) # 10 % additional errorbars
        seds1["Observation (other)"] = self.get_reference_sed(clipped_name, additional_error=0.1, filters=hfi_and_2mass_filters)

        # Plot FIRST
        plot_seds(seds1, figure=figure, main_plot=main_plots[0], residual_plots=residual_plots[0], show=False,  # don't show yet
                  min_wavelength=min_wavelength, max_wavelength=max_wavelength, min_flux=min_flux, max_flux=max_flux,
                  distance=self.galaxy_distance, options=plot_options1, tex=False, unit=unit,
                  residual_reference="observations", smooth_residuals=True, observations_legend_ncols=1, instruments_legend_ncols=3,
                  only_residuals_legend=True, observations_residuals_legend_location="lower left")

        # Second panel
        seds2 = OrderedDict()

        # Add SEDs
        seds2["Observed stellar"] = self.get_observed_stellar_sed("total")
        seds2["Absorbed"] = self.get_dust_absorption_sed("total")
        seds2["Dust"] = self.get_dust_emission_sed("total")
        seds2["Scattered"] = self.get_scattered_sed("total")
        seds2["Internal dust (SFR)"] = self.get_dust_emission_sed("sfr", dust_contribution="internal")

        # Set options
        plot_options2 = dict()
        plot_options2["Absorbed"] = {"above": "Observed stellar", "above_name": "Intrinsic stellar"}
        plot_options2["Dust"] = {"above": "Observed stellar"}
        plot_options2["Internal dust (SFR)"] = {"above": "Observed stellar", "color": "lightgrey", "fill": False} # color does not work yet

        # Plot SECOND
        plot_seds(seds2, figure=figure, main_plot=main_plots[1], show=False, # don't show yet
                  min_wavelength=min_wavelength, max_wavelength=max_wavelength, min_flux=min_flux, max_flux=max_flux,
                  distance=self.galaxy_distance, options=plot_options2, tex=False, unit=unit, yaxis_position="right")

        # Hide some tick labels
        #figure.figure.canvas.draw() # GETTING TICK LABELS ONLY WORKS IF WE DRAW FIRST
        # NO LONGER NECESSARY

        # DOESN'T DO ANYTHING??
        #residual_plots[0][-1].hide_last_xtick_label()
        #main_plots[1].hide_first_xtick_label()

        # Save or show
        if path is not None: figure.saveto(path)
        else: figure.show()

    # -----------------------------------------------------------------

    def plot_paper2(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Creating the paper bolometric heating plot ...")

        # Create figure
        figsize = (12, 6,)
        figure = MPLFigure(size=figsize)

        # Set width ratios
        width_ratios = [0.5, 0.5]

        # Create 2 plots
        #plot0, plot1 = figure.create_row(2, wspace=0, width_ratios=width_ratios)
        plot0, plot1 = figure.create_row(2, width_ratios=width_ratios)

        # Get the heating map
        frame = self.get_heating_map("cells")

        # Zoom from the normal galaxy truncation
        zoom = 1.1
        radius = self.physical_truncation_radius * zoom

        # Assume center pixel is the center of the map (galaxy)
        center_pix = frame.pixel_center

        # Plot
        plot_map_offset(frame, center_pix, radius, u("5 kpc"), interval=self.heating_fraction_interval, colorbar=False, cmap="inferno", plot=plot0)

        # Plot distribution
        #print(self.heating_distribution)
        #distr_axes = figure.figure.add_subplot(gs[1])
        #plot_distribution(self.heating_distribution, axes=distr_axes, cmap="inferno", cmap_interval=self.heating_fraction_interval)
        plot_distribution(self.heating_distribution, cmap="inferno", cmap_interval=self.heating_fraction_interval, plot=plot1, show_mean=True, show_median=True, show_most_frequent=False)
        plot1.set_xlabel("Heating fraction by unevolved stars")
        plot1.hide_yaxis()

        # Save or show
        if path is not None: figure.saveto(path)
        else: figure.show()

    # -----------------------------------------------------------------

    @lazyproperty
    def sdss_u_filter(self):
        return parse_filter("SDSS u")

    # -----------------------------------------------------------------

    @property
    def sdss_u_wavelength(self):
        return self.sdss_u_filter.wavelength

    # -----------------------------------------------------------------

    @lazyproperty
    def sdss_g_filter(self):
        return parse_filter("SDSS g")

    # -----------------------------------------------------------------

    @property
    def sdss_g_wavelength(self):
        return self.sdss_g_filter.wavelength

    # -----------------------------------------------------------------

    @lazyproperty
    def sdss_r_filter(self):
        return parse_filter("SDSS r")

    # -----------------------------------------------------------------

    @property
    def sdss_r_wavelength(self):
        return self.sdss_r_filter.wavelength

    # -----------------------------------------------------------------

    def plot_paper3(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Creating the paper spectral heating plot ...")

        # Get curve
        curve = self.get_spectral_absorption_fraction_curve(cells_name)

        # Get maps
        fuv_map = self.get_spectral_heating_map(cells_name, self.fuv_filter)
        nuv_map = self.get_spectral_heating_map(cells_name, self.nuv_filter)
        u_map = self.get_spectral_heating_map(cells_name, self.sdss_u_filter)
        g_map = self.get_spectral_heating_map(cells_name, self.sdss_g_filter)
        r_map = self.get_spectral_heating_map(cells_name, self.sdss_r_filter)

        #plot_map(r_map, interval=self.heating_fraction_interval)

        # Get filter wavelengths
        filter_wavelengths = [self.fuv_wavelength, self.nuv_wavelength, self.sdss_u_wavelength, self.sdss_g_wavelength, self.sdss_r_wavelength]

        # Create grid
        #figsize = (25, 15,)
        figsize = (18,12,) # 3:2
        figure = MPLFigure(size=figsize)
        nrows = 2
        ncols = 3
        rows = figure.create_grid(nrows, ncols, wspace=0, hspace=0)
        first_row = rows[0]
        second_row = rows[1]

        first_plot = first_row[0]
        first_plot.set_xaxis_position("top")
        first_plot.set_yaxis_position("left")

        # Test
        for plot in first_row: plot.axes.set(adjustable='box-forced')
        for plot in second_row: plot.axes.set(adjustable='box-forced')

        # Plot curve
        plot_curve(curve, xlimits=self.heating_absorption_wavelength_limits, ylimits=self.heating_fraction_interval,
                   xlog=True, y_label=self.heating_fraction_name, plot=first_row[0], vlines=filter_wavelengths)

        # Zoom from the normal galaxy truncation
        zoom = 1.1
        radius = self.physical_truncation_radius * zoom

        # Plot
        # Assume center pixel is the center of the map (galaxy)
        cmap = "inferno"
        offset_step = q("5 kpc")
        plot_map_offset(fuv_map, fuv_map.pixel_center, radius, offset_step, interval=self.heating_fraction_interval, cmap=cmap, plot=first_row[1])
        first_row[1].hide_yaxis()
        first_row[1].set_xaxis_position("top")

        plot_map_offset(nuv_map, nuv_map.pixel_center, radius, offset_step, interval=self.heating_fraction_interval, cmap=cmap, plot=first_row[2])
        first_row[2].set_xaxis_position("top")
        first_row[2].set_yaxis_position("right")

        plot_map_offset(u_map, u_map.pixel_center, radius, offset_step, interval=self.heating_fraction_interval, cmap=cmap, plot=second_row[0])

        plot_map_offset(g_map, g_map.pixel_center, radius, offset_step, interval=self.heating_fraction_interval, cmap=cmap, plot=second_row[1])
        second_row[1].hide_yaxis()

        plot_map_offset(r_map, r_map.pixel_center, radius, offset_step, interval=self.heating_fraction_interval, cmap=cmap, plot=second_row[2])
        second_row[2].set_yaxis_position("right")

        # ADD COLORBAR AXES
        last_plot = second_row[2]
        #colorbar_plot = figure.add_plot(1.01, last_plot.bounding_box.y0, 0.02, first_plot.bounding_box.y1-last_plot.bounding_box.y0)
        cb = figure.add_colorbar(1.01, last_plot.bounding_box.y0, 0.02, first_plot.bounding_box.y1-last_plot.bounding_box.y0, "inferno", "vertical", self.heating_fraction_interval)

        figure.tight_layout()

        # Save or show
        if path is not None: figure.saveto(path)
        else: figure.show()

    # -----------------------------------------------------------------

    @property
    def correlations_path(self):
        return self.analysis_run.correlations_path

    # -----------------------------------------------------------------

    @property
    def ssfr_funev_correlations_path(self):
        return fs.join(self.correlations_path, "sSFR-Funev")

    # -----------------------------------------------------------------

    @property
    def m51_ssfr_funev_path(self):
        return fs.join(self.ssfr_funev_correlations_path, "m51.dat")

    # -----------------------------------------------------------------

    @lazyproperty
    def m51_ssfr_funev_scatter(self):
        return Scatter2D.from_file(self.m51_ssfr_funev_path)

    # -----------------------------------------------------------------

    @property
    def m31_ssfr_funev_path(self):
        return fs.join(self.ssfr_funev_correlations_path, "m31.dat")

    # -----------------------------------------------------------------

    @lazyproperty
    def m31_ssfr_funev_scatter(self):
        return Scatter2D.from_file(self.m31_ssfr_funev_path)

    # -----------------------------------------------------------------

    def get_pixels_ssfr_funev_path(self, method):

        """
        This function ...
        :param method:
        :return:
        """

        if method == salim_name: return fs.join(self.ssfr_funev_correlations_path, "pixels_" + salim_name + ".dat")
        elif method == ke_name: return fs.join(self.ssfr_funev_correlations_path, "pixels_" + ke_name + ".dat")
        elif method == mappings_name: return fs.join(self.ssfr_funev_correlations_path, "pixels_" + mappings_name + ".dat")
        elif method == mappings_ke_name: return fs.join(self.ssfr_funev_correlations_path, "pixels_" + mappings_ke_name + ".dat")
        else: raise ValueError("Invalid method: '" + method + "'")

    # -----------------------------------------------------------------

    @memoize_method
    def get_pixels_ssfr_funev_scatter(self, method):

        """
        This function ...
        :param method:
        :return:
        """

        # Get path
        path = self.get_pixels_ssfr_funev_path(method)

        # Load and return
        return Scatter2D.from_file(path)

    # -----------------------------------------------------------------

    def get_cells_ssfr_funev_path(self, method):

        """
        This function ...
        :return:
        """

        if method == salim_name: return fs.join(self.ssfr_funev_correlations_path, "cells_" + salim_name + ".dat")
        elif method == ke_name: return fs.join(self.ssfr_funev_correlations_path, "cells_" + ke_name + ".dat")
        elif method == mappings_name: return fs.join(self.ssfr_funev_correlations_path, "cells_" + mappings_name + ".dat")
        elif method == mappings_ke_name: return fs.join(self.ssfr_funev_correlations_path, "cells_" + mappings_ke_name + ".dat")
        else: raise ValueError("Invalid method: '" + method + "'")

    # -----------------------------------------------------------------

    @memoize_method
    def get_cells_ssfr_funev_scatter(self, method):

        """
        This function ...
        :param method:
        :return:
        """

        # Get path
        path = self.get_cells_ssfr_funev_path(method)

        # Load and return
        return Scatter2D.from_file(path)

    # -----------------------------------------------------------------

    def plot_paper4(self, path=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Creating the paper sSFR - Funev pixel correlation plot ...")

        import mpl_scatter_density  # NOQA

        # Create the figure
        figsize = (12, 6,)
        figure = MPLFigure(size=figsize)

        # Create row of plots
        width_ratios = [0.5, 0.5]
        plot0, plot1 = figure.create_row(2, width_ratios=width_ratios, projections=["scatter_density", "scatter_density"])

        # Get pixel scatter
        import numpy as np
        pixels = self.get_pixels_ssfr_funev_scatter("ke")
        #print(len(pixels))
        valid_pixels = pixels[pixels.y_name] > 0.005
        valid_ssfr = np.asarray(pixels[pixels.x_name])[valid_pixels]
        valid_funev = np.asarray(pixels[pixels.y_name])[valid_pixels]
        pixels = Scatter2D.from_xy(valid_ssfr, valid_funev, "sSFR", "Funev", x_unit=pixels.x_unit)
        #print(len(pixels))

        # Create scatters
        scatters1 = OrderedDict()
        scatters1["M81 pixels"] = pixels
        scatters1["M31 pixels"] = self.m31_ssfr_funev_scatter
        scatters1["M51 pixels"] = self.m51_ssfr_funev_scatter

        # Make the first plot
        xlimits = [1e-13,1e-9]
        ylimits = [0,1]
        xlog = True
        ylog = False
        #plot_scatters_astrofrog(scatters1, xlimits=config.xlimits, ylimits=config.ylimits, xlog=config.xlog, ylog=False, path=config.path, colormaps=False)
        plot_scatters_astrofrog(scatters1, xlimits=xlimits, ylimits=ylimits, xlog=xlog, ylog=ylog, colormaps=False, plot=plot0)

        # Make the second plot
        #ylimits = [0.002,1] # for log
        cells = self.get_cells_ssfr_funev_scatter("ke")
        plot_scatter_astrofrog(cells, xlimits=xlimits, ylimits=ylimits, xlog=True, ylog=False, plot=plot1, color="red")

        # Save or show
        if path is not None: figure.saveto(path)
        else: figure.show()

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_absorption_map_definition(self):
        
        """
        This function ...
        :return: 
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Add options
        definition.add_positional_optional("component", "string", "component", total, choices=components)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_optional("dust_contribution", "string", "dust contribution", default=all_name, choices=dust_contributions)

        # Flags
        definition.add_flag("specific", "specific absorption luminosities (per dust mass)")

        # Return
        return definition
        
    # -----------------------------------------------------------------

    @lazyproperty
    def projected_heating_absorptions_path(self):
        return fs.join(self.projected_heating_path, "absorptions")

    # -----------------------------------------------------------------

    def get_absorption_map_path(self, contribution, projection=earth_name):

        """
        This function ...
        :param contribution:
        :param projection:
        :return:
        """

        # Total
        if contribution == total: return fs.join(self.projected_heating_absorptions_path, "total_" + projection + ".fits")
        elif contribution == young: return fs.join(self.projected_heating_absorptions_path, "young_" + projection + ".fits")
        elif contribution == sfr: return fs.join(self.projected_heating_absorptions_path, "ionizing_" + projection + ".fits")
        elif contribution == internal_name: return fs.join(self.projected_heating_absorptions_path, "internal_" + projection + ".fits")
        else: raise ValueError("Invalid contribution")

    # -----------------------------------------------------------------

    @memoize_method
    def get_absorption_map(self, contribution, projection=earth_name, dust_contribution=all_name):

        """
        This function ...
        :param contribution:
        :param projection:
        :param dust_contribution:
        :return:
        """

        # Total
        if contribution == total:

            # Diffuse dust
            if dust_contribution == diffuse_name:

                all_map = Frame.from_file(self.get_absorption_map_path(total, projection=projection))
                internal_map = Frame.from_file(self.get_absorption_map_path(internal_name, projection=projection))
                all_map, internal_map = uniformize(all_map, internal_map, convolve=False)

                # Return
                return all_map - internal_map

            # All dust
            elif dust_contribution == all_name: return Frame.from_file(self.get_absorption_map_path(total, projection=projection))

            # Invalid
            else: raise ValueError("Invalid dust contribution for total model: '" + dust_contribution + "'")

        # Bulge
        elif contribution == bulge: raise ValueError("Absorption maps for the bulge component are not available")

        # DIsk
        elif contribution == disk: raise ValueError("Absorption maps for the disk component are not available")

        # Old
        elif contribution == old:

            total_map = Frame.from_file(self.get_absorption_map_path(total, projection=projection))
            internal_map = Frame.from_file(self.get_absorption_map_path(internal_name, projection=projection))
            young_map = Frame.from_file(self.get_absorption_map_path(young, projection=projection))
            sfr_map = Frame.from_file(self.get_absorption_map_path(sfr, projection=projection))
            total_map, internal_map, young_map, sfr_map = uniformize(total_map, internal_map, young_map, sfr_map, convolve=False)

            # Return
            return total_map - internal_map - young_map - sfr_map

        # Young
        elif contribution == young:

            if dust_contribution == diffuse_name or dust_contribution == all_name: return Frame.from_file(self.get_absorption_map_path(young, projection=projection))
            else: raise ValueError("Invalid dust contribution for young component: '" + dust_contribution + "'")

        # Star formation
        elif contribution == sfr:

            # Diffuse dust
            if dust_contribution == diffuse_name: return Frame.from_file(self.get_absorption_map_path(sfr, projection=projection))

            # Internal dust
            elif dust_contribution == internal_name: return Frame.from_file(self.get_absorption_map_path(internal_name, projection=projection))

            # All dust
            elif dust_contribution == all_name:

                diffuse_map = Frame.from_file(self.get_absorption_map_path(sfr, projection=projection))
                internal_map = Frame.from_file(self.get_absorption_map_path(internal_name, projection=projection))
                diffuse_map, internal_map = uniformize(diffuse_map, internal_map, convolve=False)

                # Return
                return diffuse_map + internal_map

            # Invalid
            else: raise ValueError("Invalid dust contribution: '" + dust_contribution + "'")

        # Unevolved
        elif contribution == unevolved:

            # Diffuse dust
            if dust_contribution == diffuse_name:

                young_map = Frame.from_file(self.get_absorption_map_path(young, projection=projection))
                sfr_map = Frame.from_file(self.get_absorption_map_path(sfr, projection=projection))
                young_map, sfr_map = uniformize(young_map, sfr_map, convolve=False)

                # Return
                return young_map + sfr_map

            # Diffuse dust
            elif dust_contribution == all_name:

                young_map = Frame.from_file(self.get_absorption_map_path(young, projection=projection))
                sfr_map = Frame.from_file(self.get_absorption_map_path(sfr, projection=projection))
                internal_map = Frame.from_file(self.get_absorption_map_path(internal_name, projection=projection))
                young_map, sfr_map, internal_map = uniformize(young_map, sfr_map, internal_map, convolve=False)

                # Return
                return young_map + sfr_map + internal_map

            # Invalid
            else: raise ValueError("Invalid dust contribution for unevolved component: '" + dust_contribution + "'")

        # Invalid
        else: raise ValueError("Invalid contribution: '" + contribution + "'")

    # -----------------------------------------------------------------

    @memoize_method
    def get_specific_absorption_map(self, contribution, projection=earth_name, dust_contribution=all_name):

        """
        This function ...
        :param contribution:
        :param projection:
        :param dust_contribution:
        :return:
        """

        # Get maps
        absorption = self.get_absorption_map(contribution, projection=projection, dust_contribution=dust_contribution)
        absorption.convert_to_corresponding_brightness_unit()
        dust_mass = self.get_dust_mass_map(orientation=projection)
        dust_mass /= dust_mass.physical_pixelscale.average
        absorption, dust_mass = uniformize(absorption, dust_mass, convert=False, convolve=False)
        #print(absorption.unit)
        #print(dust_mass.unit)
        absorption.convert_to("Lsun")
        dust_mass *= dust_mass.physical_pixelscale.average

        # Return
        specific_absorption =  absorption / dust_mass
        #print(specific_absorption.unit)
        return specific_absorption

    # -----------------------------------------------------------------

    def plot_absorption_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_absorption_map_definition, **kwargs)

        # Specific absorption
        if config.specific:

            # Get the map
            frame = self.get_specific_absorption_map(config.component, projection=config.orientation, dust_contribution=config.dust_contribution)

            # Plot
            frame.replace_by_nans_where_greater_than(20000)
            plot_map(frame, scale="log", interval=(50,15000,), cmap="inferno")

        # Absorption luminosity
        else:

            # Get the map
            frame = self.get_absorption_map(config.component, projection=config.orientation, dust_contribution=config.dust_contribution)

            # Plot
            plot_map(frame, scale="log", cmap="inferno")

    # -----------------------------------------------------------------

    @property
    def heating_path(self):
        return self.analysis_run.heating_path

    # -----------------------------------------------------------------

    @lazyproperty
    def cell_heating_path(self):
        return fs.join(self.analysis_run.heating_path, "cell")

    # -----------------------------------------------------------------

    @lazyproperty
    def projected_heating_path(self):
        return fs.join(self.analysis_run.heating_path, "projected")

    # -----------------------------------------------------------------

    @lazyproperty
    def projected_heating_maps_path(self):
        return fs.join(self.projected_heating_path, "maps")

    # -----------------------------------------------------------------

    @lazyproperty
    def spectral_heating_path(self):
        return fs.join(self.analysis_run.heating_path, "spectral")

    # -----------------------------------------------------------------

    @lazyproperty
    def spectral_heating_cells_path(self):
        return fs.join(self.spectral_heating_path, "3D")

    # -----------------------------------------------------------------

    @lazyproperty
    def spectral_heating_maps_path(self):
        return fs.join(self.spectral_heating_path, "maps")

    # -----------------------------------------------------------------

    @lazyproperty
    def spectral_heating_curves_path(self):
        return fs.join(self.spectral_heating_path, "curves")

    # -----------------------------------------------------------------

    @property
    def heating_distribution_path(self):
        return fs.join(self.cell_heating_path, "distribution_total.dat")

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_distribution(self):
        return Distribution.from_file(self.heating_distribution_path)

    # -----------------------------------------------------------------

    @property
    def heating_distribution_diffuse_path(self):
        return fs.join(self.cell_heating_path, "distribution_diffuse.dat")

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_distribution_diffuse(self):
        return Distribution.from_file(self.heating_distribution_diffuse_path)

    # -----------------------------------------------------------------

    def get_heating_map(self, projection, fltr=None, correct=True):

        """
        This function ...
        :param projection:
        :param fltr:
        :param correct:
        :return:
        """

        # Spectral heating
        if fltr is not None: return self.get_spectral_heating_map(projection, fltr, correct=correct)

        # Bolometric heating
        else: return self.get_bolometric_heating_map(projection, correct=correct)

    # -----------------------------------------------------------------

    def get_heating_mask(self, projection, fltr=None):

        """
        This function ...
        :param projection:
        :param fltr:
        :return:
        """

        # Spectral heating
        if fltr is not None: return self.get_spectral_heating_mask(projection, fltr)

        # Bolometric heating
        else: return self.get_bolometric_heating_mask(projection)

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_absorption_filters(self):
        return lazy_broad_band_filter_list("GALEX,SDSS")

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_emission_filters(self):
        return lazy_broad_band_filter_list("W3,W4,MIPS 24mu,Herschel")

    # -----------------------------------------------------------------

    @lazyproperty
    def spectral_heating_filters(self):
        return self.heating_absorption_filters + self.heating_emission_filters

    # -----------------------------------------------------------------

    def get_spectral_heating_map_path(self, projection, fltr):

        """
        This function ...
        :param projection:
        :param fltr:
        :return:
        """

        # Absorption or emission filter?
        if fltr in self.heating_absorption_filters: abs_or_em = absorption_name
        elif fltr in self.heating_emission_filters: abs_or_em = emission_name
        else: raise ValueError("The '" + str(fltr) + "' filter does not have an absorption or emission heating fraction map")

        # Determine path
        if projection == cells_name: return fs.join(self.spectral_heating_cells_path, abs_or_em + "_" + str(fltr) + "_fixed.fits")
        elif projection == cells_edgeon_name: raise NotImplementedError("Spectral heating maps do not exist from cells and projected edge-on")
        elif projection == midplane_name: raise NotImplementedError("Spectral heating fraction maps do not exist for the midplane")
        elif projection == earth_name: return fs.join(self.spectral_heating_maps_path, "earth_" + abs_or_em + "_" + str(fltr) + ".fits")
        elif projection == faceon_name: return fs.join(self.spectral_heating_maps_path, "faceon_" + abs_or_em + "_" + str(fltr) + ".fits")
        elif projection == edgeon_name: return fs.join(self.spectral_heating_maps_path, "edgeon_" + abs_or_em + "_" + str(fltr) + ".fits")
        else: raise ValueError("Invalid projection: '" + projection + "'")

    # -----------------------------------------------------------------

    def get_spectral_heating_map(self, projection, fltr, correct=True):

        """
        This function ...
        :param projection:
        :param fltr:
        :param correct:
        :return:
        """

        # Get the path
        path = self.get_spectral_heating_map_path(projection, fltr)

        # Open the frame
        frame = Frame.from_file(path)

        # Correct
        if correct: self.correct_heating_map(frame)

        # Return
        return frame

    # -----------------------------------------------------------------

    def get_spectral_heating_mask(self, projection, fltr):

        """
        This function ...
        :param projection:
        :param fltr:
        :return:
        """

        # Determine path
        if projection == cells_name: path, mask_value = self.get_spectral_heating_map_path(cells_name, fltr), "nan" # CELLS HAVE NANS
        elif projection == cells_edgeon_name: path, mask_value = self.get_bolometric_heating_map_path(cells_edgeon_name), "nan"
        elif projection == midplane_name: path, mask_value = self.get_spectral_heating_map_path(cells_name, fltr), "nan" # CELLS HAVE NANS
        elif projection == earth_name: path, mask_value = self.get_bolometric_heating_map_path(earth_name), "zero" # these are better interpolated than the spectral heating maps
        elif projection == faceon_name: path, mask_value = self.get_spectral_heating_map_path(cells_name, fltr), "nan"
        elif projection == edgeon_name: path, mask_value = self.get_bolometric_heating_map_path(cells_edgeon_name), "nan"
        else: raise ValueError("Invalid projection: '" + projection + "'")

        # Get mask
        if mask_value == "nan": return Mask.nans_from_file(path)
        elif mask_value == "zero": return Mask.zeroes_from_file(path)
        else: raise RuntimeError("Invalid mask value: '" + mask_value + "'")

    # -----------------------------------------------------------------

    def get_bolometric_heating_map_path(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        # Get path
        if projection == cells_name: return fs.join(self.cell_heating_path, "highres_faceon_interpolated.fits") # cells: only diffuse?
        elif projection == cells_edgeon_name: return fs.join(self.cell_heating_path, "highres_edgeon_interpolated.fits") # cells: only diffuse?
        elif projection == midplane_name: return fs.join(self.cell_heating_path, "highres_midplane_interpolated.fits") # cells: only diffuse?
        elif projection == earth_name: return fs.join(self.projected_heating_maps_path, "earth.fits") # there is also diffuse
        elif projection == edgeon_name: return fs.join(self.projected_heating_maps_path, "edgeon.fits") # there is also diffuse
        elif projection == faceon_name: return fs.join(self.projected_heating_maps_path, "faceon.fits") # there is also diffuse
        else: raise ValueError("Invalid projection: '" + projection + "'")

    # -----------------------------------------------------------------

    def correct_heating_map(self, frame):

        """
        This function ...
        :param frame:
        :return:
        """

        #frame.replace_by_nans_where_equal_to(1)
        frame.replace_by_nans_where_greater_than(0.95)

    # -----------------------------------------------------------------

    def get_bolometric_heating_map(self, projection, correct=True):

        """
        This function ...
        :param projection:
        :param correct:
        :return:
        """

        # Get the path
        path = self.get_bolometric_heating_map_path(projection)

        # Open the frame
        frame = Frame.from_file(path)

        # Correct
        if correct: self.correct_heating_map(frame)

        # Return
        return frame

    # -----------------------------------------------------------------

    def get_bolometric_heating_mask(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        # Determine path
        if projection == cells_name: path, mask_value = self.get_bolometric_heating_map_path(cells_name), "nan"  # CELLS HAVE NANS
        elif projection == cells_edgeon_name: path, mask_value = self.get_bolometric_heating_map_path(cells_edgeon_name), "nan" # CELLS HAVE NANS
        elif projection == midplane_name: path, mask_value = self.get_bolometric_heating_map_path(midplane_name), "nan"  # CELLS HAVE NANS
        elif projection == earth_name: path, mask_value = self.get_bolometric_heating_map_path(earth_name), "zero"  # these are better interpolated than the spectral heating maps
        elif projection == faceon_name: path, mask_value = self.get_bolometric_heating_map_path(faceon_name), "zero"  # these are better interpolated than the spectral heating maps
        elif projection == edgeon_name: path, mask_value = self.get_bolometric_heating_map_path(edgeon_name), "zero"  # these are better interpolated than the spectral heating maps
        else: raise ValueError("Invalid projection: '" + projection + "'")

        # Get mask
        if mask_value == "nan": return Mask.nans_from_file(path)
        elif mask_value == "zero": return Mask.zeroes_from_file(path)
        else: raise RuntimeError("Invalid mask value: '" + mask_value + "'")

    # -----------------------------------------------------------------

    @property
    def default_heating_projection(self):
        return cells_name

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_projections(self):
        return [cells_name, cells_edgeon_name, midplane_name, earth_name, edgeon_name, faceon_name]

    # -----------------------------------------------------------------

    @property
    def heating_plot_names(self):
        return [map_name, difference_name, distribution_name, curve_name]

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_fraction_interval(self):
        return (0,1,)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_heating_map_definition(self):

        """
        This unction ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Orientation
        definition.add_positional_optional("projection", "string", "projection of heating map", self.default_heating_projection, self.heating_projections)

        # Filter
        definition.add_optional("filter", "broad_band_filter", "filter for which to plot the heating fraction (in absorption or emission)", choices=self.spectral_heating_filters)

        # Save to?
        definition.add_optional("path", "new_path", "save plot file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_heating_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_heating_map_definition, **kwargs)

        # Get the heating map
        frame = self.get_heating_map(config.projection, fltr=config.filter)

        # Get mask
        mask = self.get_heating_mask(config.projection, fltr=config.filter)

        # Apply the mask
        frame.apply_mask_nans(mask)

        # Plot
        plot_map(frame, interval=self.heating_fraction_interval, path=config.path)

    # -----------------------------------------------------------------

    @property
    def default_heating_difference_projection(self):
        return faceon_name

    # -----------------------------------------------------------------

    @property
    def heating_difference_projections(self):
        return [midplane_name, faceon_name, edgeon_name]

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_heating_difference_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Orientation
        definition.add_positional_optional("projection", "string", "projection of heating map", self.default_heating_difference_projection, self.heating_difference_projections)

        # Filter
        definition.add_optional("filter", "broad_band_filter", "filter for which to plot the heating fraction (in absorption or emission)", choices=self.spectral_heating_filters)

        # Save to?
        definition.add_optional("path", "new_path", "save plot file")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_heating_difference_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Import
        from pts.magic.plot.imagegrid import plot_one_residual_aplpy

        # Get config
        config = self.get_config_from_command(command, self.plot_heating_difference_definition, **kwargs)

        # Midplane
        if config.projection == midplane_name:

            first = self.get_heating_map(cells_name, fltr=config.filter)
            second = self.get_heating_map(midplane_name, fltr=config.filter)
            first_label = "Cells (face-on)"
            second_label = "Cells (midplane)"

        # Faceon
        elif config.projection == faceon_name:

            first = self.get_heating_map(cells_name, fltr=config.filter)
            second = self.get_heating_map(faceon_name, fltr=config.filter)
            first_label = "Cells (face-on)"
            second_label = "Projected (face-on)"

        # Edgeon
        elif config.projection == edgeon_name:

            first = self.get_heating_map(cells_edgeon_name, fltr=config.filter)
            second = self.get_heating_map(edgeon_name, fltr=config.filter)
            first_label = "Cells (edge-on)"
            second_label = "Projected (edge-on)"

        # Invalid
        else: raise ValueError("Invalid projection: '" + config.projection + "'")

        # Get images
        #observations = self.get_observed_images(filters)
        #models = self.get_simulated_images(filters)
        #residuals = self.get_residual_images(filters)

        # Get center and radius
        #center = self.galaxy_center
        #radius = self.truncation_radius * zoom
        #xy_ratio = (self.truncation_box_axial_ratio * scale_xy_ratio) ** scale_xy_exponent
        center = radius = None

        # Plot
        plot_one_residual_aplpy(first, second, center=center, radius=radius, path=config.path, first_label=first_label, second_label=second_label)

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_heating_distribution_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def plot_heating_distribution_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_heating_distribution_definition, **kwargs)

    # -----------------------------------------------------------------

    @property
    def absorption_or_emission(self):
        return [absorption_name, emission_name]

    # -----------------------------------------------------------------

    @property
    def default_heating_curve_projection(self):
        return cells_name

    # -----------------------------------------------------------------

    @property
    def heating_curve_projections(self):
        return [cells_name, earth_name, faceon_name, edgeon_name, differences_name]

    # -----------------------------------------------------------------

    @lazyproperty
    def plot_heating_curve_definition(self):

        """
        This function ...
        :return:
        """

        # Create definition
        definition = ConfigurationDefinition(write_config=False)

        # Absorption or emission
        definition.add_required("abs_or_em", "string", "absorption or emission", choices=self.absorption_or_emission)

        # Projection
        definition.add_positional_optional("projection", "string", "projection for the curve", self.default_heating_curve_projection, self.heating_curve_projections)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_absorption_min_wavelength(self):
        return q("0.1 micron")

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_absorption_max_wavelength(self):
        return q("2 micron")

    # -----------------------------------------------------------------

    @property
    def heating_absorption_wavelength_limits(self):
        return self.heating_absorption_min_wavelength, self.heating_absorption_max_wavelength

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_emission_min_wavelength(self):
        return q("5 micron")

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_emission_max_wavelength(self):
        return q("1000 micron")

    # -----------------------------------------------------------------

    @property
    def heating_emission_wavelength_limits(self):
        return self.heating_emission_min_wavelength, self.heating_emission_max_wavelength

    # -----------------------------------------------------------------

    def get_spectral_absorption_fraction_curve_path(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        if projection == cells_name: return fs.join(self.spectral_heating_curves_path, "absorption_cells.dat")
        elif projection == earth_name: return fs.join(self.spectral_heating_curves_path, "earth_absorption_seds.dat") # not from SEDs is wrong: from summing datacubes of heating fractions
        elif projection == faceon_name: return fs.join(self.spectral_heating_curves_path, "faceon_absorption_seds.dat") # not from SEDs is wrong: from summing datacubes of heating fractions
        elif projection == edgeon_name: return fs.join(self.spectral_heating_curves_path, "edgeon_absorption_seds.dat") # not from SEDs is wrong: from summing datacubes of heating fractions
        else: raise ValueError("Invalid projection: '" + projection + "'")

    # -----------------------------------------------------------------

    def get_spectral_absorption_fraction_curve(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        # Get the path
        path = self.get_spectral_absorption_fraction_curve_path(projection)

        # Open the curve
        curve = WavelengthCurve.from_file(path)

        # Return
        return curve

    # -----------------------------------------------------------------

    def get_spectral_emission_fraction_curve_path(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        if projection == cells_name: return fs.join(self.spectral_heating_curves_path, "emission_cells.dat")
        elif projection == earth_name: return fs.join(self.spectral_heating_curves_path, "earth_emission_seds.dat") # not from SEDs is wrong: from summing datacubes of heating fractions
        elif projection == faceon_name: return fs.join(self.spectral_heating_curves_path, "faceon_emission_seds.dat") # not from SEDs is wrong: from summing datacubes of heating fractions
        elif projection == edgeon_name: return fs.join(self.spectral_heating_curves_path, "edgeon_emission_seds.dat") # not from SEDs is wrong: from summing datacubes of heating fractions
        else: raise ValueError("Invalid projection: '" + projection + "'")

    # -----------------------------------------------------------------

    def get_spectral_emission_fraction_curve(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        # Get the path
        path = self.get_spectral_emission_fraction_curve_path(projection)

        # Opent the curve
        curve = WavelengthCurve.from_file(path)

        # Return
        return curve

    # -----------------------------------------------------------------

    @property
    def heating_fraction_name(self):
        return "Heating fraction"

    # -----------------------------------------------------------------

    def plot_heating_curve_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.plot_heating_curve_definition, **kwargs)

        # Absorption
        if config.abs_or_em == absorption_name: self.plot_spectral_absorption_fraction_curves(config.projection)

        # Emission
        elif config.abs_or_em == emission_name: self.plot_spectral_emission_fraction_curves(config.projection)

        # Invalid
        else: raise ValueError("Invalid value for 'abs_or_em'")

    # -----------------------------------------------------------------

    def plot_spectral_absorption_fraction_curves(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        # Differences
        if projection == differences_name:

            # Get cells, earth, faceon, and edgeon
            cells = self.get_spectral_absorption_fraction_curve(cells_name)
            earth = self.get_spectral_absorption_fraction_curve(earth_name)
            faceon = self.get_spectral_absorption_fraction_curve(faceon_name)
            edgeon = self.get_spectral_absorption_fraction_curve(edgeon_name)
            curves = {"cells": cells, "earth": earth, "faceon": faceon, "edgeon": edgeon}

            # Plot
            plot_curves(curves, xlimits=self.heating_absorption_wavelength_limits, ylimits=self.heating_fraction_interval, xlog=True, y_label=self.heating_fraction_name)

        # Single curve
        else:

            # Get single curve
            curve = self.get_spectral_absorption_fraction_curve(projection)

            # Plot
            plot_curve(curve, xlimits=self.heating_absorption_wavelength_limits, ylimits=self.heating_fraction_interval, xlog=True, y_label=self.heating_fraction_name)

    # -----------------------------------------------------------------

    def plot_spectral_emission_fraction_curves(self, projection):

        """
        This function ...
        :param projection:
        :return:
        """

        # Differences
        if projection == differences_name:

            # Get cells, earth, faceon, and edgeon
            cells = self.get_spectral_emission_fraction_curve(cells_name)
            earth = self.get_spectral_emission_fraction_curve(earth_name)
            faceon = self.get_spectral_emission_fraction_curve(faceon_name)
            edgeon = self.get_spectral_emission_fraction_curve(edgeon_name)
            curves = {"cells": cells, "earth": earth, "faceon": faceon, "edgeon": edgeon}

            # Plot
            plot_curves(curves, xlimits=self.heating_emission_wavelength_limits, ylimits=self.heating_fraction_interval, xlog=True, y_label=self.heating_fraction_name)

        # Single curve
        else:

            # Get curve
            curve = self.get_spectral_emission_fraction_curve(projection)

            # Plot
            plot_curve(curve, xlimits=self.heating_emission_wavelength_limits, ylimits=self.heating_fraction_interval, xlog=True, y_label=self.heating_fraction_name)

    # -----------------------------------------------------------------

    @lazyproperty
    def evaluate_definition(self):

        """
        This function ...
        :return:
        """

        definition = ConfigurationDefinition(write_config=False)
        definition.import_settings(evaluate_analysis_definition)
        return definition

    # -----------------------------------------------------------------

    def evaluate_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.evaluate_definition, **kwargs)

        # Evaluate
        self.evaluate(**config)

    # -----------------------------------------------------------------

    def evaluate(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Create evaluator
        evaluator = AnalysisModelEvaluator(**kwargs)

        # Set modeling path
        evaluator.config.path = self.config.path

        # Set analysis run name
        evaluator.config.run = self.config.run

        # Run
        evaluator.run()

    # -----------------------------------------------------------------

    def show_map(self, frame, contours=False, ncontours=5):

        """
        This function ...
        :param frame:
        :param contours:
        :param ncontours:
        :return:
        """

        # With contours
        if contours: plot_frame_contours(frame, nlevels=ncontours)

        # Just frame
        else: plot_frame(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_total_map_definition(self):

        """
        Thisn function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=total_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_total_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_total_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_total_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, definition=self.show_total_map_definition, **kwargs)

        # Show
        self.show_total_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------
    # TOTAL SIMULATION
    # -----------------------------------------------------------------

    @property
    def total_simulations(self):
        return self.model.total_simulations

    # -----------------------------------------------------------------

    @property
    def total_simulation(self):
        return self.model.total_simulation

    # -----------------------------------------------------------------

    @property
    def total_output(self):
        return self.model.total_simulation_output

    # -----------------------------------------------------------------

    @property
    def total_data(self):
        return self.model.total_simulation_data

    # -----------------------------------------------------------------
    # BULGE SIMULATION
    # -----------------------------------------------------------------

    @property
    def bulge_simulations(self):
        return self.model.bulge_simulations

    # -----------------------------------------------------------------

    @property
    def bulge_simulation(self):
        return self.model.bulge_simulation

    # -----------------------------------------------------------------

    @property
    def bulge_output(self):
        return self.model.bulge_simulation_output

    # -----------------------------------------------------------------

    @property
    def bulge_data(self):
        return self.model.bulge_simulation_data

    # -----------------------------------------------------------------
    # DISK SIMULATION
    # -----------------------------------------------------------------

    @property
    def disk_simulations(self):
        return self.model.disk_simulations

    # -----------------------------------------------------------------

    @property
    def disk_simulation(self):
        return self.model.disk_simulation

    # -----------------------------------------------------------------

    @property
    def disk_output(self):
        return self.model.disk_simulation_output

    # -----------------------------------------------------------------

    @property
    def disk_data(self):
        return self.model.disk_simulation_data

    # -----------------------------------------------------------------
    # OLD SIMULATION
    # -----------------------------------------------------------------

    @property
    def old_simulations(self):
        return self.model.old_simulations

    # -----------------------------------------------------------------

    @property
    def old_simulation(self):
        return self.model.old_simulation

    # -----------------------------------------------------------------

    @property
    def old_output(self):
        return self.model.old_simulation_output

    # -----------------------------------------------------------------

    @property
    def old_data(self):
        return self.model.old_simulation_data

    # -----------------------------------------------------------------
    # YOUNG SIMULATION
    # -----------------------------------------------------------------

    @property
    def young_simulations(self):
        return self.model.young_simulations

    # -----------------------------------------------------------------

    @property
    def young_simulation(self):
        return self.model.young_simulation

    # -----------------------------------------------------------------

    @property
    def young_output(self):
        return self.model.young_simulation_output

    # -----------------------------------------------------------------

    @property
    def young_data(self):
        return self.model.young_simulation_data

    # -----------------------------------------------------------------
    # SFR SIMULATION
    # -----------------------------------------------------------------

    @property
    def sfr_simulations(self):
        return self.model.sfr_simulations

    # -----------------------------------------------------------------

    @property
    def sfr_simulation(self):
        return self.model.sfr_simulation

    # -----------------------------------------------------------------

    @property
    def sfr_output(self):
        return self.model.sfr_simulation_output

    # -----------------------------------------------------------------

    @property
    def sfr_data(self):
        return self.model.sfr_simulation_data

    # -----------------------------------------------------------------
    # UNEVOLVED SIMULATION
    # -----------------------------------------------------------------

    @property
    def unevolved_simulations(self):
        return self.model.unevolved_simulations

    # -----------------------------------------------------------------

    @property
    def unevolved_simulation(self):
        return self.model.unevolved_simulation

    # -----------------------------------------------------------------

    @property
    def unevolved_output(self):
        return self.model.unevolved_simulation_output

    # -----------------------------------------------------------------

    @property
    def unevolved_data(self):
        return self.model.unevolved_simulation_data

    # -----------------------------------------------------------------
    # -----------------------------------------------------------------

    def show_total_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the total model from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_total_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_bulge_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=bulge_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_bulge_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_bulge_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_bulge_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_bulge_map_definition, **kwargs)

        # Show
        self.show_bulge_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_bulge_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the old stellar bulge component from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_bulge_map(which, orientation=orientation)

        # Show the map
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_disk_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=disk_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_disk_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_disk_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_disk_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_disk_map_definition, **kwargs)

        # Show
        self.show_disk_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_disk_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the old stellar disk component from the " + orientation + " orientation ...")

        # Get the disk map
        frame = self.get_disk_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_old_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=old_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_old_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_old_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_old_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_old_map_definition, **kwargs)

        # Show
        self.show_old_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_old_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the old stellar component from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_old_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_young_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=young_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_young_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_young_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_young_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_young_map_definition, **kwargs)

        # Show
        self.show_young_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_young_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the young stellar component from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_young_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_sfr_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=sfr_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_sfr_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_sfr_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_sfr_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_sfr_map_definition, **kwargs)

        # Show
        self.show_sfr_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_sfr_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the SFR stellar component from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_sfr_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_unevolved_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=unevolved_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_unevolved_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_unevolved_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_unevolved_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_unevolved_map_definition, **kwargs)

        # Show
        self.show_unevolved_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_unevolved_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " map of the unevolved stellar component from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_unevolved_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def show_dust_map_definition(self):

        """
        This function ...
        :return:
        """

        # Create
        definition = ConfigurationDefinition(write_config=False)

        # Options
        definition.add_required("which", "string", "which map to plot", choices=dust_map_names)
        definition.add_positional_optional("orientation", "string", "orientation of the map", default=earth_name, choices=orientations)
        definition.add_flag("contours", "show contours", False)
        definition.add_optional("ncontours", "positive_integer", "number of contour lines", 5)

        # Return
        return definition

    # -----------------------------------------------------------------

    @lazyproperty
    def show_dust_map_kwargs(self):

        """
        This function ...
        :return:
        """

        kwargs = dict()
        kwargs["required_to_optional"] = False
        return kwargs

    # -----------------------------------------------------------------

    def show_dust_map_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Set kwargs
        kwargs.update(self.show_dust_map_kwargs)

        # Get the configuration
        config = self.get_config_from_command(command, self.show_dust_map_definition, **self.show_dust_map_kwargs)

        # Show
        self.show_dust_map(config.which, orientation=config.orientation)

    # -----------------------------------------------------------------

    def show_dust_map(self, which, orientation=earth_name):

        """
        This function ...
        :param which:
        :param orientation:
        :return:
        """

        # Debugging
        log.debug("Showing the " + which + " dust map from the " + orientation + " orientation ...")

        # Get the map
        frame = self.get_dust_map(which, orientation=orientation)

        # Show
        self.show_map(frame)

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_properties_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_properties_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_properties_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_properties_definition, **kwargs)

        # Analyse
        self.analyse_properties(config=config)

    # -----------------------------------------------------------------

    def analyse_properties(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the model properties ...")

        # Create the analyser
        analyser = PropertiesAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_absorption_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_absorption_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_absorption_command(self, command, **kwargs):
        
        """
        This function ...
        :param command: 
        :param kwargs: 
        :return: 
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_absorption_definition, **kwargs)

        # Analyse
        self.analyse_absorption(config=config)
        
    # -----------------------------------------------------------------

    def analyse_absorption(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Create the analyser
        analyser = AbsorptionAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_cell_heating_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        #print(analyse_cell_heating_definition.property_names)
        #print(analyse_cell_heating_definition.section_names)

        # Add settings
        definition.import_settings(analyse_cell_heating_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_cell_heating_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_cell_heating_definition, **kwargs)

        # Analyse
        self.analyse_cell_heating(config=config)

    # -----------------------------------------------------------------

    def analyse_cell_heating(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the dust cell heating ...")

        # Create the analyser
        analyser = CellDustHeatingAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_projected_heating_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        #print(analyse_projected_heating_definition.property_names)
        #print(analyse_projected_heating_definition.section_names)

        # Add settings
        definition.import_settings(analyse_projected_heating_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_projected_heating_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_projected_heating_definition, **kwargs)

        # Analyse
        self.analyse_projected_heating(config=config)

    # -----------------------------------------------------------------

    def analyse_projected_heating(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the projected heating ...")

        # Create the analyser
        analyser = ProjectedDustHeatingAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_spectral_heating_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Change settings
        definition.import_settings(analyse_spectral_heating_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_spectral_heating_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_spectral_heating_definition, **kwargs)

        # Analyse
        self.analyse_spectral_heating(config=config)

    # -----------------------------------------------------------------

    def analyse_spectral_heating(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the spectral heating ...")

        # Create the analyser
        analyser = SpectralDustHeatingAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_cell_energy_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_cell_energy_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_cell_energy_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_cell_energy_definition, **kwargs)

        # Analyse
        self.analyse_cell_energy(config=config)

    # -----------------------------------------------------------------

    def analyse_cell_energy(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the cell energy balance ...")

        # Create the analyser
        analyser = CellEnergyAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_projected_energy_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_projected_energy_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_projected_energy_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_projected_energy_definition, **kwargs)

        # Analyse
        self.analyse_projected_energy(config=config)

    # -----------------------------------------------------------------

    def analyse_projected_energy(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the projected energy balance ...")

        # Create the analyser
        analyser = ProjectedEnergyAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_sfr_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_sfr_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_sfr_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_sfr_definition, **kwargs)

        # Analyse
        self.analyse_sfr(config=config)

    # -----------------------------------------------------------------

    def analyse_sfr(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the star formation rates ...")

        # Create the analyser
        analyser = SFRAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_correlations_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_correlations_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_correlations_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_correlations_definition, **kwargs)

        # Analyse
        self.analyse_correlations(config=config)

    # -----------------------------------------------------------------

    def analyse_correlations(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the correlations ...")

        # Create the analyser
        analyser = CorrelationsAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_fluxes_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_fluxes_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_fluxes_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_fluxes_definition, **kwargs)
        
        # Analyse
        self.analyse_fluxes(config=config)

    # -----------------------------------------------------------------
    
    def analyse_fluxes(self, config=None):
        
        """
        This function ...
        :param config: 
        :return: 
        """

        # Create the analyser
        analyser = FluxesAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_images_definition(self):

        """
        This fnction ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_images_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_images_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_images_definition, **kwargs)

        # Analyse
        self.analyse_images(config=config)

    # -----------------------------------------------------------------

    def analyse_images(self, config=None):

        """
        This function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the mock images ...")

        # Create the analyser
        analyser = ImagesAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def analyse_residuals_definition(self):

        """
        This function ...
        :return:
        """

        # Create the definition
        definition = ConfigurationDefinition(write_config=False)

        # Add settings
        definition.import_settings(analyse_residuals_definition)
        definition.remove_setting("run")

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def analyse_residuals_command(self, command, **kwargs):

        """
        This function ...
        :param command:
        :param kwargs:
        :return:
        """

        # Get config
        config = self.get_config_from_command(command, self.analyse_residuals_definition, **kwargs)

        # Analyse
        self.analyse_residuals(config=config)

    # -----------------------------------------------------------------

    def analyse_residuals(self, config=None):

        """
        Thi function ...
        :param config:
        :return:
        """

        # Inform the user
        log.info("Analysing the image residuals ...")

        # Create the analyser
        analyser = ResidualAnalyser(config=config)

        # Set the modeling path
        analyser.config.path = self.config.path

        # Set the analysis run
        analyser.config.run = self.config.run

        # Run
        analyser.run()

    # -----------------------------------------------------------------

    def examine_model(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Initialize
        examination = ModelExamination()

        # Run
        examination.run(model=self.model)

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing ...")

    # -----------------------------------------------------------------

    # FROM ANALYSISPLOTTER:

    # def load_wavelength_grid(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     # Inform the user
    #     log.info("Loading the wavelength grid ...")
    #
    #     # Determine the path to the wavelength grid file
    #     path = fs.join(self.analysis_path, "in", "wavelengths.txt")
    #
    #     # Load the wavelength grid
    #     if fs.is_file(path): self.wavelength_grid = WavelengthGrid.from_skirt_input(path)
    #
    # # -----------------------------------------------------------------
    #
    # def load_transmission_curves(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     # Inform the user
    #     log.info("Loading the transmission curves ...")
    #
    #     # Load the observed SED
    #     sed = ObservedSED.from_file(self.observed_sed_path)
    #
    #     # Loop over all filters for the points in the SED
    #     for fltr in sed.filters():
    #
    #         # Create the transmission curve
    #         transmission = TransmissionCurve.from_filter(fltr)
    #
    #         # Normalize the transmission curve
    #         transmission.normalize(value=1.0, method="max")
    #
    #         # Add the transmission curve to the dictionary
    #         self.transmission_curves[str(fltr)] = transmission
    #
    # # -----------------------------------------------------------------
    #
    # def plot_wavelengths(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     # Inform the user
    #     log.info("Plotting the wavelength grid ...")
    #
    #     # Create the transmission plotter
    #     plotter = TransmissionPlotter()
    #
    #     plotter.title = "Wavelengths used for analysis"
    #     plotter.transparent = True
    #
    #     # Add the transmission curves
    #     for label in self.transmission_curves: plotter.add_transmission_curve(self.transmission_curves[label], label)
    #
    #     # Add the wavelength points
    #     for wavelength in self.wavelength_grid.wavelengths(): plotter.add_wavelength(wavelength)
    #
    #     # Determine the path to the plot file
    #     path = fs.join(self.plot_analysis_path, "wavelengths.pdf")
    #
    #     # Run the plotter
    #     plotter.run(path, min_wavelength=self.wavelength_grid.min_wavelength, max_wavelength=self.wavelength_grid.max_wavelength, min_transmission=0.0, max_transmission=1.05)

    # -----------------------------------------------------------------

    @property
    def history_filename(self):

        """
        This function ...
        :return:
        """

        return "analysis"

# -----------------------------------------------------------------
