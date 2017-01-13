#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.core.mask Contains the Mask class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import astronomical modules
from astropy.io import fits

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ..basics.mask import MaskBase

# -----------------------------------------------------------------

class Mask(MaskBase):
    
    """
    This class ...
    """

    def __init__(self, data, **kwargs):

        """
        The constructor ...
        :param data:
        :param kwargs:
        """

        # Call the constructor of the base class
        super(Mask, self).__init__(data, **kwargs)

        # Set the WCS
        self.wcs = kwargs.pop("wcs", None)

        # The path
        self.path = None

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path, index=None, plane=None, hdulist_index=None):

        """
        This function ...
        :param path:
        :param index:
        :param plane:
        :param hdulist_index:
        :return:
        """

        name = None
        description = None
        no_filter = True
        fwhm = None
        add_meta = False

        from . import fits as pts_fits  # Import here because io imports SegmentationMap

        # PASS CLS TO ENSURE THIS CLASSMETHOD WORKS FOR ENHERITED CLASSES!!
        mask = pts_fits.load_frame(cls, path, index, name, description, plane, hdulist_index, no_filter, fwhm, add_meta=add_meta)

        # Set the path
        mask.path = path

        # Return the mask
        return mask

    # -----------------------------------------------------------------

    @property
    def header(self):

        """
        This function ...
        :return:
        """

        # If the WCS for this frame is defined, use it to create a header
        if self.wcs is not None: header = self.wcs.to_header()

        # Else, create a new empty header
        else: header = fits.Header()

        # Add properties to the header
        header['NAXIS'] = 2
        header['NAXIS1'] = self.xsize
        header['NAXIS2'] = self.ysize

        # Return the header
        return header

    # -----------------------------------------------------------------

    def save(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Saving the mask ...")

        # Check whether the path is valid
        if self.path is None: raise RuntimeError("Path is not defined")

        # Save
        self.saveto(self.path)

    # -----------------------------------------------------------------

    def saveto(self, path, header=None):

        """
        This function ...
        :param path:
        :param header:
        :return:
        """

        # If a header is not specified, created it from the WCS
        if header is None: header = self.header

        # FITS format
        if path.endswith(".fits"):

            from .fits import write_frame  # Import here because io imports Mask

            # Write to a FITS file
            write_frame(self._data.astype(int), header, path)

        # ASDF format
        elif path.endswith(".asdf"):

            # Import
            from asdf import AsdfFile

            # Create the tree
            tree = dict()

            tree["data"] = self._data
            tree["header"] = header

            # Create the asdf file
            ff = AsdfFile(tree)

            # Write
            ff.write_to(path)

        # Only FITS or ASDF format is allowed
        else: raise ValueError("Only the FITS or ASDF filetypes are supported")

        # Update the path
        self.path = path

# -----------------------------------------------------------------

def union(*args):

    """
    This function ...
    :param args:
    :return:
    """

    arrays = [arg.data for arg in args]
    return Mask(np.sum(arrays, axis=0))

# -----------------------------------------------------------------

def intersection(*args):

    """
    This function ...
    :param args:
    :return:
    """

    arrays = [arg.data for arg in args]
    return Mask(np.product(arrays, axis=0))

# -----------------------------------------------------------------
