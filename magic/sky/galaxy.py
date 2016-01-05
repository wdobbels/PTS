#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       AstroMagic -- the image editor for astronomers        **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.sky.galaxy Contains the Galaxy class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
import matplotlib.pyplot as plt

# Import astronomical modules
import astropy.io.fits as pyfits
import aplpy
from astropy import units as u
from astroquery.ned import Ned
import astroquery.exceptions
from astropy.coordinates import Angle
import astropy.coordinates as coord
from astroquery.vizier import Vizier

# Import the relevant AstroMagic classes and modules
from ..core import Source
from .skyobject import SkyObject
from ..basics import Extent

# -----------------------------------------------------------------

class Galaxy(SkyObject):

    """
    This class ...
    """

    def __init__(self, name, position, redshift, galaxy_type, names, distance, inclination, d25, major, minor, position_angle):

        """
        The constructor ...
        :param position:
        :param name:
        :return:
        """

        # Set attributes
        self.name = name
        self.redshift = redshift
        self.type = galaxy_type
        self.names = names
        self.distance = distance
        self.inclination = inclination
        self.d25 = d25
        self.major = major
        self.minor = minor
        self.pa = position_angle

        # Set the principal and companion flags to False initially
        self.principal = False
        self.companion = False

        # Initialize a list for the names of companion galaxies
        self.companions = []
        self.parent = None

        # Call the constructor of the base class
        super(Galaxy, self).__init__(position)

    # -----------------------------------------------------------------

    @classmethod
    def from_name(cls, name, position=None):

        """
        This function ...
        :return:
        """

        # Obtain more information about this galaxy
        try:

            ned_result = Ned.query_object(name)
            ned_entry = ned_result[0]

            # Get a more common name for this galaxy (sometimes, the name obtained from NED is one starting with 2MASX .., use the PGC name in this case)
            if ned_entry["Object Name"].startswith("2MASX "): self.name = name
            else: self.name = ned_entry["Object Name"]

            # Get the redshift
            self.redshift = ned_entry["Redshift"]

            # Get the type (G=galaxy, HII ...)
            self.type = ned_entry["Type"]

        except astroquery.exceptions.RemoteServiceError:

            # Set attributes
            self.name = name
            self.redshift = None
            self.type = None

        # Create a new Vizier object and set the row limit to -1 (unlimited)
        viz = Vizier(keywords=["galaxies", "optical"])
        viz.ROW_LIMIT = -1

        # Query Vizier and obtain the resulting table
        result = viz.query_object(name, catalog=["VII/237"])
        table = result[0]

        # Get the correct entry (sometimes, for example for mergers, querying with the name of one galaxy gives two hits! We have to obtain the right one each time!)
        if len(table) == 0: raise ValueError("The galaxy could not be found under this name")
        elif len(table) == 1: entry = table[0]
        else:

            entry = None

            # Some rows don't have names, if no match is found based on the name just take the row that has other names defined
            rows_with_names = []
            for row in table:
                if row["ANames"]: rows_with_names.append(row)

            # If only one row remains, take that one for the galaxy we are looking for
            if len(rows_with_names) == 1: entry = row

            # Else, loop over the rows where names are defined and look for a match
            else:
                for row in rows_with_names:

                    names = row["ANames"]

                    if name.replace(" ", "") in names or self.name.replace(" ", "") in names:

                        entry = row
                        break

            # If no matches are found, look for the table entry for which the coordinate matches the given position (if any)
            if position is not None:
                for row in table:
                    if row["_RAJ2000"] == position.ra.value and row["_DEJ2000"] == position.dec.value:
                        entry = row
                        break

        # Get the right ascension and the declination
        position = coord.SkyCoord(ra=entry["_RAJ2000"], dec=entry["_DEJ2000"], unit=(u.deg, u.deg), frame='fk5')

        # Get the names given to this galaxy
        self.names = entry["ANames"].split() if entry["ANames"] else None

        # Get the size of the galaxy
        ratio = np.power(10.0, entry["logR25"]) if entry["logR25"] else None
        diameter = np.power(10.0, entry["logD25"]) * 0.1 * u.arcmin if entry["logD25"] else None

        #print("  D25_diameter = ", diameter)

        radial_profiles_result = viz.query_object(name, catalog="J/ApJ/658/1006")

        if len(radial_profiles_result) > 0:

            radial_profiles_entry = radial_profiles_result[0][0]

            self.distance = radial_profiles_entry["Dist"] * u.Unit("Mpc")
            self.inclination = Angle(radial_profiles_entry["i"], u.deg)
            self.d25 = radial_profiles_entry["D25"] * u.arcmin

        else:

            self.distance = None
            self.inclination = None
            self.d25 = None

        # Get the size of major and minor axes
        self.major = diameter
        self.minor = diameter / ratio if diameter is not None and ratio is not None else None

        # Get the position angle of the galaxy
        self.pa = Angle(entry["PA"] - 90.0, u.deg) if entry["PA"] else None

        # Create and return a new Galaxy instance
        return cls()

    # -----------------------------------------------------------------

    def contains(self, position):

        """
        This function ...
        :param star:
        :return:
        """

        # If the position does not lie within the cutout box of the galaxy's source, return False
        if not self.source.cutout.contains(position): return False

        # If it does, check whether the pixel position is masked by the mask of the galaxy's source
        return self.source.mask.masks(self.source.cutout.rel_position(position))

    # -----------------------------------------------------------------

    @property
    def has_extent(self):

        """
        This function ...
        :return:
        """

        # Check whether the length of the major axis is defined
        return self.major is not None

    # -----------------------------------------------------------------

    def ellipse_parameters(self, wcs, pixelscale, default_radius):

        """
        This function ...
        :param default_radius:
        :return:
        """

        #print("pixelscale=", pixelscale)

        #print("self.pa=", self.pa)
        #print("self.major=", self.major)
        #print("self.minor=", self.minor)

        if self.pa is None: angle = Angle(0.0, u.deg)
        else: angle = self.pa

        if self.major is None:

            x_radius = default_radius
            y_radius = default_radius

        elif self.minor is None or angle == 0.0:

            x_radius = 0.5 * self.major.to("arcsec") / pixelscale
            y_radius = x_radius

        else:

            x_radius = 0.5 * self.major.to("arcsec") / pixelscale
            y_radius = 0.5 * self.minor.to("arcsec") / pixelscale

        #print("x_radius=", x_radius)
        #print("y_radius=", y_radius)

        pixel_position = self.pixel_position(wcs)

        #print("PIXEL_POSITION=", pixel_position)

        # Return the parameters
        return pixel_position, Extent(x=x_radius, y=y_radius), angle

    # -----------------------------------------------------------------

    def source_from_parameters(self, frame, outer_factor, expansion_factor=1.0):

        """
        This function ...
        :return:
        """

        # Get the parameters describing the elliptical contour
        center, radius, angle = self.ellipse_parameters(frame.wcs, frame.pixelscale, None)

        #print("center_here=", center)

        if center.x < 0 or center.y < 0:
            self.source = None
            return

        # Create a source object
        self.source = Source.from_ellipse(frame, center, radius*expansion_factor, angle, outer_factor)

        #print(self.source.cutout.shape)

        if self.source.cutout.shape[0] == 0 or self.source.cutout.shape[1] == 0:

            print(self.name)
            print("radius=", radius)

    # -----------------------------------------------------------------

    def fit_model(self, config):

        """
        This function ...
        :param frame:
        :param config:
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def remove(self, frame, mask, config):

        """
        This function ...
        :param frame:
        :param mask:
        :param config:
        :return:
        """

        # If a segment was found that can be identified with a source
        if self.has_source or config.remove_if_undetected:

            # Estimate the background
            self.source.estimate_background(config.interpolation_method, config.sigma_clip)

            # Replace the frame with the estimated background
            self.source.background.replace(frame, where=self.source.mask)

            # Update the mask
            mask[self.source.cutout.y_slice, self.source.cutout.x_slice] += self.source.mask

    # -----------------------------------------------------------------

    def plot(self, frame):

        """
        This function ...
        :return:
        """

        if self.has_source:

            # Create a HDU from this frame with the image header
            hdu = pyfits.PrimaryHDU(self.source.cutout)

            # Create a figure canvas
            figure = plt.figure(figsize=(15, 15))

            # Create a figure from this frame
            plot = aplpy.FITSFigure(hdu, figure=figure)

            # Plot in color scale
            plot.show_colorscale()

            # Add a color bar if requested
            plot.add_colorbar()

            if self.has_aperture: self.aperture.plot(color='white', lw=1.5, alpha=0.5, ax=plt.gca())

            # Show the plot
            plt.show()

        else:

            # Create a HDU from this frame with the image header
            hdu = pyfits.PrimaryHDU(frame, frame.wcs.to_header())

            # Create a figure canvas
            figure = plt.figure(figsize=(20, 20))

            # Create a figure from this frame
            plot = aplpy.FITSFigure(hdu, figure=figure)

            # Plot in color scale
            plot.show_colorscale()

            # Add a color bar if requested
            plot.add_colorbar()

            if self.has_aperture: self.aperture.plot(color='white', lw=1.5, alpha=0.5, ax=plt.gca())

            # Show the plot
            plt.show()

# -----------------------------------------------------------------