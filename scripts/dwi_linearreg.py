import argparse
import numpy as np
import nibabel as nib
from dipy.core.gradients import gradient_table
from dipy.align import register_dwi_to_template

# ----- Function: Linear Registration -----
def run_linear_registration(bias_corr_path, moving_bval, moving_bvec, atlas, affine_path):
    # Linear registration to atlas
    pipeline = ["center_of_mass", "translation", "rigid", "affine"]
    level_iters = [500, 100, 50]    # Adjusted parameters
    sigmas = [4.0, 2.0, 1.0]
    factors = [8, 4, 2]
    
    bias_corr = nib.load(bias_corr_path)
    MNI_atlas = nib.load(atlas)
    xformed_dwi, reg_affine = register_dwi_to_template(
        dwi=bias_corr,
        gtab=gradient_table(moving_bval, moving_bvec),
        template=MNI_atlas,
        reg_method="aff",
        nbins=32,
        metric='MI',
        pipeline=pipeline,
        level_iters=level_iters,
        sigmas=sigmas,
        factors=factors)
    # Save the affine matrix for later use
    np.savetxt(affine_path, reg_affine)
    fixed_xformed_path = "registered.nii.gz"
    fixed_xformed_dwi = nib.Nifti1Image(xformed_dwi, MNI_atlas.affine)
    nib.save(fixed_xformed_dwi, fixed_xformed_path)
    return fixed_xformed_path, reg_affine, MNI_atlas

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform linear registration of bias-corrected DWI to an atlas."
    )
    parser.add_argument("--bias_corr", type=str, required=True,
                        help="Path to the bias-corrected DWI image (NIfTI file).")
    parser.add_argument("--bval", type=str, required=True,
                        help="Path to the bvals file.")
    parser.add_argument("--bvec", type=str, required=True,
                        help="Path to the bvecs file.")
    parser.add_argument("--atlas", type=str, required=True,
                        help="Path to the atlas image (NIfTI file).")
    parser.add_argument("--affine", type=str, required=True,
                        help="Path for the affine output.")
    
    args = parser.parse_args()
    
    fixed_path, reg_affine, MNI_atlas = run_linear_registration(
        args.bias_corr,
        args.bval,
        args.bvec,
        args.atlas,
        args.affine
    )
    
    print("Registered image saved as:", fixed_path)
    print("Affine transform saved as:", args.affine)