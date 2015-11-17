#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package eagle.makeinfofile Creating information files with statistics on EAGLE SKIRT-runs.
#
# The main function in this module creates an information file with statistics on the results of an EAGLE SKIRT-run.
# The information file has a simple text format and includes statistics on the data exported from the EAGLE snapshot
# (i.e. the input data for the SKIRT simulation), on the SKIRT setup (such as the dust grid), and on the results
# of the SKIRT simulation (such as fluxes in various bands).

# -----------------------------------------------------------------

import os.path
import numpy as np
import pyfits
from scipy.ndimage.filters import gaussian_filter
import pts.archive as arch
from pts.filter import Filter

# -----------------------------------------------------------------

# private list of standard filters for which integrated fluxes should be calculated
_filterspecs = ( \
                "GALEX.FUV","GALEX.NUV",
                "MCPS.U","MCPS.B","MCPS.V","MCPS.I",
                "SDSS.u","SDSS.g","SDSS.r","SDSS.i","SDSS.z",
                "UKIDSS.Z","UKIDSS.Y","UKIDSS.J","UKIDSS.H","UKIDSS.K",
                "2MASS.J", "2MASS.H", "2MASS.K",
                "IRAS.12","IRAS.25","IRAS.60","IRAS.100",
                "IRAC.I1","IRAC.I2","IRAC.I3","IRAC.I4",
                "MIPS.24", "MIPS.70", "MIPS.160",
                "WISE.W1", "WISE.W2", "WISE.W3", "WISE.W4",
                "Pacs.blue","Pacs.green","Pacs.red",
                "SPIRE.PSW","SPIRE.PMW","SPIRE.PLW",
                )

# private list of uniform filters for which integrated fluxes should be calculated;
# for each filter, specify the filter spec and the wavelength range in micron)
_uniformfilters = ( ("Uniform_8_1000",8,1000), )

# private global dictionary to hold filter objects: (key,value) = (filterspec, Filter object)
_filters = { }

## This private function ensures that the filters relevant for this module are loaded into the private global
# dictionary \em _filters, using the filter specification string as a key and the corresponding Filter instance
# as a value. When the function is called for the first time, it creates the Filter objects and stores them
# in the dictionary. Once the dictionary has been loaded, subsequent invocations of the function don't do anything.
def _loadfilters():
    if len(_filters) == 0:
        # standard filters
        for filterspec in _filterspecs:
            _filters[filterspec] = Filter(filterspec)
        # uniform filters
        for filterspec,wavemin,wavemax in _uniformfilters:
            _filters[filterspec] = Filter((wavemin,wavemax))

# -----------------------------------------------------------------

