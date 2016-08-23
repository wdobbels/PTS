#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.analysis.component Contains the AnalysisComponent class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ..core.component import ModelingComponent
from ...core.tools import filesystem as fs
from ...core.launch.timing import TimingTable
from ...core.launch.memory import MemoryTable
from .info import AnalysisRunInfo
from ...core.simulation.skifile import SkiFile

# -----------------------------------------------------------------

class AnalysisComponent(ModelingComponent):
    
    """
    This class...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(AnalysisComponent, self).__init__(config)

        # -- Attributes --

        # The path to the timing table
        self.timing_table_path = None

        # The path to the memory table
        self.memory_table_path = None

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(AnalysisComponent, self).setup()

        # Timing table --

        # Set the path to the timing table
        self.timing_table_path = fs.join(self.analysis_path, "timing.dat")

        # Initialize the timing table if necessary
        if not fs.is_file(self.timing_table_path):

            # Create the table and save it
            timing_table = TimingTable()
            timing_table.saveto(self.timing_table_path)

        # Memory table --

        # Set the path to the memory table
        self.memory_table_path = fs.join(self.analysis_path, "memory.dat")

        # Initialize the memory table if necessary
        if not fs.is_file(self.memory_table_path):

            # Create the table and save it
            memory_table = MemoryTable()
            memory_table.saveto(self.memory_table_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def timing_table(self):

        """
        This function ...
        :return:
        """

        return TimingTable.from_file(self.timing_table_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def memory_table(self):

        """
        This function ...
        :return:
        """

        return MemoryTable.from_file(self.memory_table_path)

    # -----------------------------------------------------------------

    @property
    def analysis_run_names(self):

        """
        This function ...
        :return:
        """

        return fs.directories_in_path(self.analysis_path, returns="name")

    # -----------------------------------------------------------------

    def get_run_path(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        path = fs.join(self.analysis_path, run_name)
        return path

    # -----------------------------------------------------------------

    def get_run_info(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        path = fs.join(self.get_run_path(run_name), "info.dat")
        return AnalysisRunInfo.from_file(path)

    # -----------------------------------------------------------------

    def get_run(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        info_path = fs.join(self.get_run_path(run_name), "info.dat")
        return AnalysisRun.from_info(info_path)

# -----------------------------------------------------------------

def get_analysis_run_names(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    analysis_path = fs.join(modeling_path, "analysis")
    return fs.directories_in_path(analysis_path, returns="name")

# -----------------------------------------------------------------

def get_last_run_name(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return sorted(get_analysis_run_names(modeling_path))[-1]

# -----------------------------------------------------------------

class AnalysisRun(object):

    """
    This class ...
    """

    def __init__(self):

        """
        The constructor ...
        """

        self.galaxy_name = None
        self.info = None

    # -----------------------------------------------------------------

    @classmethod
    def from_info(cls, info_path):

        """
        This function ...
        :param info_path:
        :return:
        """

        # Create the instance
        run = cls()

        # Set the analysis run info
        run.info = AnalysisRunInfo.from_file(info_path)

        # Set galaxy name
        modeling_path = fs.directory_of(fs.directory_of(run.info.path))
        run.galaxy_name = fs.name(modeling_path)

        # Return the analysis run object
        return run

    # -----------------------------------------------------------------

    @property
    def name(self):

        """
        This function ...
        :return:
        """

        return self.info.name

    # -----------------------------------------------------------------

    @property
    def path(self):

        """
        This function ...
        :return:
        """

        return self.info.path

    # -----------------------------------------------------------------

    @property
    def out_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "out")

    # -----------------------------------------------------------------

    @property
    def extr_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "extr")

    # -----------------------------------------------------------------

    @property
    def plot_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "plot")

    # -----------------------------------------------------------------

    @property
    def misc_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "misc")

    # -----------------------------------------------------------------

    @property
    def attenuation_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "attenuation")

    # -----------------------------------------------------------------

    @property
    def colours_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "colours")

    # -----------------------------------------------------------------

    @property
    def residuals_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "residuals")

    # -----------------------------------------------------------------

    @property
    def heating_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "heating")

    # -----------------------------------------------------------------

    @property
    def heating_wavelength_grid_path(self):

        """
        This fucntion ...
        :return:
        """

        return fs.join(self.heating_path, "wavelength_grid.dat")

    # -----------------------------------------------------------------

    @property
    def heating_instruments_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.heating_path, "instruments")

    # -----------------------------------------------------------------

    def heating_simulation_path_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        return fs.join(self.heating_path, contribution)

    # -----------------------------------------------------------------

    def heating_ski_path_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        return fs.join(self.heating_simulation_path_for_contribution(contribution), self.galaxy_name + ".ski")

    # -----------------------------------------------------------------

    def heating_output_path_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        return fs.join(self.heating_simulation_path_for_contribution(contribution), "out")

    # -----------------------------------------------------------------

    @property
    def analysis_run_name(self):

        """
        This function ...
        :return:
        """

        return self.info.name

    # -----------------------------------------------------------------

    @property
    def analysis_run_path(self):

        """
        This function ...
        :return:
        """

        return self.info.path

    # -----------------------------------------------------------------

    @property
    def ski_file_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.analysis_run_path, )

    # -----------------------------------------------------------------

    @property
    def ski_file(self):

        """
        This function ...
        :return:
        """

        return SkiFile(self.ski_file_path)

    # -----------------------------------------------------------------

    @property
    def dust_grid_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "dust_grid.dg")

    # -----------------------------------------------------------------

    @property
    def wavelength_grid_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "wavelength_grid.dat")

    # -----------------------------------------------------------------

    @property
    def instruments_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "instruments")

# -----------------------------------------------------------------
