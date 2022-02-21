import os

from astropy import constants as const
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
from matplotlib import colors
from matplotlib.patches import Ellipse
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm #, LogNorm
import numpy as np
from reproject import reproject_interp
from urllib.error import HTTPError

from modules.functions import get_info
from modules.functions import chan2freq, chan2vel, sbr2nhi
from modules.get_ancillary import *
from modules.get_hst_cosmos import get_hst_cosmos

HI_restfreq = 1420405751.77 * u.Hz
optical_HI = u.doppler_optical(HI_restfreq)


###################################################################

# Overlay HI contours on another image

def make_overlay(source, src_basename, cube_params, patch, opt, base_contour, suffix='png', survey='DSS2 Blue'):
    """Overlay HI contours on top of an optical image

    :param source: source object
    :type source: Astropy data object?
    :param src_basename: basename for the source for data files
    :type src_basename: str
    :param cube_params: parameters of the data cube
    :type cube_params: dict
    :param patch: observing patch parameters
    :type patch: dict
    :param opt: optical data
    :type opt: dict
    :param base_contour: base contour
    :type base_contour: float
    :param suffix: file type, defaults to 'png'
    :type suffix: str, optional
    :param survey: survey from which to use data, defaults to 'DSS2 Blue'
    :type survey: str, optional
    """
    survey_nospace = survey.replace(" ", "").lower()
    outfile = src_basename.replace('cubelets', 'figures') + '_{}_mom0{}.{}'.format(source['id'], survey_nospace, suffix)

    if not os.path.isfile(outfile):
        try:
            print("\tMaking {} overlaid with HI contours.".format(survey))
            hdulist_hi = fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id'])))
        except FileNotFoundError:
            print("\tNo mom0 fits file. Perhaps you ran SoFiA without generating moments?")
            return

        nhi19 = sbr2nhi(base_contour, hdulist_hi[0].header['bunit'], cube_params['bmaj'].value, cube_params['bmin'].value) / 1e+19
        nhi_label = "N_HI = {:.1f}, {:.1f}, {:.0f}, {:.0f}e+19".format(nhi19 * 1, nhi19 * 2, nhi19 * 4, nhi19 * 8)

        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111, projection=WCS(opt[0].header))
        if survey == 'hst':
            # ax1.imshow(opt[0].data, origin='lower', cmap='twilight', norm=LogNorm(vmax=5))
            # ax1.imshow(opt[0].data, origin='lower', cmap='Greys', norm=LogNorm(vmin=-0.003, vmax=30))
            ax1.imshow(opt[0].data, origin='lower', cmap='Greys',
                       norm=PowerNorm(gamma=0.25, vmin=np.percentile(opt[0].data, 20),
                                      vmax=np.percentile(opt[0].data, 99.5)))
        else:
            ax1.imshow(opt[0].data, cmap='viridis', vmin=np.percentile(opt[0].data, 10),
                       vmax=np.percentile(opt[0].data, 99.8), origin='lower')
        ax1.contour(hdulist_hi[0].data, cmap='Oranges', linewidths=1, levels=base_contour * 2 ** np.arange(10),
                    transform=ax1.get_transform(WCS(hdulist_hi[0].header)))
        ax1.scatter(source['ra'], source['dec'], marker='x', c='black', linewidth=0.75,
                    transform=ax1.get_transform('fk5'))
        ax1.set_title(source['name'], fontsize=20)
        ax1.tick_params(axis='both', which='major', labelsize=18)
        ax1.coords['ra'].set_axislabel('RA (ICRS)', fontsize=20)
        ax1.coords['dec'].set_axislabel('Dec (ICRS)', fontsize=20)
        ax1.text(0.5, 0.05, nhi_label, ha='center', va='center', transform=ax1.transAxes,
                  color='white', fontsize=18)
        ax1.add_patch(Ellipse((0.92, 0.9), height=patch['height'], width=patch['width'], angle=cube_params['bpa'],
                              transform=ax1.transAxes, edgecolor='white', linewidth=1))

        fig.savefig(outfile, bbox_inches='tight')

        hdulist_hi.close()

    else:
        print('\t{} already exists. Will not overwrite.'.format(outfile))

    return