# This function creates an information file with statistics on the results of an EAGLE SKIRT-run.
# The information file has a simple text format and includes statistics on the data exported from the EAGLE snapshot
# (i.e. the input data for the SKIRT simulation), on the SKIRT setup (such as the dust grid), and on the results
# of the SKIRT simulation (such as fluxes in various bands).
#
# The information file is placed in the simulation's output directory, and is named "prefix_info.txt".
#
def makeinfofile(skirtrun):
    simulation = skirtrun.simulation()

    # the info dict that will be saved at the end
    info = { }
    info["skirt_run_id"] = skirtrun.runid()

    # load statistics on the EAGLE data from the info file in the input folder
    inpath = skirtrun.inpath()
    infile = arch.listdir(inpath, "_info.txt")[0]
    for line in arch.opentext(os.path.join(inpath,infile)):
        if not line.startswith("#"):
            segments = line.split()
            info[segments[0]] = float(segments[2])

    # gather SKIRT setup statistics
    info["setup_mass_dust"] = simulation.dustmass()
    info["setup_mass_dust_grid"] = simulation.dustgridmass()
    info["setup_mass_cold_gas"] = simulation.coldgasmass()
    info["setup_particles_cold_gas"] = simulation.coldgasparticles()
    info["setup_mass_metallic_gas"] = simulation.metallicgasmass()
    info["setup_initial_mass_stars"] = simulation.initialstellarmass()
    info["setup_mass_hii_regions"] = simulation.hiiregionmass()
    info["setup_luminosity_stars"] = simulation.stellarluminosity()
    info["setup_luminosity_hii_regions"] = simulation.hiiregionluminosity()
    info["setup_cells_dust_grid"], info["setup_optical_depth_maximum"], \
        info["setup_optical_depth_percentile90"] = map(float,simulation.dustcellstats())
    distance = simulation.instrumentdistance()
    info["setup_distance_instrument"] = distance

    # load filters and wavelength grid
    _loadfilters()
    wavelengths = simulation.wavelengths()
    # create a mask that removes the carbon line emission peaks from the dust continuum emission
    cmask = (np.abs(wavelengths-157.5)>3) & (np.abs(wavelengths-360)>20) & (np.abs(wavelengths-600)>20)

    # define properties for the Herschel instruments used in determining dust temperature
    h_filterspecs = ("Pacs.red","SPIRE.PSW","SPIRE.PMW","SPIRE.PLW")
    # --> beam FWHM & area for PACS from Herschel PACS observer's manual, July 2013
    # --> beam FWHM & area for SPIRE from Ciesla et al. 2012, A&A 543, A161
    h_beam_fwhms = (12, 18.2, 24.5, 36.0)       # in arcsec
    h_beam_areas = (180, 423, 751, 1587)        # in arcsec^2
    # --> flux limit for PACS = noise level from Cortese et al. 2014
    # --> flux limit for SPIRE = confusion noise from Nguyen et al. 2010 A&A 518, L5
    h_flux_limits = (5, 5.8, 6.3, 6.8)          # in mJy/beam
    # --> convert to MJy/sr
    h_flux_limits = np.array(h_flux_limits) / np.array(h_beam_areas) * (648000/np.pi)**2 * 1e-9

    # gather statistics on fluxes received by each instrument
    for name in simulation.instrumentnames():
        # maximum flux in Jy
        fluxdensities = simulation.fluxdensities(name, unit='Jy')
        info["instr_"+name+"_fluxdensity_maximum"] = fluxdensities.max()

        # get flux densities per unit of wavelength because filter.convolve() requires this
        fluxdensities = simulation.fluxdensities(name, unit='W/m2/micron')

        # integrated flux density and absolute magnitude for each filter
        for filterspec,filterobject in _filters.iteritems():
            fluxdensity = filterobject.convolve(wavelengths, fluxdensities)
            fluxdensity = simulation.convert(fluxdensity, from_unit='W/m2/micron', to_unit='Jy',
                                             wavelength=filterobject.pivotwavelength())
            magnitude = simulation.absolutemagnitude(fluxdensity, distance,
                                                     fluxdensity_unit='Jy', distance_unit='pc')
            filtername = filterspec.replace(".","_").lower()
            info["instr_"+name+"_fluxdensity_"+filtername] = fluxdensity
            info["instr_"+name+"_magnitude_"+filtername] = magnitude

        # for the Herschel filters, calculate flux and magnitude excluding the carbon line emission peaks
        for filterspec in ("Pacs.blue","Pacs.green","Pacs.red","SPIRE.PSW","SPIRE.PMW","SPIRE.PLW"):
            filterobject = _filters[filterspec]
            fluxdensity = filterobject.convolve(wavelengths[cmask], fluxdensities[cmask])
            fluxdensity = simulation.convert(fluxdensity, from_unit='W/m2/micron', to_unit='Jy',
                                             wavelength=filterobject.pivotwavelength())
            magnitude = simulation.absolutemagnitude(fluxdensity, distance, fluxdensity_unit='Jy', distance_unit='pc')
            filtername = filterspec.replace(".","_").lower()
            info["instr_"+name+"_fluxdensity_"+filtername+"_continuum"] = fluxdensity
            info["instr_"+name+"_magnitude_"+filtername+"_continuum"] = magnitude

        # for the Herschel filters used in determining dust temperature, calculate the "limited" flux and magnitude
        # (i.e. ignoring pixels with a flux under a specific limit, and still excluding the carbon line emission peaks)
        for filterspec,fwhm,fluxlimit in zip(h_filterspecs, h_beam_fwhms, h_flux_limits):
            fluxdensity = limitedfluxdensity(simulation, name, wavelengths, cmask, _filters[filterspec], fwhm, fluxlimit)
            if fluxdensity != None:
                magnitude = simulation.absolutemagnitude(fluxdensity, distance, fluxdensity_unit='Jy', distance_unit='pc')
                filtername = filterspec.replace(".","_").lower()
                info["instr_"+name+"_fluxdensity_"+filtername+"_limited"] = fluxdensity
                info["instr_"+name+"_magnitude_"+filtername+"_limited"] = magnitude

    # estimate a representative temperature and corresponding standard deviation
    info["probe_average_temperature_dust"], info["probe_stddev_temperature_dust"],  \
    info["probe_skew_temperature_dust"], info["probe_kurtosis_temperature_dust"] = dusttemperature(simulation)

    # save the info file
    infofilepath = simulation.outfilepath("info.txt")
    infofile = open(infofilepath, 'w')
    infofile.write('# Information file for SKIRT-run {}\n'.format(skirtrun.runid()))
    infofile.write('# cells : 1\n')
    infofile.write('# particles : 1\n')
    infofile.write('# luminosity : Lsun\n')
    infofile.write('# mass : Msun\n')
    infofile.write('# distance : pc\n')
    infofile.write('# fluxdensity : Jy\n')
    infofile.write('# temperature : K\n')
    infofile.write('# magnitude : dex\n')
    maxkeylen = max(map(len,info.keys()))
    for key in sorted(info.keys()):
        valueformat = ".0f" if "_particles_" in key or "_cells_" in key or "run_id" in key else ".9e"
        infofile.write( ("{0:"+str(maxkeylen)+"} = {1:16"+valueformat+"}\n").format(key, info[key]) )
    infofile.close()

    # report success
    print "Created info file " + infofilepath

