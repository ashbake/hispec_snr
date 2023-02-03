##############################################################
# General functions for calc_snr_max
###############################################################

import numpy as np
from scipy import interpolate

from astropy.modeling.blackbody import blackbody_lambda, blackbody_nu
from astropy import units as u
from astropy import constants as c 

from throughput_tools import get_emissivity, get_emissivities

all = {'get_sky_bg','get_inst_bg','sum_total_noise','plot_noise_components'}

def get_sky_bg(x,airmass=1.5,pwv=1.5,npix=3,lam0=2000,R=100000,diam=10,area=76,skypath = '../../../../_DATA/sky/'):
    """
    generate sky background per pixel, default to HIPSEC. Source: DMawet jup. notebook

    inputs:
    -------

    outputs:
    --------
    sky background (ph/s)
    """
    diam *= u.m
    area = area * u.m * u.m
    wave=x*u.nm

    fwhm = ((wave  / diam) * u.radian).to(u.arcsec)
    solidangle = fwhm**2 * 1.13 #corrected for Gaussian beam (factor 1.13)

    sky_background_MK_tmp  = np.genfromtxt(skypath+'mk_skybg_zm_'+str(pwv)+'_'+str(airmass)+'_ph.dat', skip_header=0)
    sky_background_MK      = sky_background_MK_tmp[:,1]
    sky_background_MK_wave = sky_background_MK_tmp[:,0] #* u.nm

    pix_width_nm  = (wave/R/npix) #* u.nm 
    sky_background_interp=np.interp(wave.value, sky_background_MK_wave, sky_background_MK) * u.photon/(u.s*u.arcsec**2*u.nm*u.m**2) * area * solidangle * pix_width_nm 

    return sky_background_interp.value # ph/s

def get_inst_bg(x,npix=3,lam0=2000,R=100000,diam=10,area=76):
    """
    generate sky background per pixel, default to HIPSEC. Source: DMawet jup. notebook

    inputs:
    -------

    outputs:
    --------
    sky background (photons/s) already considering PSF sampling

    """
    em_red,em_blue, temps = get_emissivity(x)

    # telescope
    diam *= u.m
    area *= u.m * u.m
    lam0 *= u.nm
    wave = x*u.nm

    fwhm = ((wave  / diam) * u.radian).to(u.arcsec)
    solidangle = fwhm**2 * 1.13 #corrected for Gaussian beam (factor 1.13)
    pix_width_nm  = (wave/R/npix) #* u.nm 

    # step through temperatures and emissivities for red and blue
    # red
    for i,temp in enumerate(temps):
        bbtemp = blackbody_lambda(wave, temp).to(u.erg/(u.micron * u.s * u.cm**2 * u.arcsec**2)) * area.to(u.cm**2) * solidangle
        if i==0:
            tel_thermal_red  = em_red[i] * bbtemp.to(u.photon/u.s/u.micron, equivalencies=u.spectral_density(wave)) * pix_width_nm
            tel_thermal_blue = em_blue[i] * bbtemp.to(u.photon/u.s/u.micron, equivalencies=u.spectral_density(wave)) * pix_width_nm
        else:
            therm_red_temp   = em_red[i] * bbtemp.to(u.photon/u.s/u.micron, equivalencies=u.spectral_density(wave)) * pix_width_nm
            therm_blue_temp  = em_blue[i] * bbtemp.to(u.photon/u.s/u.micron, equivalencies=u.spectral_density(wave)) * pix_width_nm
            tel_thermal_red+= therm_red_temp
            tel_thermal_blue+= therm_blue_temp

    # interpolate and combine into one thermal spectrum
    isubred = np.where(wave > 1.4*u.um)[0]
    em_red_tot  = tel_thermal_red[isubred].decompose()
    isubblue = np.where(wave <1.4*u.um)[0]
    em_blue_tot  = tel_thermal_blue[isubblue].decompose()

    w = np.concatenate([x[isubblue],x[isubred]])
    s = np.concatenate([em_blue_tot,em_red_tot])

    tck        = interpolate.splrep(w,s.value, k=2, s=0)
    em_total   = interpolate.splev(x,tck,der=0,ext=1)

    return em_total # units of ph/s/pix