# Make HI grey scale image
def make_mom0(source, src_basename, cube_params, patch, opt_head, base_contour, suffix='png'):

    outfile = src_basename.replace('cubelets', 'figures') + '_{}_mom0hi.{}'.format(source['id'], suffix)

    if not os.path.isfile(outfile):
        try:
            print("\tMaking HI grey scale map.")
            hdulist_hi = fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id'])))
        except FileNotFoundError:
            print("\tNo mom0 fits file. Perhaps you ran SoFiA without generating moments?")
            return

        hi_reprojected, footprint = reproject_interp(hdulist_hi, opt_head)

        nhi19 = sbr2nhi(base_contour, hdulist_hi[0].header['bunit'], cube_params['bmaj'].value, cube_params['bmin'].value) / 1e+19
        nhi_label = "N_HI = {:.1f}, {:.1f}, {:.0f}, {:.0f}e+19".format(nhi19 * 1, nhi19 * 2, nhi19 * 4, nhi19 * 8)

        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111, projection=WCS(opt_head))
        im = ax1.imshow(hi_reprojected, cmap='gray_r', origin='lower')
        ax1.set(facecolor="white")  # Doesn't work with the color im
        ax1.contour(hi_reprojected, cmap='Oranges_r', linewidths=1.2, levels=base_contour * 2 ** np.arange(10))
        ax1.scatter(source['ra'], source['dec'], marker='x', c='white', linewidth=0.75,
                    transform=ax1.get_transform('fk5'))
        ax1.set_title(source['name'], fontsize=20)
        ax1.tick_params(axis='both', which='major', labelsize=18)
        ax1.coords['ra'].set_axislabel('RA (ICRS)', fontsize=20)
        ax1.coords['dec'].set_axislabel('Dec (ICRS)', fontsize=20)
        ax1.text(0.5, 0.05, nhi_label, ha='center', va='center', transform=ax1.transAxes, fontsize=18)
        ax1.add_patch(Ellipse((0.92, 0.9), height=patch['height'], width=patch['width'], angle=cube_params['bpa'],
                              transform=ax1.transAxes, facecolor='darkorange', edgecolor='black', linewidth=1))
        cb_ax = fig.add_axes([0.91, 0.11, 0.02, 0.76])
        cbar = fig.colorbar(im, cax=cb_ax)
        cbar.set_label("HI Intensity [{}]".format(hdulist_hi[0].header['bunit']), fontsize=18)

        fig.savefig(outfile, bbox_inches='tight')

        hdulist_hi.close()

    else:
        print('\t{} already exists. Will not overwrite.'.format(outfile))

    return


# Make HI significance image
def make_snr(source, src_basename, cube_params, patch, opt_head, base_contour, suffix='png'):

    outfile = src_basename.replace('cubelets', 'figures') + '_{}_snr.{}'.format(source['id'], suffix)

    if not os.path.isfile(outfile):
        try:
            print("\tMaking pixel SNR map.")
            hdulist_snr = fits.open(src_basename + '_{}_snr.fits'.format(str(source['id'])))
        except FileNotFoundError:
            print("\tNo SNR fits file. Perhaps you ran SoFiA without generating moments?")
            return

        hdulist_hi = fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id'])))
        snr_reprojected, footprint = reproject_interp(hdulist_snr, opt_head)
        hi_reprojected, footprint = reproject_interp(hdulist_hi, opt_head)

        nhi19 = sbr2nhi(base_contour, hdulist_hi[0].header['bunit'], cube_params['bmaj'].value, cube_params['bmin'].value) / 1e+19

        wa_cmap = colors.ListedColormap(['w', 'royalblue', 'limegreen', 'yellow', 'orange', 'r'])
        boundaries = [0, 1, 2, 3, 4, 5, 6]
        norm = colors.BoundaryNorm(boundaries, wa_cmap.N, clip=True)
        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111, projection=WCS(opt_head))
        ax1.set(facecolor="white")  # Doesn't work with the color im
        im = ax1.imshow(snr_reprojected, cmap=wa_cmap, origin='lower', norm=norm)
        ax1.contour(hi_reprojected, linewidths=2, levels=[base_contour, ], colors=['k', ])
        ax1.scatter(source['ra'], source['dec'], marker='x', c='black', linewidth=0.75,
                    transform=ax1.get_transform('fk5'))
        ax1.set_title(source['name'], fontsize=20)
        ax1.tick_params(axis='both', which='major', labelsize=18)
        ax1.coords['ra'].set_axislabel('RA (ICRS)', fontsize=20)
        ax1.coords['dec'].set_axislabel('Dec (ICRS)', fontsize=20)
        ax1.text(0.5, 0.05, "N_HI = {:.1f}e+19".format(nhi19), ha='center', va='center',
                 transform=ax1.transAxes, fontsize=18)
        ax1.add_patch(Ellipse((0.92, 0.9), height=patch['height'], width=patch['width'], angle=cube_params['bpa'],
                              transform=ax1.transAxes, facecolor='gold', edgecolor='indigo', linewidth=1))
        cb_ax = fig.add_axes([0.91, 0.11, 0.02, 0.76])
        cbar = fig.colorbar(im, cax=cb_ax)
        cbar.set_label("Pixel SNR", fontsize=18)
        fig.savefig(outfile, bbox_inches='tight')
        hdulist_hi.close()

    else:
        print('\t{} already exists. Will not overwrite.'.format(outfile))

    return