# -----------------------------------------------------------------

# Calculate and return statistics for the indicative temperature (weighted by mass) as a tuple:
#  (average, standard deviation, skew, excess curtosis).
# The data is extracted from the <prefix>_ds_celltemps.dat file generated by SKIRT.
# If this file is not present, the procedure fails.
def dusttemperature(simulation):
    # load the mass and temperature data for all cells
    filepath = simulation.outfilepath("ds_celltemps.dat")
    M,T = np.loadtxt(arch.opentext(filepath), unpack=True)

    # if the galaxy contains dust, calculate and return the statistics
    Mtot =  M.sum()
    if Mtot > 0:
        Tavg = np.average(T, weights=M)
        Tstd = np.sqrt( (M*((T-Tavg)**2)).sum()/Mtot )
        skew = (M*((T-Tavg)**3)).sum()/Mtot/ Tstd**3
        kurtosis = (M*((T-Tavg)**4)).sum()/Mtot/ Tstd**4 - 3
        return ( Tavg, Tstd, skew, kurtosis )

    # otherwise return dummy values
    else:
        return ( 0, 0, 0, 0 )

# -----------------------------------------------------------------

# This function calculates and returns the "limited" flux density (in Jy) in a given band
# based on the data cube of a particular instrument. The function first convolves the data cube over
# the wavelengths of the specified filter to obtain an averaged image, then convolves the image with
# a Gaussion PSF, and finally integrates over the image ignoring any pixels with a value under the
# specified surface brightness limit.
#
# The function takes the following arguments:
#  - \em simulation: a SkirtSimulation instance representing the simulation for which to perform the calculation.
#  - \em instrumentname: the name of the instrument (as listed in the ski file) for which to perform the calculation.
#  - \em wavelengths: the simulation's wavelength grid (this could be retrieved from the simulation but happens to
#                     be available at the caller site already).
#  - \em cmask: a mask indicating the wavelengths to include/exclude in the convolution with the filter.
#  - \em filterobject: the filter defining the band for which to perform the convolution.
#  - \em fwhm: the FWHM of the Gaussion filter to be applied to the image, in arcsecs.
#  - \em fluxlimit: the min. surface brightness for a pixel to be included in the integration over the image, in MJy/sr.
#
def limitedfluxdensity(simulation, instrumentname, wavelengths, cmask, filterobject, fwhm, fluxlimit):

    # get the path for the data cube corresponding to this instrument
    fitspaths = filter(lambda fn: ("_"+instrumentname+"_") in fn, simulation.totalfitspaths())
    if len(fitspaths) != 1: return None

    # get the data cube and convert it to per-wavelength units
    cube = pyfits.getdata(arch.openbinary(fitspaths[0])).T
    cube = simulation.convert(cube, to_unit='W/m3/sr', quantity='surfacebrightness', wavelength=wavelengths)

    # convolve the data cube to a single frame, and convert back to per-frequency units
    frame = filterobject.convolve(wavelengths[cmask], cube[:,:,cmask])
    frame = simulation.convert(frame, from_unit='W/m3/sr', to_unit='MJy/sr', wavelength=filterobject.pivotwavelength())

    # convolve the frame with a Gaussian of the appropriate size
    pixelarea = simulation.angularpixelarea()   # in sr
    pixelwidth = np.sqrt(pixelarea)             # in radians
    pixelwidth = pixelwidth * 648000 / np.pi    # in arcsec
    frame = gaussian_filter(frame, sigma=fwhm/pixelwidth/2.35482, mode='constant')

    # integrate over the frame to obtain the total flux density and convert from MJy to Jy
    fluxdensity = frame[frame>fluxlimit].sum() * pixelarea * 1e6
    return fluxdensity

# -----------------------------------------------------------------
