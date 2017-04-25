#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.truncation.truncation Contains the Truncator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ...magic.region.list import SkyRegionList, PixelRegionList
from .component import TruncationComponent
from ...core.tools import filesystem as fs
from ...core.tools.logging import log
from ...magic.dist_ellipse import distance_ellipse
from ...core.basics.range import RealRange
from ...core.basics.map import Map

# -----------------------------------------------------------------

class Truncator(TruncationComponent):
    
    """
    This class...
    """

    def __init__(self, config=None, interactive=False):

        """
        The constructor ...
        :param config:
        :param interactive:
        :return:
        """

        # Call the constructor of the base class
        super(Truncator, self).__init__(config, interactive)

        # --- Attributes ---

        # The statistics for each image
        self.statistics = dict()

        # The frames and error maps
        self.frames = None
        self.errormaps = None
        self.masks = None

        # The sky ellipses
        self.sky_ellipses = dict()

        # Truncation ellipse
        self.ellipses = defaultdict(dict)

        # Paths
        self.paths = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Load the data
        self.load_data()

        # 3. Create directories
        self.create_directories()

        # 4. Find the best radius for the truncation
        self.calculate_statistics()

        # 5. Create the ellipses
        self.create_ellipses()

        # 6. Writing
        self.write()

        # 7. Plotting
        self.plot()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(Truncator, self).setup(**kwargs)

    # -----------------------------------------------------------------

    def load_data(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Loading the data ...")

        # Get the frames
        self.frames = self.dataset.get_framelist()

        # Get the error maps
        self.errormaps = self.dataset.get_errormaplist()

        # Loop over all prepared images, get the images
        self.masks = dict()
        for name in self.dataset.names:

            # Get the mask
            mask_names = ["padded", "bad"]
            mask = self.dataset.get_image_masks_union(name, mask_names, strict=False)

            # Set the mask
            if mask is None: continue
            self.masks[name] = mask

    # -----------------------------------------------------------------

    def create_directories(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Creating a directory for each image ...")

        # Loop over the image
        for name in self.frames.names:

            # Create directory
            path = fs.create_directory_in(self.truncation_path, name)

            # Set path
            self.paths[name] = path

    # -----------------------------------------------------------------

    def calculate_statistics(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Getting the statistics as a function of radius ...")

        # Get the angle
        center = self.disk_ellipse.center  # in sky coordinates
        semimajor = self.disk_ellipse.semimajor
        semiminor = self.disk_ellipse.semiminor
        angle = self.disk_ellipse.angle

        # Determine the ratio of semimajor and semiminor
        ratio = semiminor / semimajor

        # Loop over all prepared images
        for name in self.frames.names:

            # Get the image
            frame = self.dataset.get_frame(name)

            # Get the mask
            mask_names = ["padded", "bad"]
            mask = self.dataset.get_image_masks_union(name, mask_names, strict=False)

            # Convert center to pixel coordinates
            center_pix = center.to_pixel(frame.wcs)

            # Create distance ellipse frame
            distance_frame = distance_ellipse(frame.shape, center_pix, ratio, angle)

            radius_list = []
            signal_to_noise_list = []
            nmasked_list = []

            # Loop over the radii
            min_distance = np.min(distance_frame)
            max_distance = np.max(distance_frame)
            step = (max_distance - min_distance) / float(self.config.nbins)

            # Set the first range
            radius_range = RealRange(min_distance, min_distance + step)

            # Loop, shifting ranges of radius
            while True:

                # Check the range
                if radius_range.min > max_distance: break

                # Get the average radius
                radius_center = radius_range.center

                # Make a mask of the pixels corresponding to the current radius range
                range_mask = radius_range.min <= distance_frame < radius_range.max

                # Calculate the mean signal to noise in the pixels
                signal_to_noises = self.frames[name][range_mask] / self.errormaps[name][mask]

                # Calcalute the mean signal to noise
                signal_to_noise = np.mean(signal_to_noises)

                # Make a mask of all the pixels below the center radius
                below_mask = distance_frame < radius_center

                # Calculate the number of masked pixels
                nmasked = np.sum(mask[below_mask])
                ntotal = np.sum(below_mask)
                rel_nmasked = nmasked / ntotal

                # Add point
                radius_list.append(radius_center)
                signal_to_noise_list.append(signal_to_noise)
                nmasked_list.append(rel_nmasked)

                # Shift the range
                radius_range += step

            # Set the statistics for this image
            statistics = Map()
            statistics.radii = radius_list
            statistics.snr = signal_to_noise_list
            statistics.nmasked = nmasked_list
            self.statistics[name] = statistics

    # -----------------------------------------------------------------

    @lazyproperty
    def factors(self):

        """
        This function ..
        :return: 
        """

        return self.config.factor_range.linear(self.config.factor_nvalues, as_list=True)

    # -----------------------------------------------------------------

    def create_ellipses(self):

        """
        This function ....
        :return: 
        """

        # Inform the user
        log.info("Creating ellipses ...")

        # Loop over the different scale factors
        for factor in self.factors:

            # Get the scaled ellipse
            sky_ellipse = self.disk_ellipse * factor

            # Add the sky ellipse
            self.sky_ellipses[factor] = sky_ellipse

            # Loop over the frames
            for name in self.frames.names:

                # Convert to pixel ellipse
                pixel_ellipse = sky_ellipse.to_pixel(self.frames[name].wcs)

                # Add the ellipse
                self.ellipses[name][factor] = pixel_ellipse

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the truncation ellipse
        self.write_ellipses()

        # Write the truncated images
        self.write_images()

    # -----------------------------------------------------------------

    def write_ellipses(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the ellipses ...")

        # Write sky ellipses
        self.write_sky_ellipses()

        # Write image ellipses
        self.write_image_ellipses()

    # -----------------------------------------------------------------

    def write_sky_ellipses(self):

        """
        Thisf ucntion ...
        :return: 
        """

        # Inform the user
        log.info("Writing the truncation ellipse region ...")

        # Determine the path to the region file
        path = fs.join(self.truncation_path, "ellipses.reg")

        # Create the region list
        regions = SkyRegionList()

        # Loop over the ellipses
        for factor in self.sky_ellipses:

            # Add ellipse
            ellipse = self.sky_ellipses[factor]
            ellipse.meta["text"] = str(factor)
            regions.append(ellipse)

        # Write
        regions.saveto(path)

    # -----------------------------------------------------------------

    def write_image_ellipses(self):

        """
        Thisf ucntion ...
        :return: 
        """

        # Inform the user
        log.info("Writing the image ellipses ...")

        # Loop over the images
        for name in self.ellipses:

            # Get the path
            path = fs.join(self.paths[name], "ellipses.reg")

            # Create region list
            regions = PixelRegionList()

            # Loop over the ellipses
            for factor in self.ellipses[name]:

                # Add ellipse
                ellipse = self.ellipses[name][factor]
                ellipse.meta["text"] = str(factor)
                regions.append(ellipse)

            # Write
            regions.saveto(path)

    # -----------------------------------------------------------------

    def write_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the truncated images ...")

        # Loop over the the images
        for name in self.frames.names:

            # Loop over the factors
            for factor in self.factors:

                # Get the pixel ellipse
                ellipse = self.ellipses[name][factor]

                # Convert into mask
                mask = ellipse.to_mask(self.frames[name].xsize, self.frames[name].ysize)

                # Truncate the frame
                frame = self.frames[name]
                frame[mask] = 0.0

                # Determine the path
                path = fs.join(self.paths[name], str(factor) + ".fits")

                # Save
                frame.saveto(path)

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Plotting ...")

        # Plot the curves
        self.plot_snr()

        # Plot nmasked pixels
        self.plot_nmasked()

    # -----------------------------------------------------------------

    def plot_snr(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Plotting the snr curves ...")

        # Loop over the frame names
        for name in self.statistics:

            # Get x and y
            radii = self.statistics[name].radii
            snr = self.statistics[name].snr

            # Create plot
            plt.figure()
            plt.plot(radii, snr)

            # Add vertical lines
            for factor in self.ellipses[name]:
                radius = self.ellipses[name][factor].major
                plt.axvline(x=radius)

            # Determine the path
            path = fs.join(self.paths[name], "snr.pdf")

            # Save the figure
            plt.savefig(path)
            plt.close()

    # -----------------------------------------------------------------

    def plot_nmasked(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Plotting the nmasked pixels curves ...")

        # Loop over the frame nems
        for name in self.statistics:

            # Get x and y
            radii = self.statistics[name].radii
            nmasked = self.statistics[name].nmasked

            # Create plot
            plt.figure()
            plt.plot(radii, nmasked)

            # Add vertical lines
            for factor in self.ellipses[name]:
                radius = self.ellipses[name][factor].major
                plt.axvline(x=radius)

            # Determine the path
            path = fs.join(self.paths[name], "nmasked.pdf")

            # Save the figure
            plt.savefig(path)
            plt.close()

# -----------------------------------------------------------------