# Make velocity map for object
def make_mom1(source, src_basename, cube_params, patch, opt_head, HIlowest, opt_view=6*u.arcmin, suffix='png', sofia=2):

    outfile = src_basename.replace('cubelets', 'figures') + '_{}_mom1.{}'.format(source['id'], suffix)

    if not os.path.isfile(outfile):

        try:
            print("\tMaking velocity map.")
            mom1 = fits.open(src_basename + '_{}_mom1.fits'.format(source['id']))
        except FileNotFoundError:
            print("\tNo mom1 fits file. Perhaps you ran SoFiA without generating moments?")
            return

        # Do some preparatory work depending on the units of the spectral axis on the input cube.
        convention = 'Optical'
        if 'freq' in source.colnames:
            # Convert moment map from Hz into units of km/s
            for i in range(mom1[0].data.shape[0]):
                for j in range(mom1[0].data.shape[1]):
                    mom1[0].data[i][j] = (mom1[0].data[i][j] * u.Hz).to(u.km / u.s, equivalencies=optical_HI).value
            # Calculate spectral quantities for plotting
            v_sys = (source['freq'] * u.Hz).to(u.km/u.s, equivalencies=optical_HI).value
            # Currently SoFiA-2 puts out frequency w20/w50 in Hz units (good)
            w50 = (const.c * source['w50'] * u.Hz / (source['freq'] * u.Hz)).to(u.km/u.s,
                                                                                equivalencies=optical_HI).value
            w20 = (const.c * source['w20'] * u.Hz / (source['freq'] * u.Hz)).to(u.km/u.s,
                                                                                equivalencies=optical_HI).value
            if sofia == 2:
                freqmin = chan2freq(source['z_min'], src_basename + '_{}_cube.fits'.format(source['id']))
                freqmax = chan2freq(source['z_max'], src_basename + '_{}_cube.fits'.format(source['id']))
            elif sofia == 1:
                freqmin = chan2freq(source['z_min'], src_basename + '_{}.fits'.format(source['id']))
                freqmax = chan2freq(source['z_max'], src_basename + '_{}.fits'.format(source['id']))
            velmax = freqmin.to(u.km / u.s, equivalencies=optical_HI).value + 5
            velmin = freqmax.to(u.km / u.s, equivalencies=optical_HI).value - 5
        else:
            # Convert moment map from m/s into units of km/s.
            for i in range(mom1[0].data.shape[0]):
                for j in range(mom1[0].data.shape[1]):
                    mom1[0].data[i][j] = (mom1[0].data[i][j] * u.m / u.s).to(u.km / u.s).value
            # Calculate spectral quantities for plotting
            v_sys = (source['v_col'] * u.m / u.s).to(u.km / u.s).value
            # SoFiA-2 puts out velocity w20/w50 in pixel units. https://github.com/SoFiA-Admin/SoFiA-2/issues/63
            w50 = (source['w50'] * cube_params['chan_width']).to(u.km / u.s).value
            w20 = (source['w20'] * cube_params['chan_width']).to(u.km / u.s).value
            velmin = chan2vel(source['z_min'], src_basename +
                              '_{}_cube.fits'.format(source['id'])).to(u.km / u.s).value + 5
            velmax = chan2vel(source['z_max'], src_basename +
                              '_{}_cube.fits'.format(source['id'])).to(u.km / u.s).value - 5
            if cube_params['spec_axis'] == 'VRAD': convention = 'Radio'

        mom1_reprojected, footprint = reproject_interp(mom1, opt_head)

        # Only plot values above the lowest calculated HI value:
        hdulist_hi = fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id'])))
        hi_reprojected, footprint = reproject_interp(hdulist_hi, opt_head)

        mom1_reprojected[hi_reprojected < HIlowest] = np.nan

        v_sys_label = "v_sys = {}   W_50 = {}  W_20 = {}".format(int(v_sys), int(w50), int(w20))
        hi_pos = SkyCoord(source['ra'], source['dec'], unit='deg')
        kinpa = source['kin_pa'] * u.deg

        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111, projection=WCS(opt_head))
        im = ax1.imshow(mom1_reprojected, cmap='RdBu_r', origin='lower')  #vmin=velmin, vmax=velmax, origin='lower')
        # ax1.contour(hi_reprojected, linewidths=1, levels=[sensitivity, ], colors=['k', ])
        if np.abs(velmax - velmin) > 200:
            levels = [v_sys - 100, v_sys - 50, v_sys, v_sys + 50, v_sys + 100]
            clevels = ['white', 'gray', 'black', 'gray', 'white']
        else:
            levels = [v_sys - 50, v_sys, v_sys + 50]
            clevels = ['lightgray', 'black', 'lightgray']
        ax1.contour(mom1_reprojected, colors=clevels, levels=levels, linewidths=0.6)
        # Plot HI center of galaxy
        ax1.scatter(source['ra'], source['dec'], marker='x', c='black', linewidth=0.75,
                    transform=ax1.get_transform('fk5'))
        ax1.plot([(hi_pos.ra + 0.5 * opt_view * np.sin(kinpa) / np.cos(hi_pos.dec)).deg,
                  (hi_pos.ra - 0.5 * opt_view * np.sin(kinpa) / np.cos(hi_pos.dec)).deg],
                 [(hi_pos.dec + 0.5 * opt_view * np.cos(kinpa)).deg,
                  (hi_pos.dec - 0.5 * opt_view * np.cos(kinpa)).deg],
                 c='black', linestyle='--', linewidth=0.75, transform=ax1.get_transform('icrs'))
        ax1.set_title(source['name'], fontsize=20)
        ax1.tick_params(axis='both', which='major', labelsize=18)
        ax1.coords['ra'].set_axislabel('RA (ICRS)', fontsize=20)
        ax1.coords['dec'].set_axislabel('Dec (ICRS)', fontsize=20)
        ax1.text(0.5, 0.05, v_sys_label, ha='center', va='center', transform=ax1.transAxes,
                 color='black', fontsize=18)
        ax1.add_patch(Ellipse((0.92, 0.9), height=patch['height'], width=patch['width'], angle=cube_params['bpa'],
                              transform=ax1.transAxes, edgecolor='darkred', linewidth=1))
        cb_ax = fig.add_axes([0.91, 0.11, 0.02, 0.76])
        cbar = fig.colorbar(im, cax=cb_ax)
        # cbar.set_label("Barycentric Optical Velocity [km/s]", fontsize=18)
        cbar.set_label("{} {} Velocity [km/s]".format(cube_params['spec_sys'].capitalize(), convention), fontsize=18)

        fig.savefig(outfile, bbox_inches='tight')

        mom1.close()

    else:
        print('\t{} already exists. Will not overwrite.'.format(outfile))

    return


