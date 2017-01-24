#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.wavelengthgrids Contains the WavelengthGridGenerator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import astronomical modules
from astropy.table import Table

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ...core.simulation.wavelengthgrid import WavelengthGrid
from ..core.emissionlines import EmissionLines

# -----------------------------------------------------------------

# The names of the subgrids
subgrids = ["UV", "optical", "PAH", "dust", "extension"]

# Define the limits of the subgrids
limits = dict()
limits["UV"] = (0.02, 0.085)
limits["optical"] = (0.085, 3.)
limits["PAH"] = (3., 27.)
limits["dust"] = (27., 1000.)
limits["extension"] = (1000., 2000)

# Define the relative fineness (the number of points) of the subgrids
relpoints = dict()
relpoints["UV"] = 25./325.    # 25
relpoints["optical"] = 100./325.     # 100
relpoints["PAH"] = 125./325.  # 125
relpoints["dust"] = 50./325.  # 50
relpoints["extension"] = 25./325.  # 25

# -----------------------------------------------------------------

class WavelengthGridGenerator(object):
    
    """
    This class...
    """

    def __init__(self):

        """
        The constructor ...
        :return:
        """

        # Call the constructor of the base class
        super(WavelengthGridGenerator, self).__init__()

        # -- Attributes --

        # Settings
        self.npoints_range = None
        self.ngrids = None
        self.fixed = None
        self.add_emission_lines = False
        self.min_wavelength = None
        self.max_wavelength = None

        # The wavelength grids
        self.grids = []

        # The wavelength grid property table
        self.table = None

        # The emission line object
        self.emission_lines = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Generate the grids
        self.generate()

        # 3. Show
        self.show()

        # 4. Write
        self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Set options
        self.npoints_range = kwargs.pop("npoints_range")
        self.ngrids = kwargs.pop("ngrids")
        self.fixed = kwargs.pop("fixed", None)
        self.add_emission_lines = kwargs.pop("add_emission_lines", False)
        self.min_wavelength = kwargs.pop("min_wavelength", None)
        self.max_wavelength = kwargs.pop("max_wavelength", None)

        # Create the emission lines instance
        self.emission_lines = EmissionLines()

        # Initialize the table
        names = ["UV points", "Optical points", "PAH points", "Dust points", "Extension points", "Emission lines", "Fixed points", "Total points"]
        dtypes = [int, int, int, int, int, int, int, int]
        self.table = Table(names=names, dtype=dtypes)

    # -----------------------------------------------------------------

    def generate(self):

        """
        This function ...
        :param:
        """

        # Inform the user
        log.info("Generating the wavelength grids ...")

        # Loop over the different number of points
        for npoints in self.npoints_range.linear(self.ngrids):

            # Create the grid and add it to the list
            self.create_grid(npoints)

    # -----------------------------------------------------------------

    def create_grid(self, npoints):

        """
        This function ...
        :param npoints:
        :return:
        """

        # Inform the user
        with_without = " with " if self.add_emission_lines else " without "
        log.info("Creating a wavelength grid with " + str(npoints) + " points" + with_without + "emission lines ...")

        # Create the grid
        if self.add_emission_lines: grid, subgrid_npoints, emission_npoints, fixed_npoints = create_one_subgrid_wavelength_grid(npoints, self.emission_lines, self.fixed, min_wavelength=self.min_wavelength, max_wavelength=self.max_wavelength)
        else: grid, subgrid_npoints, emission_npoints, fixed_npoints = create_one_subgrid_wavelength_grid(npoints, fixed=self.fixed, min_wavelength=self.min_wavelength, max_wavelength=self.max_wavelength)

        # Add the grid
        self.grids.append(grid)

        # Add an entry to the table
        uv_npoints = subgrid_npoints["UV"]
        optical_npoints = subgrid_npoints["optical"]
        pah_npoints = subgrid_npoints["PAH"]
        dust_npoints = subgrid_npoints["dust"]
        extension_npoints = subgrid_npoints["extension"]
        self.table.add_row([uv_npoints, optical_npoints, pah_npoints, dust_npoints, extension_npoints, emission_npoints, fixed_npoints, len(grid)])

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        pass

# -----------------------------------------------------------------

