import argparse
from nifreeze.data import dmri
from nifreeze.estimator_motion import Estimator

# ----- Function: Motion Correction -----
def run_motion_correction(denoised_path, moving_bval, moving_bvec):
    data_moving = dmri.load(denoised_path, bval_file=moving_bval, bvec_file=moving_bvec)
    motion_estimator = Estimator()
    motion_estimator.run(data_moving)
    corrected_path = "moving_motion_corrected.nii.gz"
    data_moving.to_nifti(corrected_path)
    return corrected_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform motion correction on a DWI image using nifreeze."
    )
    parser.add_argument("--denoised", type=str, required=True,
                        help="Path to the denoised image (NIfTI file).")
    parser.add_argument("--bval", type=str, required=True,
                        help="Path to the bvals file.")
    parser.add_argument("--bvec", type=str, required=True,
                        help="Path to the bvecs file.")
    
    args = parser.parse_args()
    corrected_image = run_motion_correction(args.denoised, args.bval, args.bvec)
    print("Motion corrected image saved as:", corrected_image)