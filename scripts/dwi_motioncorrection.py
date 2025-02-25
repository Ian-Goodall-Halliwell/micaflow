import argparse
import ants
import numpy as np
from tqdm import tqdm

def run_motion_correction(dwi_path, bval_path, bvec_path):
    """
    Replace the previous motion correction logic with the QuickSyN-based 
    registration you provided for each volume in the DWI.
    """
    # Read the main DWI file using ANTs
    dwi_ants = ants.image_read(dwi_path)
    dwi_data = dwi_ants.numpy()

    # B0 is assumed to be the first volume (index 0)
    b0_data = dwi_data[..., 0]
    b0_ants = ants.from_numpy(
        b0_data,
        origin=dwi_ants.origin[:3],
        spacing=dwi_ants.spacing[:3]
    )

    registered_data = np.zeros_like(dwi_data)
    # Keep the original B0 in the first volume
    registered_data[..., 0] = b0_data

    # Register each shell to B0 using a quick approach
    for idx in tqdm(range(1, dwi_data.shape[-1]), desc="Registering volumes"):
        moving_data = dwi_data[..., idx]
        moving_ants = ants.from_numpy(
            moving_data,
            origin=dwi_ants.origin[:3],
            spacing=dwi_ants.spacing[:3]
        )

        # Rigid registration
        rigid_reg = ants.registration(
            fixed=b0_ants,
            moving=moving_ants,
            type_of_transform='QuickRigid'
        )
        # Non-linear registration (SyNOnly) using the rigid transform as initial
        quicksyn_reg = ants.registration(
            fixed=b0_ants,
            moving=rigid_reg['warpedmovout'],
            initial_transform=rigid_reg['fwdtransforms'][0],
            type_of_transform='SyNOnly'
        )

        # Place the registered volume in the output array
        warped_data = quicksyn_reg['warpedmovout'].numpy()
        registered_data[..., idx] = warped_data

    # Save the registered data
    registered_ants = ants.from_numpy(
        registered_data,
        origin=dwi_ants.origin,
        spacing=dwi_ants.spacing
    )
    out_path = "moving_motion_corrected.nii.gz"
    ants.image_write(registered_ants, out_path)

    print("Motion correction completed for all shells with QuickSyN registration.")
    return out_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform motion correction on a DWI image using ANTs QuickSyN."
    )
    parser.add_argument("--denoised", type=str, required=True,
                        help="Path to the denoised DWI (NIfTI file).")
    parser.add_argument("--bval", type=str, required=True,
                        help="Path to the bvals file. (Currently unused, but retained for consistency.)")
    parser.add_argument("--bvec", type=str, required=True,
                        help="Path to the bvecs file. (Currently unused, but retained for consistency.)")
    
    args = parser.parse_args()
    corrected_image = run_motion_correction(args.denoised, args.bval, args.bvec)
    print("Motion corrected image saved as:", corrected_image)
