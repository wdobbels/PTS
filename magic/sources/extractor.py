#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.sources.extractor Contains the SourceExtractor class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import math
import numpy as np

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ..basics.mask import Mask
from ..region.ellipse import PixelEllipseRegion
from ..basics.coordinate import PixelCoordinate
from ..core.source import Source
from ...core.tools.logging import log
from ...core.basics.configurable import Configurable
from ..tools import masks
from ...core.basics.animation import Animation
from ..region.list import PixelRegionList
from ..core.image import Image
from ..core.frame import Frame
from ...core.tools import filesystem as fs

# -----------------------------------------------------------------

class SourceExtractor(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :return:
        """

        # Call the constructor of the base class
        super(SourceExtractor, self).__init__(config)

        # -- Attributes --

        # The image frame
        self.frame = None

        # The original minimum and maximum value
        self.minimum_value = None
        self.maximum_value = None

        # The mask of nans
        self.nan_mask = None

        # Regions
        self.galaxy_region = None
        self.star_region = None
        self.saturation_region = None
        self.other_region = None

        # The animation
        self.animation = None

        # Special mask
        self.special_mask = None

        # Segmentation maps
        self.galaxy_segments = None
        self.star_segments = None
        self.other_segments = None

        # The total mask of removed sources
        self.mask = None

        # The list of sources
        self.sources = []

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Load the sources
        self.load_sources()

        # 3. Create the mask of all sources to be removed
        self.create_mask()

        # 3. For each source, check the pixels in the background that belong to an other source
        self.set_cross_contamination()

        # 4. Remove the sources
        self.remove_sources()

        # 5. Fix extreme values that showed up during the interpolation steps
        self.fix_extreme_values()

        # 6. Set nans back into the frame
        self.set_nans()

        # Writing
        if self.config.output is not None: self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(SourceExtractor, self).setup(**kwargs)

        # Set the image frame
        if "frame" in kwargs:
            self.frame = kwargs.pop("frame")
        else: self.load_frame()

        # Regions
        #self.galaxy_region = kwargs.pop("galaxy_region")
        #self.star_region = kwargs.pop("star_region")
        #self.saturation_region = kwargs.pop("saturation_region")
        #self.other_region = kwargs.pop("other_region")

        # Segmentation maps
        #self.galaxy_segments = kwargs.pop("galaxy_segments")
        #self.star_segments = kwargs.pop("star_segments")
        #self.other_segments = kwargs.pop("other_segments")

        self.load_regions()

        self.load_segments()

        # Initialize the mask
        self.mask = Mask.empty_like(self.frame)

        # Remember the minimum and maximum value
        self.minimum_value = np.nanmin(self.frame)
        self.maximum_value = np.nanmax(self.frame)

        # Create a mask of the pixels that are NaNs
        self.nan_mask = Mask.is_nan(self.frame)
        self.frame[self.nan_mask] = 0.0

        # Make a reference to the animation
        self.animation = kwargs.pop("animation", None)

        # Create mask from special region
        if "special_region" in kwargs:
            special_region = kwargs.pop("special_region")
            self.special_mask = Mask.from_region(special_region, self.frame.xsize, self.frame.ysize) if special_region is not None else None

        # If making animation is enabled
        if self.config.animation:
            self.animation = Animation()
            self.animation.fps = 1

    # -----------------------------------------------------------------

    def load_frame(self):

        """
        This function ...
        :return:
        """

        self.frame = Frame.from_file(self.config.image)

    # -----------------------------------------------------------------

    def load_regions(self):

        """
        This function ...
        :return:
        """

        # Load the galaxy region
        galaxy_region_path = self.input_path_file("galaxies.reg")
        self.galaxy_region = PixelRegionList.from_file(galaxy_region_path) if fs.is_file(galaxy_region_path) else None

        # Load the star region
        star_region_path = self.input_path_file("stars.reg")
        self.star_region = PixelRegionList.from_file(star_region_path) if fs.is_file(star_region_path) else None

        # Load the saturation region
        saturation_region_path = self.input_path_file("saturation.reg")
        self.saturation_region = PixelRegionList.from_file(saturation_region_path) if fs.is_file(saturation_region_path) else None

        # Load the region of other sources
        other_region_path = self.input_path_file("other_sources.reg")
        self.other_region = PixelRegionList.from_file(other_region_path) if fs.is_file(other_region_path) else None

    # -----------------------------------------------------------------

    def load_segments(self):

        """
        This function ...
        :return:
        """

        # Load the image with segmentation maps
        segments = Image.from_file(self.input_path_file("segments.fits"), no_filter=True)

        # Get the segmentation maps
        self.galaxy_segments = segments.frames.galaxies if "galaxies" in segments.frames else None
        self.star_segments = segments.frames.stars if "stars" in segments.frames else None
        self.other_segments = segments.frames.other_sources if "other_sources" in segments.frames else None

    # -----------------------------------------------------------------

    def load_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the sources ...")

        # Load the galaxy sources
        self.load_galaxy_sources()

        # Load the star sources
        if self.star_region is not None: self.load_star_sources()

        # Load the other sources
        if self.other_region is not None: self.load_other_sources()

    # -----------------------------------------------------------------

    def load_galaxy_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the galaxy sources ...")

        # Loop over the shapes in the galaxy region
        for shape in self.galaxy_region:

            # Shapes without text are in this case just coordinates
            if "text" not in shape.meta: continue

            # Get the coordinate of the center for this galaxy
            center = shape.center

            # Check the label of the corresponding segment
            label = self.galaxy_segments[int(center.y), int(center.x)]

            if label == 3 or (label == 2 and self.config.remove_companions):

                # Create a source
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)

                # Check whether it is a 'special' source
                source.special = self.special_mask.masks(center) if self.special_mask is not None else False

                # Add the source to the list
                self.sources.append(source)

    # -----------------------------------------------------------------

    def load_star_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the star sources ...")

        # Loop over all stars in the region
        for shape in self.star_region:

            # Ignore shapes without text, these should be just the positions of the peaks
            if "text" not in shape.meta: continue

            # Ignore shapes with color red (stars without source)
            if shape.meta["color"] == "red": continue

            # Get the star index
            index = int(shape.meta["text"])

            # Look whether a saturation source is present
            saturation_source = None

            # Check whether the star is a foreground star
            #if self.principal_mask.masks(shape.center): foreground = True

            if self.saturation_region is not None:

                # Add the saturation sources
                # Loop over the shapes in the saturation region
                for j in range(len(self.saturation_region)):

                    saturation_shape = self.saturation_region[j]

                    if "text" not in saturation_shape.meta: continue

                    saturation_index = int(saturation_shape.meta["text"])

                    if index != saturation_index: continue
                    else:
                        # Remove the saturation shape from the region
                        saturation_shape = self.saturation_region.pop(j)

                        # Create saturation source
                        saturation_source = Source.from_shape(self.frame, saturation_shape, self.config.source_outer_factor)

                        # Replace the saturation mask
                        segments_cutout = self.star_segments[saturation_source.y_slice, saturation_source.x_slice]
                        saturation_mask = Mask(segments_cutout == index)
                        saturation_source.mask = saturation_mask.fill_holes()

                        # Break the loop
                        break

            # Check whether the star is a 'special' region
            special = self.special_mask.masks(shape.center) if self.special_mask is not None else False

            if saturation_source is not None:

                ## DILATION

                if self.config.dilate_saturation:

                    # factor = saturation_dilation_factor
                    dilation_factor = self.config.saturation_dilation_factor

                    saturation_source = saturation_source.zoom_out(dilation_factor, self.frame, keep_original_mask=True)

                    mask_area = np.sum(saturation_source.mask)
                    area_dilation_factor = dilation_factor ** 2.
                    new_area = mask_area * area_dilation_factor

                    ## Circular mask approximation

                    # ellipse = find_contour(source.mask.astype(float), source.mask)
                    # radius = ellipse.radius.norm

                    mask_radius = math.sqrt(mask_area / math.pi)
                    new_radius = math.sqrt(new_area / math.pi)

                    kernel_radius = new_radius - mask_radius

                    # Replace mask
                    saturation_source.mask = saturation_source.mask.disk_dilation(radius=kernel_radius)

                ## END DILATION CODE

                # Set special
                saturation_source.special = special

                # Add the saturation source
                self.sources.append(saturation_source)

            else:

                # Create a new source from the shape
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)

                # Set special
                source.special = special

                # Add it to the list
                self.sources.append(source)

    # -----------------------------------------------------------------

    def load_other_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the other sources ...")

        # Loop over the shapes in the other sources region
        for shape in self.other_region:

            # This is a source found by SourceFinder
            if "text" in shape.meta:

                label = int(shape.meta["text"])

                # Create a source
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)

                # Replace the source mask
                segments_cutout = self.other_segments[source.y_slice, source.x_slice]
                source.mask = Mask(segments_cutout == label).fill_holes()

                ## DILATION

                if self.config.dilate_other:

                    # DILATE SOURCE
                    # factor = other_dilation_factor

                    dilation_factor = self.config.other_dilation_factor

                    ## CODE FOR DILATION (FROM SOURCES MODULE)

                    source = source.zoom_out(dilation_factor, self.frame, keep_original_mask=True)

                    mask_area = np.sum(source.mask)
                    area_dilation_factor = dilation_factor ** 2.
                    new_area = mask_area * area_dilation_factor

                    ## Circular mask approximation

                    # ellipse = find_contour(source.mask.astype(float), source.mask)
                    # radius = ellipse.radius.norm

                    mask_radius = math.sqrt(mask_area / math.pi)
                    new_radius = math.sqrt(new_area / math.pi)

                    kernel_radius = new_radius - mask_radius

                    # Replace mask
                    source.mask = source.mask.disk_dilation(radius=kernel_radius)

                ## END DILATION CODE

            # This is a shape drawn by the user and added to the other sources region
            else:

                # Create a source
                source = Source.from_shape(self.frame, shape, self.config.source_outer_factor)

            # Check whether source is 'special'
            source.special = self.special_mask.masks(shape.center) if self.special_mask is not None else False

            # Add the source to the list
            self.sources.append(source)

    # -----------------------------------------------------------------

    def create_mask(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the mask of all sources to be removed ...")

        # Loop over all sources
        #for source in self.sources:
        index = 0
        while index < len(self.sources):

            # Get the current source
            source = self.sources[index]

            # If these pixels are already masked by an overlapping source (e.g. saturation), remove this source,
            # otherwise the area will be messed up
            current_mask_cutout = self.mask[source.y_slice, source.x_slice]
            if current_mask_cutout.covers(source.mask):
                self.sources.pop(index)
                continue

            # Adapt the mask
            self.mask[source.y_slice, source.x_slice] += source.mask

            # Increment the index
            index += 1

    # -----------------------------------------------------------------

    def set_cross_contamination(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("For each source, checking which pixels in the neighborhood are contaminated by other sources ...")

        # Loop over all sources
        for source in self.sources:

            # Create the contamination mask for this source
            other_sources_mask = Mask.empty_like(source.cutout)
            other_sources_mask[source.background_mask] = self.mask[source.y_slice, source.x_slice][source.background_mask]
            source.contamination = other_sources_mask

    # -----------------------------------------------------------------

    def remove_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the frame over the masked pixels ...")

        nsources = len(self.sources)
        count = 0

        # Set principal ellipse for the source extraction animation
        if self.animation is not None: self.animation.principal_shape = self.principal_shape

        # Loop over all sources and remove them from the frame
        for source in self.sources:

            # Debugging
            log.debug("Estimating background and replacing the frame pixels of source " + str(count+1) + " of " + str(nsources) + " ...")

            # Check whether the source is in front of the principal galaxy
            #foreground = self.principal_mask.masks(source.center)
            if self.principal_mask is not None: foreground = masks.overlap(self.principal_mask[source.y_slice, source.x_slice], source.mask)
            else: foreground = False

            # Disable sigma-clipping for estimating background when the source is foreground to the principal galaxy (to avoid clipping the galaxy's gradient)
            sigma_clip = self.config.sigma_clip if not foreground else False

            # Debugging
            log.debug("Sigma-clipping enabled for estimating background gradient for this source" if sigma_clip else "Sigma-clipping disabled for estimating background gradient for this source")

            # If these pixels are already replaced by an overlapping source (e.g. saturation), skip this source,
            # otherwise the area will be messed up
            #current_mask_cutout = self.mask[source.y_slice, source.x_slice]
            #if current_mask_cutout.covers(source.mask):
            #    count += 1
            #    continue
            ## ==> this is now also done in create_mask

            # Estimate the background
            try:
                source.estimate_background(self.config.interpolation_method, sigma_clip=sigma_clip)
            except ValueError: # ValueError: zero-size array to reduction operation minimum which has no identity
                # in: limits = (np.min(known_points), np.max(known_points)) [inpaint_biharmonic]
                count += 1
                continue

            # Adapt the mask
            #self.mask[source.y_slice, source.x_slice] += source.mask # this is now done beforehand, in the create_mask function

            # Add frame to the animation
            if self.animation is not None and (self.principal_mask is None or self.principal_mask.masks(source.center)) and self.animation.nframes <= 20:
                self.animation.add_source(source)

            # Replace the pixels by the background
            source.background.replace(self.frame, where=source.mask)

            #if not sigma_clip:
            #    # source.plot()

            #    plotting.plot_removal(source.cutout, source.mask, source.background,
            #                          self.frame[source.y_slice, source.x_slice])

            count += 1

    # -----------------------------------------------------------------

    def fix_extreme_values(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fixing extreme values that were introduced during the interpolation steps ...")

        self.frame[self.frame < self.minimum_value] = self.minimum_value
        self.frame[self.frame > self.maximum_value] = self.maximum_value

    # -----------------------------------------------------------------

    def set_nans(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting original NaN-pixels back to NaN ...")

        # Set the NaN pixels to zero in the frame
        self.frame[self.nan_mask] = float("nan")

    # -----------------------------------------------------------------

    def write(self):

        """
        THis function ...
        :return:
        """

        # Inform the suer
        log.info("Writing ...")

        # Write the animation
        if self.animation is not None: self.write_animation()

        # Write the resulting frame
        self.write_frame()

        # Write the mask
        self.write_mask()

    # -----------------------------------------------------------------

    def write_animation(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the animation ...")

        # Save the animation
        path = fs.join(output_path, "animation.gif")
        self.animation.save(path)

    # -----------------------------------------------------------------

    def write_frame(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the result ...")

        # Determine the path to the resulting FITS file
        path = self.output_path_file(self.frame.name + ".fits")

        # Save the resulting image as a FITS file
        self.frame.save(path)

    # -----------------------------------------------------------------

    def write_mask(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the mask ...")

        # Determine the path to the mask
        path = self.output_path_file("mask.fits")

        # Save the total mask as a FITS file
        Frame(self.mask.astype(float)).save(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def principal_shape(self):

        """
        This function ...
        :return:
        """

        if self.galaxy_region is None: return None

        largest_shape = None

        # Loop over all the shapes in the galaxy region
        for shape in self.galaxy_region:

            # Skip single coordinates
            if isinstance(shape, PixelCoordinate): continue

            if "principal" in shape.meta["text"]: return shape

            if not isinstance(shape, PixelEllipseRegion): return shape

            major_axis_length = shape.major
            if largest_shape is None or major_axis_length > largest_shape.major: largest_shape = shape

        # Return the largest shape
        return largest_shape

    # -----------------------------------------------------------------

    @lazyproperty
    def principal_mask(self):

        """
        This function ...
        :return:
        """

        if self.principal_shape is None: return None
        return self.principal_shape.to_mask(self.frame.xsize, self.frame.ysize)

# -----------------------------------------------------------------