def get_sky_bg_tracking(x,fwhm,airmass=1.5,pwv=1.5,area=76,skypath = '../../../../_DATA/sky/'):
    """
    generate sky background per pixel, default to HIPSEC. Source: DMawet jup. notebook

    inputs:
    -------
    fwhm: arcsec

    outputs:
    --------
    sky background (ph/s)
    """
    area = area * u.m * u.m
    wave=x*u.nm

    fwhm *= u.arcsec
    solidangle = fwhm**2 * 1.13 #corrected for Gaussian beam (factor 1.13)

    sky_background_MK_tmp  = np.genfromtxt(skypath+'mk_skybg_zm_'+str(pwv)+'_'+str(airmass)+'_ph.dat', skip_header=0)
    sky_background_MK      = sky_background_MK_tmp[:,1] * u.photon/(u.s*u.arcsec**2*u.nm*u.m**2) 
    sky_background_MK_wave = sky_background_MK_tmp[:,0] * u.nm

    sky_background_interp=np.interp(wave, sky_background_MK_wave, sky_background_MK)
    sky_background_interp*= area * solidangle 
    
    return sky_background_interp.value # ph/s/nm

def get_inst_bg_tracking(x,fwhm,area=76):
    """
    generate sky background per pixel, default to HIPSEC. Source: DMawet jup. notebook
    change this to take emissivities and temps as inputs so dont
    have to rely on get_emissivities

    inputs:
    -------

    outputs:
    --------
    sky background (photons/s) already considering PSF sampling

    """
    temps = [276,276,276]
    em = get_emissivities(x,surfaces=['tel','ao','feicom'])

    # telescope
    area *= u.m * u.m
    wave = x*u.nm

    fwhm *= u.arcsec
    solidangle = fwhm**2 * 1.13 #corrected for Gaussian beam (factor 1.13)
    
    # step through temperatures and emissivities for red and blue
    # red
    for i,temp in enumerate(temps):
        bbtemp = solidangle * blackbody_lambda(wave, temp).to(u.erg/(u.nm * u.s * u.cm**2 * u.arcsec**2)) * area.to(u.cm**2) 
        if i==0:
            tel_thermal = em[i] * bbtemp.to(u.photon/u.s/u.nm, equivalencies=u.spectral_density(wave)) 
        else:
            therm_temp   = em[i] * bbtemp.to(u.photon/u.s/u.nm, equivalencies=u.spectral_density(wave)) 
            tel_thermal += therm_temp

    return tel_thermal.value # units of ph/nm/s

def sum_total_noise(flux,texp, nramp, inst_bg, sky_bg,darknoise,readnoise,npix):
    """
    noise in 1 exposure

    inputs:
    --------
    flux - array [e-] 
        spectrum of star in units of electrons
    texp - float [seconds]
        exposure time, (0s,900s] (for one frame)
    nramp - int
        number of ramps which will reduce read noise [1,inf] - 16 max for kpic
    inst_bg - array or float [e-/s]
        instrument background, if array should match sampling of flux
    sky_bg - array or float [e-/s]
        sky background, if array should match sampling of flux
    darknoise - float [e-/s/pix]
        dark noise of detector
    readnoise - float [e-/s]
        read noise of detector
    npix - float [pixels]
        number of pixels in cross dispersion of spectrum being combined into one 1D spectrum

    outputs:
    -------
    noise: array [e-]
        total noise sampled on flux grid
    """
    # shot noise - array w/ wavelength or integrated over band
    sig_flux = np.sqrt(flux)

    # background (instrument and sky) - array w/ wavelength matching flux array sampling or integrated over band
    total_bg = (inst_bg + sky_bg)
    sig_bg   = np.sqrt(inst_bg + sky_bg) 

    # read noise  - reduces by number of ramps
    sig_read = np.max((6,(readnoise/np.sqrt(nramp))))
    
    # dark current - times time and pixels
    sig_dark = np.sqrt(nramp * darknoise * npix) #* get dark noise every sample
    
    noise = np.sqrt(sig_flux **2 + sig_bg**2 + sig_read**2 + sig_dark**2)

    return noise

def read_noise(rn,npix):
    """
    input:
    ------
    rn: [e-/pix]
        read noise
    npix [pix]
        number of pixels
    """
    return np.sqrt(npix * rn**2)



def plot_noise_components():
    """
    plot spectra and transmission so know what we're dealing with
    """
    plt.figure()
    plt.plot(so.stel.v,so.hispec.ytransmit)