def create_one_subgrid_wavelength_grid(npoints, emission_lines=None, fixed=None, min_wavelength=None, max_wavelength=None):

    """
    This function ...
    :param npoints:
    :param emission_lines:
    :param fixed:
    :param min_wavelength:
    :param max_wavelength:
    :return:
    """

    # Debugging
    log.debug("Creating wavelength grid with " + str(npoints) + " points ...")

    # A list of the wavelength points
    wavelengths = []

    # Keep track of the number of points per subgrid
    subgrid_npoints = dict()

    # Loop over the subgrids
    for subgrid in subgrids:

        # Debugging
        log.debug("Adding the " + subgrid + " subgrid ...")

        # Determine minimum, maximum
        min_lambda = limits[subgrid][0]
        max_lambda = limits[subgrid][1]

        # Skip subgrids out of range
        if min_wavelength is not None and max_lambda < min_wavelength: continue
        if max_wavelength is not None and min_lambda > max_wavelength: continue

        # Determine the normal number of wavelength points for this subgrid
        points = int(round(relpoints[subgrid] * npoints))

        # Correct the number of wavelengths based on the given min and max wavelength
        #if min_wavelength is not None: min_lambda = max(min_lambda, min_wavelength)
        #if max_wavelength is not None: max_lambda = min(max_lambda, max_wavelength)

        # Generate and add the wavelength points
        wavelengths_subgrid_original = make_grid(min_lambda, max_lambda, points)

        # Filter based on given boundaries
        wavelengths_subgrid = []
        for wav in wavelengths_subgrid_original:
            if min_wavelength is not None and wav < min_wavelength: continue
            if max_wavelength is not None and wav > max_wavelength: continue
            wavelengths_subgrid.append(wav)

        # Set the number of points for this subgrid
        subgrid_npoints[subgrid] = len(wavelengths_subgrid)

        # Add the wavelength points
        wavelengths += wavelengths_subgrid

    # Add the emission lines
    emission_npoints = 0
    if emission_lines is not None:

        # Add the mission lines
        wavelengths = add_emission_lines(wavelengths, emission_lines, min_wavelength, max_wavelength)
        emission_npoints = len(emission_lines)

    # Add fixed wavelength points
    fixed_npoints = 0
    if fixed is not None:
        fixed_npoints = len(fixed)
        for wavelength in fixed:
            if min_wavelength is not None and wavelength < min_wavelength: continue
            if max_wavelength is not None and wavelength > max_wavelength: continue
            wavelengths.append(wavelength)

    # Sort the wavelength points
    wavelengths = sorted(wavelengths)

    # Create the wavelength grid
    grid = WavelengthGrid.from_wavelengths(wavelengths)

    # Return the grid and some information about the subgrids
    return grid, subgrid_npoints, emission_npoints, fixed_npoints

# -----------------------------------------------------------------

def create_one_logarithmic_wavelength_grid(wrange, npoints, emission_lines=None, fixed=None):

    """
    This function ...
    :param wrange:
    :param npoints:
    :param emission_lines:
    :param fixed:
    :return:
    """

    # Verify the grid parameters
    if npoints < 2: raise ValueError("the number of points in the grid should be at least 2")
    if wrange.min <= 0: raise ValueError("the shortest wavelength should be positive")

    # Calculate log of boundaries
    logmin = np.log10(float(wrange.min))
    logmax = np.log10(float(wrange.max))

    # Calculate the grid points
    wavelengths = np.logspace(logmin, logmax, num=npoints, endpoint=True, base=10)

    # Add the emission lines
    emission_npoints = 0
    if emission_lines is not None:

        # Add the mission lines
        wavelengths = add_emission_lines(wavelengths, emission_lines)
        emission_npoints = len(emission_lines)

    # Add fixed wavelength points
    fixed_npoints = 0
    if fixed is not None:
        fixed_npoints = len(fixed)
        for wavelength in fixed: wavelengths.append(wavelength)

    # Sort the wavelength points
    wavelengths = sorted(wavelengths)

    # Create the wavelength grid
    grid = WavelengthGrid.from_wavelengths(wavelengths)

    # Return the grid
    return grid, emission_npoints, fixed_npoints

# -----------------------------------------------------------------