# Overlay HI contours on false color optical image
def make_color_im(source, src_basename, cube_params, patch, color_im, opt_head, base_contour, suffix='png',
                   survey='panstarrs'):

    outfile = src_basename.replace('cubelets', 'figures') + '_{}_mom0{}.{}'.format(source['id'], survey, suffix)

    if survey == 'panstarrs': survey = 'PanSTARRS'
    elif survey == 'decals': survey = 'DECaLS'

    if not os.path.isfile(outfile):
        print("\tMaking {} image overlaid with HI contours.".format(survey))
        hdulist_hi = fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id'])))
        hi_reprojected, footprint = reproject_interp(hdulist_hi, opt_head)

        nhi19 = sbr2nhi(base_contour, hdulist_hi[0].header['bunit'], cube_params['bmaj'].value, cube_params['bmin'].value) / 1e+19
        nhi_label = "N_HI = {:.1f}, {:.1f}, {:.0f}, {:.0f}e+19".format(nhi19 * 1, nhi19 * 2, nhi19 * 4, nhi19 * 8)

        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111, projection=WCS(opt_head))
        # ax1.set_facecolor("darkgray")   # Doesn't work with the color im
        ax1.imshow(color_im, origin='lower')
        ax1.contour(hi_reprojected, cmap='Oranges', linewidths=1, levels=base_contour * 2 ** np.arange(10))
        ax1.scatter(source['ra'], source['dec'], marker='x', c='white', linewidth=0.75,
                    transform=ax1.get_transform('fk5'))
        ax1.set_title(source['name'], fontsize=20)
        ax1.tick_params(axis='both', which='major', labelsize=18)
        ax1.coords['ra'].set_axislabel('RA (ICRS)', fontsize=20)
        ax1.coords['dec'].set_axislabel('Dec (ICRS)', fontsize=20)
        ax1.text(0.5, 0.05, nhi_label, ha='center', va='center', transform=ax1.transAxes,
                 color='white', fontsize=18)
        ax1.add_patch(Ellipse((0.92, 0.9), height=patch['height'], width=patch['width'], angle=cube_params['bpa'],
                              transform=ax1.transAxes, edgecolor='lightgray', linewidth=1))
        fig.savefig(outfile, bbox_inches='tight')
    else:
        print('\t{} already exists. Will not overwrite.'.format(outfile))

    return


