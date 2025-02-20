import nibabel as nib
from dipy.align import register_dwi_to_template
from dipy.denoise.nlmeans import nlmeans
from dipy.denoise.noise_estimate import estimate_sigma
from dipy.core.gradients import gradient_table
import copy
import numpy as np
import subprocess
from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
from dipy.align.metrics import CCMetric  # cross-correlation metric
from nibabel.processing import resample_from_to
def topup(moving_dwi_img,b0_image, down_bval, down_bvec):
    moving_map = nib.load(moving_dwi_img)
    fixed_map = nib.load(b0_image)
    
    moving_sigma = estimate_sigma(moving_map.get_fdata()[...,0])
    moving_map_denoised = nlmeans(moving_map.get_fdata()[...,0],moving_sigma)
    
    fixed_sigma = estimate_sigma(fixed_map.get_fdata())
    fixed_map_denoised = nlmeans(fixed_map.get_fdata(),fixed_sigma)
    
    
    pipeline = ["center_of_mass", "translation","rigid", "affine"]
    level_iters = [500, 100, 50]    # Adjusted parameters
    sigmas = [4.0, 2.0, 1.0]
    factors = [8, 4, 2]
    xformed_dwi, reg_affine = register_dwi_to_template(
            dwi=fixed_map_denoised,
            dwi_affine=fixed_map.affine,
            gtab=gradient_table(down_bval,down_bvec),
            template=moving_map_denoised,
            template_affine=moving_map.affine,
            reg_method="aff",
            nbins=32,
            metric='MI',
            pipeline=pipeline,
            level_iters=level_iters,
            sigmas=sigmas,
            factors=factors)
    
    fixed_xformed_dwi = nib.Nifti1Image(xformed_dwi, moving_map.affine)
    nib.save(fixed_xformed_dwi, "topup_registered.nii.gz")
    
    # ----- Use HD-BET to extract brains from both xformed_dwi and upwards_map_denoised -----
    # Run HD-BET on the registered image
    subprocess.run("hd-bet -i topup_registered.nii.gz -o topup_registered_extracted.nii.gz --save_bet_mask", shell=True)
    fixed_xformed_dwi_brain = nib.load("topup_registered_extracted.nii.gz")
    
    # Save the denoised upwards map as a temporary NIfTI for HD-BET, then run HD-BET
    upwards_nifti = nib.Nifti1Image(moving_map_denoised, moving_map.affine)
    nib.save(upwards_nifti, "upwards_map_denoised.nii.gz")
    subprocess.run("hd-bet -i upwards_map_denoised.nii.gz -o moving_map_denoised_extracted.nii.gz --save_bet_mask", shell=True)
    moving_map_denoised_brain = nib.load("moving_map_denoised_extracted.nii.gz")
    
    
    # First, robustly scale the fixed, denoised up map
    p1_up, p99_up = np.percentile(moving_map_denoised_brain.get_fdata(), (1, 99))
    scaled_up = np.clip(moving_map_denoised_brain.get_fdata(), p1_up, p99_up)
    corrected_moving = (scaled_up - p1_up) / (p99_up - p1_up + 1e-8)
    # Robustly scale the current corrected up image between 0 and 1
    p1_corr, p99_corr = np.percentile(fixed_xformed_dwi_brain.get_fdata(), (1, 99))
    scaled_corr = np.clip(fixed_xformed_dwi_brain.get_fdata(), p1_corr, p99_corr)
    corrected_fixed = (scaled_corr - p1_corr) / (p99_corr - p1_corr + 1e-8)
    
    # --- STEP 2: Set Up the Symmetric Diffeomorphic Registration (SDR) ---
    # Choose a metric. Here we use the cross-correlation metric.
    metric = CCMetric(3)  # 3 is the dimension (3D)
    # Level iterations (you may need to adjust these for your data)
    level_iters = [1000, 100, 10]

    # Initialize the registration object
    sdr = SymmetricDiffeomorphicRegistration(metric, level_iters)
    mapping = sdr.optimize(corrected_fixed,corrected_moving)
    
    
    half_forward_map = mapping.forward/2
    half_inverse_map = mapping.backward/2
    
    nib.save(nib.Nifti1Image(half_forward_map,moving_map.affine), "half_forward.nii.gz")
    nib.save(nib.Nifti1Image(half_inverse_map,moving_map.affine), "half_backward.nii.gz")
    
    halfmapping = copy.deepcopy(mapping)
    halfmapping.forward = half_forward_map
    halfmapping.backward = half_inverse_map
    

    return halfmapping, "moving_map_denoised_extracted_bet.nii.gz"

if __name__ == "__main__":
    topup("sub-HC131_ses-01_acq-b700-41_dir-AP_dwi.nii.gz","sub-HC131_ses-01_dir-PA_dwi.nii.gz","sub-HC131_ses-01_dir-PA_dwi.bval","sub-HC131_ses-01_dir-PA_dwi.bvec")