def create_one_nested_log_wavelength_grid(wrange, npoints, wrange_zoom, npoints_zoom, emission_lines=None, fixed=None):

    """
    This function ...
    :param wrange:
    :param npoints:
    :param wrange_zoom:
    :param npoints_zoom:
    :param emission_lines:
    :param fixed:
    :return:
    """

    # Verify the grid parameters
    if npoints < 2: raise ValueError("the number of points in the low-resolution grid should be at least 2")
    if npoints_zoom < 2: raise ValueError("the number of points in the high-resolution subgrid should be at least 2")
    if wrange.min <= 0: raise ValueError("the shortest wavelength should be positive")
    if (wrange_zoom.min <= wrange.min
        or wrange_zoom.max <= wrange_zoom.min
        or wrange.max <= wrange_zoom.max):
        raise ValueError("the high-resolution subgrid should be properly nested in the low-resolution grid")

    logmin = np.log10(float(wrange.min))
    logmax = np.log10(float(wrange.max))
    logmin_zoom = np.log10(float(wrange_zoom.min))
    logmax_zoom = np.log10(float(wrange_zoom.max))

    # Build the high- and low-resolution grids independently
    base_grid = np.logspace(logmin, logmax, num=npoints, endpoint=True, base=10)
    zoom_grid = np.logspace(logmin_zoom, logmax_zoom, num=npoints_zoom, endpoint=True, base=10)

    # Merge the two grids
    wavelengths = []

    # Add the wavelengths of the low-resolution grid before the first wavelength of the high-resolution grid
    for wavelength in base_grid:
        if wavelength < wrange_zoom.min: wavelengths.append(wavelength)

    # Add the wavelengths of the high-resolution grid
    for wavelength in zoom_grid: wavelengths.append(wavelength)

    # Add the wavelengths of the low-resolution grid after the last wavelength of the high-resolution grid
    for wavelength in base_grid:
        if wavelength > wrange_zoom.max: wavelengths.append(wavelength)

    # Add the emission lines
    emission_npoints = 0
    if emission_lines is not None:

        # Add the mission lines
        wavelengths = add_emission_lines(wavelengths, emission_lines)
        emission_npoints = len(emission_lines)

    # Add fixed wavelength points
    fixed_npoints = 0
    if fixed is not None:
        fixed_npoints = len(fixed)
        for wavelength in fixed: wavelengths.append(wavelength)

    # Sort the wavelength points
    wavelengths = sorted(wavelengths)

    # Create the wavelength grid
    grid = WavelengthGrid.from_wavelengths(wavelengths)

    # Return the grid
    return grid, emission_npoints, fixed_npoints

# -----------------------------------------------------------------

def add_emission_lines(wavelengths, emission_lines, min_wavelength=None, max_wavelength=None):

    """
    This function ...
    :param wavelengths:
    :param emission_lines:
    :param min_wavelength:
    :param max_wavelength:
    :return:
    """

    # Add emission line grid points
    logdelta = 0.001
    for line in emission_lines:

        center = line.center
        left = line.left
        right = line.right

        if min_wavelength is not None and center < min_wavelength: continue
        if max_wavelength is not None and center > max_wavelength: continue

        # logcenter = np.log10(center)
        logleft = np.log10(left if left > 0 else center) - logdelta
        logright = np.log10(right if right > 0 else center) + logdelta
        newgrid = []
        for w in wavelengths:
            logw = np.log10(w)
            if logw < logleft or logw > logright:
                newgrid.append(w)
        newgrid.append(center)
        if left > 0:
            newgrid.append(left)
        if right > 0:
            newgrid.append(right)
        wavelengths = newgrid

    # Return the new wavelength list
    return wavelengths

# -----------------------------------------------------------------

def make_grid(wmin, wmax, N):

    """
    This function returns a wavelength grid (in micron) with a given resolution (nr of points per decade)
    # in the specified range (in micron), aligned with the 10^n grid points.
    """

    result = []

    # generate wavelength points p on a logarithmic scale with lambda = 10**p micron
    #  -2 <==> 0.01
    #   4 <==> 10000
    for i in range(-2*N,4*N+1):
        p = float(i)/N
        w = 10.**p
        if wmin <= w < wmax: result.append(w)

    # Return the grid
    return result

# -----------------------------------------------------------------