# Make pv plot for object
def make_pv(source, src_basename, cube_params, suffix='png'):

    outfile = src_basename.replace('cubelets', 'figures') + '_{}_pv.{}'.format(source['id'], suffix)

    if not os.path.isfile(outfile):
        try:
            print("\tMaking pv slice.")
            pv = fits.open(src_basename + '_{}_pv.fits'.format(str(source['id'])))
        except FileNotFoundError:
            print("\tNo pv fits file.  Perhaps you ran SoFiA-2 which doesn't produce this yet?")
            return

        wcs_pv = WCS(pv[0].header)
        ang1, freq1 = wcs_pv.wcs_pix2world(0, 0, 0)
        ang2, freq2 = wcs_pv.wcs_pix2world(pv[0].header['NAXIS1'] - 1, pv[0].header['NAXIS2'] - 1, 0)
        pv_rms = np.nanstd(pv[0].data)

        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111, projection=WCS(pv[0].header))
        ax1.imshow(pv[0].data, cmap='gray', aspect='auto')
        # if np.all (np.isnan (pv[0].data)): continue
        ax1.contour(pv[0].data, colors='black', levels=[-2 * pv_rms, 2 * pv_rms, 4 * pv_rms])
        ax1.autoscale(False)
        ax1.plot([0.0, 0.0], [freq1, freq2], c='orange', linestyle='--', linewidth=0.75,
                 transform=ax1.get_transform('world'))
        ax1.set_title(source['name'], fontsize=16)
        ax1.tick_params(axis='both', which='major', labelsize=18)
        ax1.set_xlabel('Angular Offset [deg]', fontsize=16)
        ax1.text(0.5, 0.05, 'Kinematic PA = {:5.1f} deg'.format(source['kin_pa']), ha='center', va='center',
                 transform=ax1.transAxes, color='orange', fontsize=18)
        ax1.coords[1].set_ticks_position('l')

        convention = 'Optical'
        if 'freq' in source.colnames:
            freq_sys = source['freq']
            ax1.plot([ang1, ang2], [freq_sys, freq_sys], c='orange', linestyle='--',
                     linewidth=0.75, transform=ax1.get_transform('world'))
            ax1.set_ylabel('Frequency [Hz]', fontsize=16)
            # freq_yticks = ax1.get_yticks()  # freq auto yticks from matplotlib
            ax2 = ax1.twinx()
            vel1 = const.c.to(u.km / u.s).value * (HI_restfreq.value / freq1 - 1)
            vel2 = const.c.to(u.km / u.s).value * (HI_restfreq.value / freq2 - 1)
            ax2.set_ylim(vel2, vel1)
            ax2.set_ylabel('{} {} velocity [km/s]'.format(cube_params['spec_sys'].capitalize(), convention))
        else:
            if cube_params['spec_axis'] == 'VRAD': convention = 'Radio'
            vel_sys = source['v_col']
            ax1.plot([ang1, ang2], [vel_sys, vel_sys], c='orange', linestyle='--',
                     linewidth=0.75, transform=ax1.get_transform('world'))
            ax1.set_ylabel('{} {} velocity [m/s]'.format(cube_params['spec_sys'].capitalize(), convention,
                                                         fontsize=18))

        fig.savefig(outfile, bbox_inches='tight')
        pv.close()

    else:
        print('\t{} already exists. Will not overwrite.'.format(outfile))

    return


