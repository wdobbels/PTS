#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.maps.component Contains the MapsComponent class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from collections import defaultdict
from abc import ABCMeta, abstractproperty

# Import the relevant PTS classes and modules
from ..component.galaxy import GalaxyModelingComponent
from ...core.tools import filesystem as fs
from ...core.tools.logging import log
from ...magic.tools.colours import get_filters_for_colour
from ...magic.core.frame import Frame
from ...core.tools import types
from ...core.filter.filter import parse_filter
from ...magic.core.list import NamedFrameList
from ...core.tools.serialization import load_dict, write_dict

# -----------------------------------------------------------------

origins_filename = "origins.txt"

# -----------------------------------------------------------------

class MapsComponent(GalaxyModelingComponent):
    
    """
    This class...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(MapsComponent, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The maps
        self.maps = dict()
        self.error_maps = dict()

        # The origins
        self.origins = dict()

        # The paths to the maps
        self.paths = dict()

        # The current (already calculated) maps
        self.current_maps = dict()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(MapsComponent, self).setup(**kwargs)

    # -----------------------------------------------------------------

    @property
    def maps_colours_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_colours_path

    # -----------------------------------------------------------------

    @property
    def maps_ssfr_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_ssfr_path

    # -----------------------------------------------------------------

    @property
    def maps_tir_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_tir_path

    # -----------------------------------------------------------------

    @property
    def maps_attenuation_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_attenuation_path

    # -----------------------------------------------------------------

    @property
    def maps_old_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_old_path

    # -----------------------------------------------------------------

    @property
    def maps_young_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_young_path

    # -----------------------------------------------------------------

    @property
    def maps_ionizing_path(self):

        """
        This fucntion ...
        :return:
        """

        return self.environment.map_ionizing_path

    # -----------------------------------------------------------------

    @property
    def maps_dust_path(self):

        """
        This fucntion ...
        :return:
        """

        return self.environment.maps_dust_path

    # -----------------------------------------------------------------

    @property
    def maps_sub_paths(self):

        """
        This function ...
        :return: 
        """

        return [self.maps_colours_path, self.maps_ssfr_path, self.maps_tir_path, self.maps_attenuation_path, self.maps_old_path, self.maps_young_path, self.maps_ionizing_path, self.maps_dust_path]

    # -----------------------------------------------------------------

    @property
    def maps_sub_names(self):

        """
        This function ...
        :return: 
        """

        return [fs.name(path) for path in self.maps_sub_paths]

    # -----------------------------------------------------------------

    def get_origins_sub_name(self, name):

        """
        This function ...
        :param name:
        :return: 
        """

        # Determine path
        sub_path = fs.join(self.maps_path, name)
        if not fs.is_directory(sub_path): raise ValueError("Invalid name '" + name + "'")
        direct_origins_path = fs.join(sub_path, origins_filename)

        # No subdirectories
        if fs.is_file(direct_origins_path): origins = load_dict(direct_origins_path)

        # Subdirectories
        else:

            # Initialize
            origins = dict()

            # Loop over subdirectories
            for method_path, method_path in fs.directories_in_path(sub_path):

                origins_path = fs.join(method_path, origins_filename)
                if not fs.is_file(origins_path): raise ValueError("File '" + origins_path + "' is missing")

                # Load the origins
                origins[method_path] = load_dict(origins_path)

        # Return the origins
        return origins

    # -----------------------------------------------------------------

    def get_origins_sub_names(self):

        """
        This function ...
        :return: 
        """

        origins = dict()
        for name in self.maps_sub_names: origins[name] = self.get_origins_sub_name(name)
        return origins

    # -----------------------------------------------------------------

    @abstractproperty
    def maps_sub_path(self):

        """
        This function ...
        :return: 
        """

        pass

    # -----------------------------------------------------------------

    @property
    def maps_sub_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.maps_sub_path)

    # -----------------------------------------------------------------

    @property
    def colour_map_filters(self):

        """
        This function ...
        :return: 
        """

        filters = []

        # Loop over the images in the colour maps directory
        for path, name in fs.files_in_path(self.maps_colours_path, extension="fits", returns=["path", "name"]):

            # Get the filters
            fltr_a, fltr_b = get_filters_for_colour(name)

            # Add a tuple
            filters.append((fltr_a, fltr_b))

        # Return the list
        return filters

    # -----------------------------------------------------------------

    @property
    def colour_map_filters_and_paths(self):

        """
        This function ...
        :return: 
        """

        filters = dict()

        # Loop over the images in the colour maps directory
        for path, name in fs.files_in_path(self.maps_colours_path, extension="fits", returns=["path", "name"]):

            # Get the filters
            fltr_a, fltr_b = get_filters_for_colour(name)

            # Add
            filters[(fltr_a, fltr_b)] = path

        # Return the dictionary
        return filters

    # -----------------------------------------------------------------

    def has_colour_map_for_filters(self, fltr_a, fltr_b):

        """
        This function ...
        :param fltr_a: 
        :param fltr_b: 
        :return: 
        """

        # Loop over the filters of the existing colour maps
        for fltr_ai, fltr_bi in self.colour_map_filters:

            if (fltr_ai, fltr_bi) == (fltr_a, fltr_b): return True
            if (fltr_bi, fltr_ai) == (fltr_a, fltr_b): return True

        # No colour map encountered
        return False

    # -----------------------------------------------------------------

    def get_colour_map_for_filters(self, fltr_a, fltr_b):

        """
        This function ...
        :param fltr_a: 
        :param fltr_b: 
        :return: 
        """

        # Loop over the existing colour maps
        filters = self.colour_map_filters_and_paths
        for fltr_ai, fltr_bi in filters:

            # Get the path
            path = filters[(fltr_ai, fltr_bi)]

            # Check colours
            if (fltr_ai, fltr_bi) == (fltr_a, fltr_b): return Frame.from_file(path)
            if (fltr_bi, fltr_ai) == (fltr_a, fltr_b): return -1. * Frame.from_file(path)

        # No colour map encountered
        return None

    # -----------------------------------------------------------------

    def has_frame_for_filter(self, fltr):

        """
        This function ...
        :param fltr: 
        :return: 
        """

        return self.dataset.has_frame_for_filter(fltr)

    # -----------------------------------------------------------------

    def get_frame_for_filter(self, fltr):

        """
        THis function ...
        :param fltr: 
        :return: 
        """

        return self.dataset.get_frame_for_filter(fltr)

    # -----------------------------------------------------------------

    def has_errormap_for_filter(self, fltr):

        """
        This function ...
        :param fltr: 
        :return: 
        """

        return self.dataset.has_errormap_for_filter(fltr)

    # -----------------------------------------------------------------

    def get_errormap_for_filter(self, fltr):

        """
        This function ...
        :param fltr: 
        :return: 
        """

        return self.dataset.get_errormap_for_filter(fltr)

    # -----------------------------------------------------------------

    def get_ssfr_maps(self):

        """
        This function ...
        :return: 
        """

        return NamedFrameList.from_directory(self.maps_ssfr_path).to_dictionary()

    # -----------------------------------------------------------------

    def get_ssfr_origins(self):

        """
        This function ...
        :return: 
        """

        origins_path = fs.join(self.maps_ssfr_path, origins_filename)
        return load_dict(origins_path)

    # -----------------------------------------------------------------

    def get_tir_maps(self):

        """
        This function ...
        :return: 
        """

        single = self.get_tir_single_maps()
        multi = self.get_tir_multi_maps()

        maps = dict()
        for name in single: maps["single_" + name] = single[name]
        for name in multi: maps["multi_" + name] = multi[name]
        return maps

    # -----------------------------------------------------------------

    def get_tir_single_maps(self):

        """
        This function ...
        :return: 
        """

        path = fs.join(self.maps_tir_path, "single")
        return NamedFrameList.from_directory(path).to_dictionary()

    # -----------------------------------------------------------------

    def get_tir_multi_maps(self):

        """
        This function ...
        :return: 
        """

        path = fs.join(self.maps_tir_path, "multi")
        return NamedFrameList.from_directory(path).to_dictionary()

    # -----------------------------------------------------------------

    def get_tir_origins(self):

        """
        This function ...
        :return: 
        """

        single = self.get_tir_single_origins()
        multi = self.get_tir_multi_origins()

        origins = dict()
        for name in single: origins["single_" + name] = single[name]
        for name in multi: origins["multi_" + name] = multi[name]
        return origins

    # -----------------------------------------------------------------

    def get_tir_single_origins(self):

        """
        This function ...
        :return: 
        """

        path = fs.join(self.maps_tir_path, "single", origins_filename)
        return load_dict(path)

    # -----------------------------------------------------------------

    def get_tir_multi_origins(self):

        """
        This function ...
        :return: 
        """

        path = fs.join(self.maps_tir_path, "multi", origins_filename)
        return load_dict(path)

    # -----------------------------------------------------------------

    def get_fuv_attenuation_maps(self):

        """
        This function ...
        :return: 
        """

        cortese = self.get_cortese_fuv_attenuation_maps()
        buat = self.get_buat_fuv_attenuation_maps()

        maps = dict()
        for name in cortese: maps["cortese_" + name] = cortese[name]
        for name in buat: maps["buat_" + name] = buat[name]
        return maps

    # -----------------------------------------------------------------

    def get_fuv_attenuation_origins(self):

        """
        This function ...
        :return: 
        """

        cortese = self.get_cortese_fuv_attenuation_origins()
        buat = self.get_buat_fuv_attenuation_origins()

        origins = dict()
        for name in cortese: origins["cortese_" + name] = cortese[name]
        for name in buat: origins["cortese_" + name] = buat[name]
        return origins

    # -----------------------------------------------------------------

    def get_buat_fuv_attenuation_maps(self):

        """
        This function ...
        :return: 
        """

        buat_path = fs.join(self.maps_attenuation_path, "buat")
        return NamedFrameList.from_directory(buat_path, contains="FUV").to_dictionary()

    # -----------------------------------------------------------------

    def get_cortese_fuv_attenuation_maps(self):

        """
        This function ...
        :return: 
        """

        cortese_path = fs.join(self.maps_attenuation_path, "cortese")
        return NamedFrameList.from_directory(cortese_path).to_dictionary()

    # -----------------------------------------------------------------

    def get_buat_fuv_attenuation_origins(self):

        """
        This function ...
        :return: 
        """

        buat_path = fs.join(self.maps_attenuation_path, "buat")
        table_path = fs.join(buat_path, origins_filename)
        return load_dict(table_path)

    # -----------------------------------------------------------------

    def get_cortese_fuv_attenuation_origins(self):

        """
        This function ...
        :return: 
        """

        cortese_path = fs.join(self.maps_attenuation_path, "cortese")
        table_path = fs.join(cortese_path, origins_filename)
        return load_dict(table_path)

    # -----------------------------------------------------------------

    def get_old_stellar_disk_map(self, fltr):

        """
        This fucntion ...
        :param fltr:
        :return: 
        """

        if types.is_string_type(fltr): fltr = parse_filter(fltr)

        path = fs.join(self.maps_old_path, "disk", str(fltr) + ".fits")
        return Frame.from_file(path)

    # -----------------------------------------------------------------

    def get_hot_dust_maps(self):

        """
        This function ...
        :return: 
        """

        hot_dust_path = fs.join(self.maps_dust_path, "hot")
        return NamedFrameList.from_directory(hot_dust_path).to_dictionary()

    # -----------------------------------------------------------------

    def get_hot_dust_origins(self):

        """
        This function ...
        :return: 
        """

        hot_dust_path = fs.join(self.maps_dust_path, "hot")
        origins_path = fs.join(hot_dust_path, origins_filename)
        return load_dict(origins_path)

    # -----------------------------------------------------------------

    def get_current_origins(self):

        """
        This function ...
        :return:
        """

        return self.get_origins_sub_name(self.maps_sub_name)

    # -----------------------------------------------------------------

    def get_current_map_paths(self):

        """
        This function ...
        :return:
        """

        # Subdirectories
        if fs.contains_directories(self.maps_sub_path):

            paths = dict()

            # Loop over the subdirectories
            for method_path, method in fs.directories_in_path(self.maps_sub_path, returns=["path", "name"]):

                # Set the map paths, as a dictionary with the filename as keys
                paths[method] = fs.files_in_path(method_path, returns="dict")

        # Files present
        elif fs.contains_files(self.maps_sub_path): return fs.files_in_path(self.maps_sub_path, returns="dict")

        # Nothing present
        else: return dict()

    # -----------------------------------------------------------------

    def get_current_maps(self):

        """
        This function ...
        :return:
        """

        # Initialize the maps dictionary
        maps = dict()

        paths = self.get_current_map_paths()

        # Loop over the entries
        for method_or_name in paths:

            # Methods
            if types.is_dictionary(paths[method_or_name]):

                method = method_or_name
                maps[method] = dict()

                # Loop over the paths, load the maps and add to dictionary
                for name in paths[method_or_name]: maps[method][name] = Frame.from_file(paths[method_or_name][name])

            # Just maps
            elif types.is_string_type(paths[method_or_name]):

                name = method_or_name
                maps[name] = Frame.from_file(paths[method_or_name])

            # Something wrong
            else: raise RuntimeError("Something went wrong")

        # Return the maps
        return maps

    # -----------------------------------------------------------------

    def get_path_for_map(self, name, method=None):

        """
        This function ...
        :return:
        """

        # Subdivided into methods
        if method is not None:

            # Create directory, if necessary
            if not fs.contains_directory(self.maps_sub_path, method): path = fs.create_directory_in(self.maps_sub_path, method)
            else: path = fs.join(self.maps_sub_path, method)

            # Determine path
            map_path = fs.join(path, name + ".fits")

        # Determine path
        else: map_path = fs.join(self.maps_sub_path, name + ".fits")

        # Return the map path
        return map_path

    # -----------------------------------------------------------------

    def write_maps(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Writing the maps ...")

        # Loop over the methods
        for method in self.maps:

            # Depending on whether subdictionaries
            if types.is_dictionary(self.maps[method]):

                # Create directory
                #path = fs.create_directory_in(self.maps_sub_path, method)

                # Loop over the maps
                for name in self.maps[method]:

                    # Determine path
                    #map_path = fs.join(path, name + ".fits")

                    map_path = self.get_path_for_map(name, method)

                    if fs.is_file(map_path): continue

                    # Save
                    self.maps[method][name].saveto(map_path)

            # No different methods
            else:

                # Determine path
                #map_path = fs.join(self.maps_sub_path, method + ".fits")

                map_path = self.get_path_for_map(method)

                if fs.is_file(map_path): continue

                # Save
                self.maps[method].saveto(map_path)

    # -----------------------------------------------------------------

    #def write_error_maps(self):

        #"""
        #This function ...
        #:return:
        #"""

        # Inform the user
        #log.info("Writing the error maps (with different methods) ...")

        # Loop over the methods
        #for method in self.maps:

            # Create a directory
            #path = fs.create_directory_in(self.maps_dust_path, method)

            # Loop over the maps
            #for name in self.error_maps[method]:

                # Determine path
                #map_path = fs.join(path, name + "_error.fits")

                # Save the map
                #self.maps[method][name].saveto(map_path)

    # -----------------------------------------------------------------

    def write_origins(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Writing the maps ...")

        # Loop over the methods
        for method in self.origins:

            # Depending on whether subdictionaries
            if types.is_dictionary(self.maps[method]):

                # Directory path
                path = fs.join(self.maps_sub_path, method)

                # Origins path
                origins_path = fs.join(path, origins_filename)

                # Write
                write_dict(self.origins[method], origins_path)

            # No different methods
            else:

                # Determine the origins file path
                origins_path = fs.join(self.maps_sub_path, origins_filename)

                # Write
                write_dict(self.origins, origins_path)

# -----------------------------------------------------------------

def get_dust_maps_path(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.join(modeling_path, "maps", "dust")

# -----------------------------------------------------------------

def get_dust_map_names(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.files_in_path(get_dust_maps_path(modeling_path), extension="fits", returns="name")

# -----------------------------------------------------------------

def get_old_stars_maps_path(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.join(modeling_path, "maps", "old")

# -----------------------------------------------------------------

def get_old_stellar_map_names(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.files_in_path(get_old_stars_maps_path(modeling_path), extension="fits", returns="name")

# -----------------------------------------------------------------

def get_young_stars_maps_path(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.join(modeling_path, "maps", "young")

# -----------------------------------------------------------------

def get_young_stellar_map_names(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.files_in_path(get_young_stars_maps_path(modeling_path), extension="fits", returns="name")

# -----------------------------------------------------------------

def get_ionizing_stars_maps_path(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.join(modeling_path, "maps", "ionizing")

# -----------------------------------------------------------------

def get_ionizing_stellar_map_names(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return fs.files_in_path(get_ionizing_stars_maps_path(modeling_path), extension="fits", returns="name")

# -----------------------------------------------------------------
