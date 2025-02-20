import os
import random
import string
from collections import Counter

import ants
import numpy as np


def write_nifti(input, id, output_dir, type):
    output_fname = os.path.join(output_dir, id + '_' + type + '.nii.gz')
    ants.image_write(input, output_fname)


def compute_RI(image, bg, mask):
    ri = np.zeros_like(image)
    bgm = np.stack(np.where(np.logical_and(image < bg, mask == 1)), axis=1)
    bgm_ind = bgm[:, 0], bgm[:, 1], bgm[:, 2]
    bgp = np.stack(np.where(np.logical_and(image > bg, mask == 1)), axis=1)
    bgp_ind = bgp[:, 0], bgp[:, 1], bgp[:, 2]

    ri[bgm_ind] = 100 * (1 - (bg - image[bgm_ind]) / bg)
    ri[bgp_ind] = 100 * (1 + (bg - image[bgp_ind]) / bg)
    return ri


def peakfinder(gm, wm, lower_q, upper_q):
    gm_peak = Counter(threshold_percentile(gm, lower_q, upper_q)).most_common(1)[0][0]
    wm_peak = Counter(threshold_percentile(wm, lower_q, upper_q)).most_common(1)[0][0]
    bg = 0.5 * (gm_peak + wm_peak)
    return bg


def threshold_percentile(x, lower_q, upper_q):
    x = x.numpy()
    lq = np.percentile(x, lower_q)
    uq = np.percentile(x, upper_q)
    x = x[np.logical_and(x > lq, x <= uq)]
    return x.flatten().round()


def find_logger_basefilename(logger):
    """Finds the logger base filename(s) currently there is only one"""
    log_file = None
    handler = logger.handlers[0]
    log_file = handler.baseFilename
    return log_file


def random_case_id():
    letters = ''.join(random.choices(string.ascii_letters, k=16))
    digits = ''.join(random.choices(string.digits, k=16))
    x = letters[:3].lower() + '_' + digits[:4]
    return x

import os

# restrict compute to CPU only
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import multiprocessing
import sys
import time

import ants  # type: ignore[import-untyped]
import numpy as np

# import zipfile
from PIL import Image

# reduce tensorflow logging verbosity
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

os.environ['ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS'] = str(multiprocessing.cpu_count())
os.environ['ANTS_RANDOM_SEED'] = '666'



class noelTexturesPy:
    def __init__(
        self,
        id,
        output_dir=None,
        input=None,
        mask=None,
    ):
        super().__init__()
        self._id = id
        self._outputdir = output_dir
        self.input = input
        self.mask = mask

    def load_nifti_file(self):
        # load nifti data to memory
        print('loading nifti files')
        self._input = ants.image_read(self.input)
        self._mask = ants.image_read(self.mask)


    def segmentation(self):
        print('computing GM, WM, CSF segmentation')
        # https://antsx.github.io/ANTsPyNet/docs/build/html/utilities.html#applications


        segm = ants.atropos(
            a=self._input,
            i='Kmeans[3]',
            m='[0.2,1x1x1]',
            c='[3,0]',
            x=self._mask,
        )
        self._segm = segm['segmentation']
        self._gm = np.where((self._segm.numpy() == 2), 1, 0).astype('float32')
        self._wm = np.where((self._segm.numpy() == 3), 1, 0).astype('float32')


    def gradient_magnitude(self):
        print('computing gradient magnitude')

        self._grad_input = ants.iMath(self._input, 'Grad', 1)

        ants.image_write(
            self._grad_input,
            self._outputdir + '_gradient_magnitude.nii',
        )


    def relative_intensity(self):
        print('computing relative intensity')

        input_n4_gm = self._input * self._input.new_image_like(self._gm)
        input_n4_wm = self._input * self._input.new_image_like(self._wm)
        bg_input = peakfinder(input_n4_gm, input_n4_wm, 1, 99.5)
        input_ri = compute_RI(self._input.numpy(), bg_input, self._mask.numpy())
        tmp = self._input.new_image_like(input_ri)
        self._ri = ants.smooth_image(tmp, sigma=3, FWHM=True)
        ants.image_write(
            self._ri,
            self._outputdir + '_relative_intensity.nii',
        )


    def file_processor(self):
        start = time.time()
        self.load_nifti_file()
        self.segmentation()
        self.gradient_magnitude()
        self.relative_intensity()
        # self.create_zip_archive()
        end = time.time()
        print(
            'pipeline processing time elapsed: {} seconds'.format(
                np.round(end - start, 1)
            )
        )
