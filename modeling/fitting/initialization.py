#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.initialization Contains the InputInitializer

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import math
import copy
import bisect
import numpy as np

# Import astronomical modules
from astropy.units import Unit, dimensionless_angles
from astropy import constants

# Import the relevant PTS classes and modules
from .component import FittingComponent
from ...core.tools import inspection, tables
from ...core.tools import filesystem as fs
from ...core.simulation.skifile import SkiFile
from ...core.basics.filter import Filter
from ..basics.models import SersicModel, DeprojectionModel
from ...magic.basics.coordinatesystem import CoordinateSystem
from ..decomposition.decomposition import load_parameters
from ...magic.basics.skyregion import SkyRegion
from ..basics.instruments import SEDInstrument
from ..core.sun import Sun
from ..core.mappings import Mappings
from ...magic.tools import wavelengths
from ...core.tools.logging import log
from ...core.simulation.wavelengthgrid import WavelengthGrid
from ..basics.projection import GalaxyProjection
from ...core.simulation.execute import SkirtExec
from ...core.simulation.arguments import SkirtArguments

# -----------------------------------------------------------------

template_ski_path = fs.join(inspection.pts_dat_dir("modeling"), "ski", "template.ski")

# -----------------------------------------------------------------

class InputInitializer(FittingComponent):
    
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
        super(InputInitializer, self).__init__(config)

        # -- Attributes --

        # The ski file
        self.ski = None

        # The wavelength grid
        self.wavelength_grid = None

        # The structural parameters
        self.parameters = None

        # The projection system
        self.projection = None

        # The truncation ellipse
        self.ellipse = None

        # The geometric bulge model
        self.bulge = None

        # The deprojection model
        self.deprojection = None

        # The instrument
        self.instrument = None

        # The table of weights for each band
        self.weights = None

        # The fluxes table
        self.fluxes = None

        # Filters
        self.i1 = None
        self.fuv = None

        # Solar luminosity units
        self.sun_fuv = None
        self.sun_i1 = None

        # Coordinate system
        self.reference_wcs = None

        # The ski files for simulating the contributions of the various stellar components
        self.ski_contributions = dict()

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new InputInitializer instance
        initializer = cls(arguments.config)

        # Set the modeling path
        initializer.config.path = arguments.path

        # Set minimum and maximum wavelength of the total grid
        if arguments.lambda_minmax is not None:
            initializer.config.wavelengths.min = arguments.lambda_minmax[0]
            initializer.config.wavelengths.max = arguments.lambda_minmax[1]

        # Set minimum and maximum wavelength of the zoomed-in grid
        if arguments.lambda_minmax_zoom is not None:
            initializer.config.wavelengths.min_zoom = arguments.lambda_minmax_zoom[0]
            initializer.config.wavelengths.max_zoom = arguments.lambda_minmax_zoom[1]

        # Set the number of wavelength points
        if arguments.nlambda is not None:
            # Based on npoints = 1.1 * npoints_zoom
            initializer.config.wavelengths.npoints = 1.1 * arguments.nlambda / 2.1
            initializer.config.wavelengths.npoints_zoom = arguments.nlambda / 2.1

        # Set the number of photon packages per wavelength
        if arguments.packages is not None: initializer.config.packages = arguments.packages

        # Set selfabsorption
        initializer.config.selfabsorption = arguments.selfabsorption

        # Return the new instance
        return initializer

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Load the template ski file
        self.load_template()

        # 3. Load the structural parameters of the galaxy
        self.load_parameters()

        # 4. Load the projection system
        self.load_projection()

        # 5. Load the truncation ellipse
        self.load_truncation_ellipse()

        # 4. Load the fluxes
        self.load_fluxes()

        # 5. Create the wavelength grid
        self.create_wavelength_grid()

        # 6. Create the bulge model
        self.create_bulge_model()

        # 7. Create the deprojection model
        self.create_deprojection_model()

        # 8. Create the instrument
        self.create_instrument()

        # 9. Adjust the ski file
        self.adjust_ski()

        # 10. Adjust the ski files for simulating the contributions of the various stellar components
        self.adjust_ski_contributions()

        # 11. Calculate the weight factor to give to each band
        self.calculate_weights()

        # 12. Generate the dust grid data files
        self.generate_dust_grid()

        # 13. Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(InputInitializer, self).setup()

        # Create filters
        self.i1 = Filter.from_string("I1")
        self.fuv = Filter.from_string("FUV")

        # Solar properties
        sun = Sun()
        self.sun_fuv = sun.luminosity_for_filter_as_unit(self.fuv) # Get the luminosity of the Sun in the FUV band
        self.sun_i1 = sun.luminosity_for_filter_as_unit(self.i1)   # Get the luminosity of the Sun in the IRAC I1 band

        # Reference coordinate system
        reference_path = fs.join(self.truncation_path, self.reference_image + ".fits")
        self.reference_wcs = CoordinateSystem.from_file(reference_path)

    # -----------------------------------------------------------------

    def load_template(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the ski file template ...")

        # Open the template ski file
        self.ski = SkiFile(template_ski_path)

    # -----------------------------------------------------------------

    def load_parameters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the decomposition parameters ...")

        # Determine the path to the parameters file
        path = fs.join(self.components_path, "parameters.dat")

        # Load the parameters
        self.parameters = load_parameters(path)

    # -----------------------------------------------------------------

    def load_projection(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the projection system ...")

        # Determine the path to the projection file
        path = fs.join(self.components_path, "earth.proj")

        # Load the projection system
        self.projection = GalaxyProjection.from_file(path)

    # -----------------------------------------------------------------

    def load_truncation_ellipse(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the ellipse region used for truncating the observed images ...")

        # Determine the path
        path = fs.join(self.truncation_path, "ellipse.reg")

        # Get the ellipse
        region = SkyRegion.from_file(path)
        self.ellipse = region[0]

    # -----------------------------------------------------------------

    def load_fluxes(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the observed fluxes table ...")

        # Determine the path to the fluxes table
        fluxes_path = fs.join(self.phot_path, "fluxes.dat")

        # Load the fluxes table
        self.fluxes = tables.from_file(fluxes_path, format="ascii.ecsv")

    # -----------------------------------------------------------------

    def create_wavelength_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the wavelength grid ...")

        # Verify the grid parameters
        if self.config.wavelengths.npoints < 2: raise ValueError("the number of points in the low-resolution grid should be at least 2")
        if self.config.wavelengths.npoints_zoom < 2: raise ValueError("the number of points in the high-resolution subgrid should be at least 2")
        if self.config.wavelengths.min <= 0: raise ValueError("the shortest wavelength should be positive")
        if (self.config.wavelengths.min_zoom <= self.config.wavelengths.min
            or self.config.wavelengths.max_zoom <= self.config.wavelengths.min_zoom
            or self.config.wavelengths.max <= self.config.wavelengths.max_zoom):
                raise ValueError("the high-resolution subgrid should be properly nested in the low-resolution grid")

        logmin = np.log10(float(self.config.wavelengths.min))
        logmax = np.log10(float(self.config.wavelengths.max))
        logmin_zoom = np.log10(float(self.config.wavelengths.min_zoom))
        logmax_zoom = np.log10(float(self.config.wavelengths.max_zoom))

        # Build the high- and low-resolution grids independently
        base_grid = np.logspace(logmin, logmax, num=self.config.wavelengths.npoints, endpoint=True, base=10)
        zoom_grid = np.logspace(logmin_zoom, logmax_zoom, num=self.config.wavelengths.npoints_zoom, endpoint=True, base=10)

        # Merge the two grids
        total_grid = []

        # Add the wavelengths of the low-resolution grid before the first wavelength of the high-resolution grid
        for wavelength in base_grid:
            if wavelength < self.config.wavelengths.min_zoom: total_grid.append(wavelength)

        # Add the wavelengths of the high-resolution grid
        for wavelength in zoom_grid: total_grid.append(wavelength)

        # Add the wavelengths of the low-resolution grid after the last wavelength of the high-resolution grid
        for wavelength in base_grid:
            if wavelength > self.config.wavelengths.max_zoom: total_grid.append(wavelength)

        # Add the central wavelengths of the filters used for normalizing the stellar components
        bisect.insort(total_grid, self.i1.centerwavelength())
        bisect.insort(total_grid, self.fuv.centerwavelength())

        # Create table for the wavelength grid
        self.wavelength_grid = WavelengthGrid.from_wavelengths(total_grid)

    # -----------------------------------------------------------------

    def create_bulge_model(self):

        """
        :return:
        """

        # Inform the user
        log.info("Creating the bulge model ...")

        # Create a Sersic model for the bulge
        self.bulge = SersicModel.from_galfit(self.parameters.bulge, self.parameters.inclination, self.parameters.disk.PA)

    # -----------------------------------------------------------------

    def create_deprojection_model(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the deprojection parameters ...")

        filename = None
        hz = None

        # Get the galaxy distance, the inclination and position angle
        distance = self.parameters.distance
        inclination = self.parameters.inclination
        pa = self.parameters.disk.PA

        # Get the center pixel
        pixel_center = self.parameters.center.to_pixel(self.reference_wcs)
        xc = pixel_center.x
        yc = pixel_center.y

        # Get the pixelscale in physical units
        pixelscale_angular = self.reference_wcs.xy_average_pixelscale * Unit("pix") # in deg
        pixelscale = (pixelscale_angular * distance).to("pc", equivalencies=dimensionless_angles())

        # Get the number of x and y pixels
        x_size = self.reference_wcs.xsize
        y_size = self.reference_wcs.ysize

        # Create the deprojection model
        self.deprojection = DeprojectionModel(filename, pixelscale, pa, inclination, x_size, y_size, xc, yc, hz)

    # -----------------------------------------------------------------

    def create_instrument(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the instrument ...")

        # Create an SED instrument
        self.instrument = SEDInstrument.from_projection(self.projection)

    # -----------------------------------------------------------------

    def adjust_ski(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adjusting the ski file parameters ...")

        # Remove the existing instruments
        self.ski.remove_all_instruments()

        # Add the instrument
        self.ski.add_instrument("earth", self.instrument)

        # Set the number of photon packages
        self.ski.setpackages(self.config.packages)

        # Set the name of the wavelength grid file
        self.ski.set_file_wavelength_grid("wavelengths.txt")

        # Set the stellar and dust components
        self.set_components()

        # Set transient dust emissivity
        self.ski.set_transient_dust_emissivity()

        # Set the dust grid
        if self.config.dust_grid == "cartesian": self.set_cartesian_dust_grid()
        elif self.config.dust_grid == "bintree": self.set_bintree_dust_grid()
        elif self.config.dust_grid == "octtree": self.set_octtree_dust_grid()
        else: raise ValueError("Invalid option for dust grid type")

        # Set all-cells dust library
        self.ski.set_allcells_dust_lib()

        # Dust self-absorption
        if self.config.selfabsorption: self.ski.enable_selfabsorption()
        else: self.ski.disable_selfabsorption()

        # Disable all writing options
        self.ski.disable_all_writing_options()

    # -----------------------------------------------------------------

    def set_components(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the stellar and dust components ...")

        # Set the evolved stellar bulge component
        self.set_bulge_component()

        # Set the evolved stellar disk component
        self.set_old_stellar_component()

        # Set the young stellar component
        self.set_young_stellar_component()

        # Set the ionizing stellar component
        self.set_ionizing_stellar_component()

        # The dust component
        self.set_dust_component()

    # -----------------------------------------------------------------

    def set_bulge_component(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the bulge component ...")

        # Like M31
        bulge_template = "BruzualCharlot"
        bulge_age = 12
        bulge_metallicity = 0.02

        # Get the flux density of the bulge
        fluxdensity = self.parameters.bulge.fluxdensity # In Jy

        # Convert the flux density into a spectral luminosity
        luminosity = fluxdensity_to_luminosity(fluxdensity, self.i1.pivotwavelength() * Unit("micron"), self.parameters.distance)

        # Get the spectral luminosity in solar units
        #luminosity = luminosity.to(self.sun_i1).value

        # Set the parameters of the bulge
        self.ski.set_stellar_component_geometry("Evolved stellar bulge", self.bulge)
        self.ski.set_stellar_component_sed("Evolved stellar bulge", bulge_template, bulge_age, bulge_metallicity) # SED
        #self.ski.set_stellar_component_luminosity("Evolved stellar bulge", luminosity, self.i1) # normalization by band
        self.ski.set_stellar_component_luminosity("Evolved stellar bulge", luminosity, self.i1.centerwavelength() * Unit("micron"))

    # -----------------------------------------------------------------

    def set_old_stellar_component(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the old stellar component ...")

        # Like M31
        disk_template = "BruzualCharlot"
        disk_age = 8
        disk_metallicity = 0.02

        # Get the scale height
        #scale_height = 521. * Unit("pc") # first models
        scale_height = self.parameters.disk.hr / 8.26 # De Geyter et al. 2014

        # Get the 3.6 micron flux density with the bulge subtracted
        i1_index = tables.find_index(self.fluxes, "I1", "Band")
        fluxdensity = self.fluxes["Flux"][i1_index]*Unit("Jy") - self.parameters.bulge.fluxdensity

        # Convert the flux density into a spectral luminosity
        luminosity = fluxdensity_to_luminosity(fluxdensity, self.i1.pivotwavelength() * Unit("micron"), self.parameters.distance)

        # Get the spectral luminosity in solar units
        #luminosity = luminosity.to(self.sun_i1).value

        # Set the parameters of the evolved stellar component
        self.deprojection.filename = "old_stars.fits"
        self.deprojection.scale_height = scale_height
        self.ski.set_stellar_component_geometry("Evolved stellar disk", self.deprojection)
        self.ski.set_stellar_component_sed("Evolved stellar disk", disk_template, disk_age, disk_metallicity) # SED
        #self.ski.set_stellar_component_luminosity("Evolved stellar disk", luminosity, self.i1) # normalization by band
        self.ski.set_stellar_component_luminosity("Evolved stellar disk", luminosity, self.i1.centerwavelength() * Unit("micron"))

    # -----------------------------------------------------------------

    def set_young_stellar_component(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the young stellar component ...")

        # Like M31
        young_template = "BruzualCharlot"
        young_age = 0.1
        young_metallicity = 0.02

        # Get the scale height
        #scale_height = 150 * Unit("pc") # first models
        scale_height = 100. * Unit("pc") # M51

        # Get the FUV flux density
        fuv_index = tables.find_index(self.fluxes, "FUV", "Band")
        fluxdensity = 5. * self.fluxes["Flux"][fuv_index] * Unit("Jy")

        # Convert the flux density into a spectral luminosity
        luminosity = fluxdensity_to_luminosity(fluxdensity, self.fuv.pivotwavelength() * Unit("micron"), self.parameters.distance)

        # Get the spectral luminosity in solar units
        #luminosity = luminosity.to(self.sun_fuv).value

        # Set the parameters of the young stellar component
        self.deprojection.filename = "young_stars.fits"
        self.deprojection.scale_height = scale_height
        self.ski.set_stellar_component_geometry("Young stars", self.deprojection)
        self.ski.set_stellar_component_sed("Young stars", young_template, young_age, young_metallicity) # SED
        #self.ski.set_stellar_component_luminosity("Young stars", luminosity, self.fuv) # normalization by band
        self.ski.set_stellar_component_luminosity("Young stars", luminosity, self.fuv.centerwavelength() * Unit("micron"))

    # -----------------------------------------------------------------

    def set_ionizing_stellar_component(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the ionizing stellar component ...")

        # Like M51 and M31
        ionizing_metallicity = 0.02
        ionizing_compactness = 6
        ionizing_pressure = 1e12 * Unit("K/m3")
        ionizing_covering_factor = 0.2

        # Get the scale height
        #scale_height = 150 * Unit("pc") # first models
        scale_height = 100. * Unit("pc") # M51

        # Convert the SFR into a FUV luminosity
        sfr = 1.0 # The star formation rate
        mappings = Mappings(ionizing_metallicity, ionizing_compactness, ionizing_pressure, ionizing_covering_factor, sfr)
        luminosity = mappings.luminosity_for_filter(self.fuv)
        #luminosity = luminosity.to(self.sun_fuv).value

        # Set the parameters of the ionizing stellar component
        self.deprojection.filename = "ionizing_stars.fits"
        self.deprojection.scale_height = scale_height
        self.ski.set_stellar_component_geometry("Ionizing stars", self.deprojection)
        self.ski.set_stellar_component_mappingssed("Ionizing stars", ionizing_metallicity, ionizing_compactness, ionizing_pressure, ionizing_covering_factor) # SED
        #self.ski.set_stellar_component_luminosity("Ionizing stars", luminosity, self.fuv) # normalization by band
        self.ski.set_stellar_component_luminosity("Ionizing stars", luminosity, self.fuv.centerwavelength() * Unit("micron"))

    # -----------------------------------------------------------------

    def set_dust_component(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the dust component ...")

        #scale_height = 260.5 * Unit("pc") # first models
        scale_height = 200. * Unit("pc") # M51
        dust_mass = 1.5e7 * Unit("Msun")

        hydrocarbon_pops = 25
        enstatite_pops = 25
        forsterite_pops = 25

        # Set the parameters of the dust component
        self.deprojection.filename = "dust.fits"
        self.deprojection.scale_height = scale_height
        self.ski.set_dust_component_geometry(0, self.deprojection)
        self.ski.set_dust_component_themis_mix(0, hydrocarbon_pops, enstatite_pops, forsterite_pops) # dust mix
        self.ski.set_dust_component_mass(0, dust_mass) # dust mass

    # -----------------------------------------------------------------

    def set_cartesian_dust_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the cartesian dust grid ...")

        # Calculate the major radius of the truncation ellipse in physical coordinates (pc)
        major_angular = self.ellipse.major  # major axis length of the sky ellipse
        radius_physical = (major_angular * self.parameters.distance).to("pc", equivalencies=dimensionless_angles())

        # Calculate the boundaries of the dust grid
        min_x = - radius_physical
        max_x = radius_physical
        min_y = - radius_physical
        max_y = radius_physical
        min_z = -3. * Unit("kpc")
        max_z = 3. * Unit("kpc")

        # Get the pixelscale in physical units
        distance = self.parameters.distance
        pixelscale_angular = self.reference_wcs.xy_average_pixelscale * Unit("pix")  # in deg
        pixelscale = (pixelscale_angular * distance).to("pc", equivalencies=dimensionless_angles())

        # Because we (currently) can't position the grid exactly as the 2D pixels,
        # take half of the pixel size to avoid too much interpolation
        #smallest_scale = 0.5 * pixelscale
        smallest_scale = pixelscale # limit the number of cells

        # Calculate the number of bins in each direction
        x_bins = int(math.ceil((max_x-min_x).to("pc").value / smallest_scale.to("pc").value))
        y_bins = int(math.ceil((max_y-min_y).to("pc").value / smallest_scale.to("pc").value))
        z_bins = int(math.ceil((max_z-min_z).to("pc").value / smallest_scale.to("pc").value))

        # Set the cartesian dust grid
        self.ski.set_cartesian_dust_grid(min_x, max_x, min_y, max_y, min_z, max_z, x_bins, y_bins, z_bins)

    # -----------------------------------------------------------------

    def set_bintree_dust_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the bintree dust grid ...")

        # Calculate the major radius of the truncation ellipse in physical coordinates (pc)
        major_angular = self.ellipse.major # major axis length of the sky ellipse
        radius_physical = (major_angular * self.parameters.distance).to("pc", equivalencies=dimensionless_angles())

        # Calculate the boundaries of the dust grid
        min_x = - radius_physical
        max_x = radius_physical
        min_y = - radius_physical
        max_y = radius_physical
        min_z = -3. * Unit("kpc")
        max_z = 3. * Unit("kpc")

        # Get the pixelscale in physical units
        distance = self.parameters.distance
        pixelscale_angular = self.reference_wcs.xy_average_pixelscale * Unit("pix")  # in deg
        pixelscale = (pixelscale_angular * distance).to("pc", equivalencies=dimensionless_angles())

        # Because we (currently) can't position the grid exactly as the 2D pixels (rotation etc.),
        # take half of the pixel size to avoid too much interpolation
        smallest_scale = 0.5 * pixelscale

        # Set a minimum level for the tree
        min_level = 9

        # Calculate the minimum division level that is necessary to resolve the smallest scale of the input maps
        extent_x = (max_x - min_x).to("pc").value
        smallest_scale = smallest_scale.to("pc").value
        max_level = min_level_for_smallest_scale_bintree(extent_x, smallest_scale)

        # Set the maximum mass fraction
        max_mass_fraction = 0.5e-6

        # Set the bintree dust grid
        self.ski.set_binary_tree_dust_grid(min_x, max_x, min_y, max_y, min_z, max_z, min_level=min_level, max_level=max_level, max_mass_fraction=max_mass_fraction)

    # -----------------------------------------------------------------

    def set_octtree_dust_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Configuring the octtree dust grid ...")

        # Calculate the major radius of the truncation ellipse in physical coordinates (pc)
        major_angular = self.ellipse.major  # major axis length of the sky ellipse
        radius_physical = (major_angular * self.parameters.distance).to("pc", equivalencies=dimensionless_angles())

        # Calculate the boundaries of the dust grid
        min_x = - radius_physical
        max_x = radius_physical
        min_y = - radius_physical
        max_y = radius_physical
        min_z = -3. * Unit("kpc")
        max_z = 3. * Unit("kpc")

        # Get the pixelscale in physical units
        distance = self.parameters.distance
        pixelscale_angular = self.reference_wcs.xy_average_pixelscale * Unit("pix")  # in deg
        pixelscale = (pixelscale_angular * distance).to("pc", equivalencies=dimensionless_angles())

        # Because we (currently) can't position the grid exactly as the 2D pixels (rotation etc.),
        # take half of the pixel size to avoid too much interpolation
        smallest_scale = 0.5 * pixelscale

        # Set a minimum level for the octree
        min_level = 3

        # Calculate the minimum division level that is necessary to resolve the smallest scale of the input maps
        extent_x = (max_x - min_x).to("pc").value
        smallest_scale = smallest_scale.to("pc").value
        max_level = min_level_for_smallest_scale_octtree(extent_x, smallest_scale)

        # Set the octtree dust grid
        self.ski.set_octtree_dust_grid(min_x, max_x, min_y, max_y, min_z, max_z, min_level=min_level, max_level=max_level)

    # -----------------------------------------------------------------

    def adjust_ski_contributions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adjusting ski files for simulating the contribution of the various stellar components ...")

        # Loop over the different contributions, create seperate ski file instance
        contributions = ["old", "young", "ionizing"]
        component_names = {"old": ["Evolved stellar bulge", "Evolved stellar disk"],
                           "young": "Young stars",
                           "ionizing": "Ionizing stars"}
        for contribution in contributions:

            # Create a copy of the ski file instance
            ski = self.ski.copy()

            # Remove other stellar components
            ski.remove_stellar_components_except(component_names[contribution])

            # Add the ski file to the dictionary
            self.ski_contributions[contribution] = ski

    # -----------------------------------------------------------------

    def calculate_weights(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the weight to give to each band ...")

        # Create the table to contain the weights
        self.weights = tables.new([[], [], []], names=["Instrument", "Band", "Weight"], dtypes=["S5", "S7", "float64"])

        # Initialize lists to contain the filters of the different wavelength ranges
        uv_bands = []
        optical_bands = []
        nir_bands = []
        mir_bands = []
        fir_bands = []
        submm_bands = []

        # Set the number of groups
        number_of_groups = 6

        # Loop over the entries in the observed fluxes table
        for i in range(len(self.fluxes)):

            instrument = self.fluxes["Instrument"][i]
            band = self.fluxes["Band"][i]

            # Construct filter
            fltr = Filter.from_instrument_and_band(instrument, band)

            # Get the central wavelength
            wavelength = fltr.centerwavelength() * Unit("micron")

            # Get a string identifying which portion of the wavelength spectrum this wavelength belongs to
            spectrum = wavelengths.name_in_spectrum(wavelength)

            #print(band, wavelength, spectrum)

            # Determine to which group
            if spectrum[0] == "UV": uv_bands.append(fltr)
            elif spectrum[0] == "Optical": optical_bands.append(fltr)
            elif spectrum[0] == "Optical/IR": optical_bands.append(fltr)
            elif spectrum[0] == "IR":
                if spectrum[1] == "NIR": nir_bands.append(fltr)
                elif spectrum[1] == "MIR": mir_bands.append(fltr)
                elif spectrum[1] == "FIR": fir_bands.append(fltr)
                else: raise RuntimeError("Unknown IR range")
            elif spectrum[0] == "Submm": submm_bands.append(fltr)
            else: raise RuntimeError("Unknown wavelength range")

        # Determine the weight for each group of filters
        number_of_data_points = len(self.fluxes)
        uv_weight = 1. / (len(uv_bands) * number_of_groups) * number_of_data_points
        optical_weight = 1. / (len(optical_bands) * number_of_groups) * number_of_data_points
        nir_weight = 1. / (len(nir_bands) * number_of_groups) * number_of_data_points
        mir_weight = 1. / (len(mir_bands) * number_of_groups) * number_of_data_points
        fir_weight = 1. / (len(fir_bands) * number_of_groups) * number_of_data_points
        submm_weight = 1. / (len(submm_bands) * number_of_groups) * number_of_data_points

        #print("UV", len(uv_bands), uv_weight)
        #print("Optical", len(optical_bands), optical_weight)
        #print("NIR", len(nir_bands), nir_weight)
        #print("MIR", len(mir_bands), mir_weight)
        #print("FIR", len(fir_bands), fir_weight)
        #print("Submm", len(submm_bands), submm_weight)

        # Loop over the bands in each group and set the weight in the weights table
        for fltr in uv_bands: self.weights.add_row([fltr.instrument, fltr.band, uv_weight])
        for fltr in optical_bands: self.weights.add_row([fltr.instrument, fltr.band, optical_weight])
        for fltr in nir_bands: self.weights.add_row([fltr.instrument, fltr.band, nir_weight])
        for fltr in mir_bands: self.weights.add_row([fltr.instrument, fltr.band, mir_weight])
        for fltr in fir_bands: self.weights.add_row([fltr.instrument, fltr.band, fir_weight])
        for fltr in submm_bands: self.weights.add_row([fltr.instrument, fltr.band, submm_weight])

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the input
        self.write_input()

        # Write the ski file
        self.write_ski_file()

        # Write the ski files for simulating the contributions of the various stellar components
        self.write_ski_files_contributions()

        # Write the weights table
        self.write_weights()

    # -----------------------------------------------------------------

    def write_input(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the input ...")

        # Write the wavelength grid
        self.write_wavelength_grid()

        # Write the old stellar map
        self.write_old_stars()

        # Write the map of young stars
        self.write_young_stars()

        # Write the map of ionizing stars
        self.write_ionizing_stars()

        # Write the dust map
        self.write_dust()

    # -----------------------------------------------------------------

    def write_wavelength_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the wavelength grid ...")

        # Determine the path to the wavelength grid file
        grid_path = fs.join(self.fit_in_path, "wavelengths.txt")

        # Write the wavelength grid
        self.wavelength_grid.to_skirt_input(grid_path)

    # -----------------------------------------------------------------

    def write_old_stars(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Copying the map of old stars to the input directory ...")

        # Determine the path to the old stars map
        old_stars_path = fs.join(self.maps_path, "old_stars.fits")

        # Copy the map
        fs.copy_file(old_stars_path, self.fit_in_path)

    # -----------------------------------------------------------------

    def write_young_stars(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Copying the map of young stars to the input directory ...")

        # Determine the path to the young stars map
        young_stars_path = fs.join(self.maps_path, "young_stars.fits")

        # Copy the map
        fs.copy_file(young_stars_path, self.fit_in_path)

    # -----------------------------------------------------------------

    def write_ionizing_stars(self):

        """
        This function ...
        :return:
        """

        # Determine the path to the ionizing stars map
        ionizing_stars_path = fs.join(self.maps_path, "ionizing_stars.fits")

        # Copy the map
        fs.copy_file(ionizing_stars_path, self.fit_in_path)

    # -----------------------------------------------------------------

    def write_dust(self):

        """
        This function ...
        :return:
        """

        # Determine the path to the dust map
        dust_path = fs.join(self.maps_path, "dust.fits")

        # Copy the map
        fs.copy_file(dust_path, self.fit_in_path)

    # -----------------------------------------------------------------

    def write_ski_file(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the ski file to " + self.fit_ski_path + " ...")

        # Save the ski file to the specified location
        self.ski.saveto(self.fit_ski_path)

    # -----------------------------------------------------------------

    def write_ski_files_contributions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the ski files for simulating the contribution of the various stellar components ...")

        # Loop over the ski files
        for contribution in self.ski_contributions:

            # Create the directory for this contribution
            contribution_path = fs.join(self.fit_best_path, contribution)
            fs.create_directory(contribution_path)

            # Determine the path to the ski file
            ski_path = fs.join(contribution_path, self.galaxy_name + ".ski")

            # Write the ski file
            self.ski_contributions[contribution].saveto(ski_path)

    # -----------------------------------------------------------------

    def write_weights(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the table with weights to " + self.weights_table_path + " ...")

        # Write the table with weights
        tables.write(self.weights, self.weights_table_path, format="ascii.ecsv")

    # -----------------------------------------------------------------

    def generate_dust_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Running a simulation just to generate the dust grid data files ...")

        # Create a copy of the ski file
        ski = self.ski.copy()

        # Convert to oligochromatic simulation
        ski.to_oligochromatic([1. * Unit("micron")])

        # Remove the instrument system
        ski.remove_instrument_system()

        # Set the number of photon packages to zero
        ski.setpackages(0)

        # Disable all writing options, except the one for writing the dust grid and cell properties
        ski.disable_all_writing_options()
        ski.set_write_grid()
        ski.set_write_cell_properties()

        # Save the ski file to the fit/grid directory
        ski_path = fs.join(self.fit_grid_path, self.galaxy_name + ".ski")
        ski.saveto(ski_path)

        # Create the local SKIRT execution context
        skirt = SkirtExec()

        # Create the SKIRT arguments object
        arguments = SkirtArguments()
        arguments.ski_pattern = ski_path
        arguments.input_path = self.fit_in_path
        arguments.output_path = self.fit_grid_path

        # Run SKIRT to generate the dust grid data files
        skirt.run(arguments)

        # Determine the path to the cell properties file
        cellprops_path = fs.join(self.fit_grid_path, self.galaxy_name + "_ds_cellprops.dat")

        # Get the optical depth for which 90% of the cells have a smaller value
        optical_depth = None
        for line in reversed(open(cellprops_path).readlines()):
            if "of the cells have optical depth smaller than" in line:
                optical_depth = float(line.split("than: ")[1])
                break

        # Set the maximal optical depth
        ski.set_binary_tree_max_optical_depth(optical_depth)

        # Save the ski file
        ski.save()

        # Run SKIRT again
        skirt.run(arguments)

        # Set the max optical depth also for the main ski file
        self.ski.set_binary_tree_max_optical_depth(optical_depth)

# -----------------------------------------------------------------

# The speed of light
speed_of_light = constants.c

# -----------------------------------------------------------------

def spectral_factor_hz_to_micron(wavelength):

    """
    This function ...
    :param wavelength:
    :return:
    """

    wavelength_unit = "micron"
    frequency_unit = "Hz"

    # Convert string units to Unit objects
    if isinstance(wavelength_unit, basestring): wavelength_unit = Unit(wavelength_unit)
    if isinstance(frequency_unit, basestring): frequency_unit = Unit(frequency_unit)

    conversion_factor_unit = wavelength_unit / frequency_unit

    # Calculate the conversion factor
    factor = (wavelength ** 2 / speed_of_light).to(conversion_factor_unit).value
    return 1. / factor

# -----------------------------------------------------------------

def fluxdensity_to_luminosity(fluxdensity, wavelength, distance):

    """
    This function ...
    :param fluxdensity:
    :param wavelength:
    :param distance:
    :return:
    """

    luminosity = (fluxdensity * 4. * math.pi * distance ** 2.).to("W/Hz")

    # 3 ways:
    #luminosity_ = luminosity.to("W/micron", equivalencies=spectral_density(wavelength)) # does not work
    luminosity_ = (speed_of_light * luminosity / wavelength**2).to("W/micron")
    luminosity = luminosity.to("W/Hz").value * spectral_factor_hz_to_micron(wavelength) * Unit("W/micron")
    #print(luminosity_, luminosity) # is OK!

    return luminosity

# -----------------------------------------------------------------

def min_level_for_smallest_scale_bintree(extent, smallest_scale):

    """
    This function ...
    :param extent:
    :param smallest_scale:
    :return:
    """

    ratio = extent / smallest_scale
    octtree_level = int(math.ceil(math.log(ratio, 2)))
    level = int(3 * octtree_level)
    return level

# -----------------------------------------------------------------

def min_level_for_smallest_scale_octtree(extent, smallest_scale):

    """
    This function ...
    :param extent:
    :param smallest_scale:
    :return:
    """

    ratio = extent / smallest_scale
    octtree_level = int(math.ceil(math.log(ratio, 2)))
    return octtree_level

# -----------------------------------------------------------------