def main(source, src_basename, opt_view=6*u.arcmin, suffix='png', sofia=2, beam=None, surveys=None, snr_range=[2,3]):

    print("\n\tStart making spatial images of the spectral line source {}: {}.".format(source['id'], source['name']))

    # Get beam information from the source cubelet
    if sofia == 2:
        cube_params = get_info(src_basename + '_{}_cube.fits'.format(source['id']), beam)
    elif sofia == 1:
        cube_params = get_info(src_basename + '_{}.fits'.format(source['id']), beam)

    opt_head = None

    # Calculate base contour
    try:
        with fits.open(src_basename + '_{}_snr.fits'.format(str(source['id']))) as hdulist_snr, fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id']))) as hdulist_hi:
             HIlowest = np.median(hdulist_hi[0].data[(hdulist_snr[0].data > snr_range[0])*(hdulist_snr[0].data < snr_range[1])])
        print("\tThe first HI contour defined at SNR = {0} has level = {1:.3e} (mom0 data units).".format(snr_range,HIlowest))
    except FileNotFoundError:
        print("\tNo SNR and/or mom0 fits file. Perhaps you ran SoFiA without generating moments?")
        return
#    with fits.open(src_basename + '_{}_mom0.fits'.format(str(source['id']))) as hdulist_hi
#    base_contour = np.median(hdulist_hi[0].data[(hdulist_snr[0].data > snr_range[0])*(hdulist_snr[0].data < snr_range[1])])

    # Get the position of the source to retrieve an survey image
    hi_pos = SkyCoord(ra=source['ra'], dec=source['dec'], unit='deg',
                      equinox=cube_params['equinox'], frame=cube_params['frame'])

    # SkyView (and maybe other queries??) won't retrieve non-ICRS or non-J2000 coordinates every time,
    # so let's transform everything to ICRS ....Need to keep an eye on this (may have been a server issue).
    hi_pos_icrs = hi_pos.transform_to('icrs')

    # Calculate the size of the survey image for the moment maps
    Xc = source['x']
    Yc = source['y']
    Xmin = source['x_min']
    Ymin = source['y_min']
    Xmax = source['x_max']
    Ymax = source['y_max']
    Xsize = np.array([((Xmax - Xc) * cube_params['cellsize']).to(u.arcmin).value,
                      ((Xc - Xmin) * cube_params['cellsize']).to(u.arcmin).value])
    Ysize = np.array([((Ymax - Yc) * cube_params['cellsize']).to(u.arcmin).value,
                      ((Yc - Ymin) * cube_params['cellsize']).to(u.arcmin).value])
    if np.any(Xsize > opt_view.value / 2) | np.any(Ysize > opt_view.value / 2):
        opt_view = np.max([Xsize, Ysize]) * 2 * 1.05 * u.arcmin
        print("\tImage size bigger than default. Now {:.2f} arcmin".format(opt_view.value))

    # Temporarily replace with ICRS ra/dec for plotting purposes in the rest (won't change catalog file.):
    source['ra'] = hi_pos_icrs.ra.deg
    source['dec'] = hi_pos_icrs.dec.deg

    # Calculate the size of the beam (plotted as a fraction of the image size)
    patch_height = (cube_params['bmaj'] / opt_view).decompose()
    patch_width = (cube_params['bmin'] / opt_view).decompose()
    patch = {'width': patch_width, 'height': patch_height}

    # For CHILES: plot HI contours on HST image if desired.
    if ('hst' in surveys) | ('HST' in surveys):
        hst_opt_view = 40 * u.arcsec
        if np.any(Xsize > hst_opt_view.to(u.arcmin).value / 2) | np.any(Ysize > hst_opt_view.to(u.arcmin).value / 2):
            hst_opt_view = (np.max([Xsize, Ysize]) * 2 * 1.05 * u.arcmin).to(u.arcsec)
        hst_opt = get_hst_cosmos(source, opt_view=hst_opt_view)
        if hst_opt:
            patch_height = (cube_params['bmaj'] / hst_opt_view).decompose()
            patch_width = (cube_params['bmin'] / hst_opt_view).decompose()
            patch_hst = {'width': patch_width, 'height': patch_height}
            make_overlay(source, src_basename, cube_params, patch_hst, hst_opt, HIlowest, suffix=suffix,
                         survey='hst')
        if surveys[0] == 'hst':
            opt_head = hst_opt[0].header
            opt_view = hst_opt_view
            patch = patch_hst
        surveys.remove('hst')

    # Create a false color optical panstarrs overlay, if requested, or if dss2 fails for some reason:
    if ('panstarrs' in surveys):
        pstar_im, pstar_head = get_panstarrs(hi_pos_icrs, opt_view=opt_view)
        if pstar_im:
            make_color_im(source, src_basename, cube_params, patch, pstar_im, pstar_head, HIlowest,
                          suffix=suffix, survey='panstarrs')
        if surveys[0] == 'panstarrs':
            opt_head = pstar_head
        surveys.remove('panstarrs')

    # If requested plot HI contours on DECaLS imaging
    if 'decals' in surveys:
        decals_im, decals_head = get_decals(hi_pos_icrs, opt_view=opt_view)
        make_color_im(source, src_basename, cube_params, patch, decals_im, decals_head, HIlowest, suffix=suffix,
                      survey='decals')
        if surveys[0] == 'decals':
            opt_head = decals_head
        surveys.remove('decals')

    # If requested, plot the HI contours on any number of survey images available through SkyView.
    if len(surveys) > 0:
        for survey in surveys:
            try:
                overlay_image = get_skyview(hi_pos_icrs, opt_view=opt_view, survey=survey)
                make_overlay(source, src_basename, cube_params, patch, overlay_image, HIlowest, suffix=suffix,
                             survey=survey)
                if surveys[0] == survey:
                    opt_head = overlay_image[0].header
            except ValueError:
                print("\tERROR: \"{}\" may not among the survey hosted at skyview or survey names recognized by "
                      "astroquery. \n\t\tSee SkyView.list_surveys or SkyView.survey_dict from astroquery for valid "
                      "surveys.".format(survey))
            except HTTPError:
                print("\tERROR: http error 404 returned from SkyView query.  Skipping {}.".format(survey))

    # Make the rest of the images if there is a survey image to regrid to.
    if opt_head:
        make_mom0(source, src_basename, cube_params, patch, opt_head, HIlowest, suffix=suffix)
        make_snr(source, src_basename, cube_params, patch, opt_head, HIlowest, suffix=suffix)
        make_mom1(source, src_basename, cube_params, patch, opt_head, HIlowest, opt_view=opt_view, suffix=suffix,
                  sofia=2)

    # Make pv if it was created (only in SoFiA-1); not dependent on having a survey image to regrid to.
    make_pv(source, src_basename, cube_params, suffix=suffix)

    plt.close('all')

    print("\tDone making spatial images of the spectral line source {}: {}.".format(source['id'], source['name']))

    return True


if __name__ == '__main__':

    main(source, src_basename, opt_view=6*u.arcmin, suffix='png', snr_range=[2,3])
