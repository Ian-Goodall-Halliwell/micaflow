import argparse
import numpy as np
import nibabel as nib
from dipy.core.gradients import gradient_table
from dipy.align import register_dwi_to_template
import ants
from tqdm import tqdm
import shutil

def run(dwi_path, atlas_path, warp_file=None, affine_file=None, rev_warp_file=None, rev_affine_file=None):
    """
    Replace the previous motion correction logic with the QuickSyN-based 
    registration you provided for each volume in the DWI.
    """
    # Read the main DWI file using ANTs
    dwi_ants = ants.image_read(dwi_path)
    dwi_data = dwi_ants.numpy()

    atlas_ants = ants.image_read(atlas_path)    
    atlas_data = atlas_ants.numpy()
    

    b0_ants = ants.from_numpy(
        dwi_data,
        origin=dwi_ants.origin[:3],
        spacing=dwi_ants.spacing[:3]
    )

    
    # 'SyN' transform includes both linear and nonlinear registration.
    transforms = ants.registration(fixed=atlas_ants, moving=b0_ants, type_of_transform="SyNRA")

    # The result of the registration is a dictionary containing, among other keys:
    # 'warpedmovout' and 'fwdtransforms' (list of transform paths generated).
    registered = transforms["warpedmovout"]

    # If specified, save the transform files
    # Typically, transforms["fwdtransforms"][0] is the warp field, and [1] is the affine.
    if warp_file:
        shutil.copyfile(transforms["fwdtransforms"][0], warp_file)
        print(f"Saved warp field as {warp_file}")
    if affine_file:
        shutil.copyfile(transforms["fwdtransforms"][1], affine_file)
        print(f"Saved affine transform as {affine_file}")
    if rev_warp_file:
        shutil.copyfile(transforms["invtransforms"][0], rev_warp_file)
        print(f"Saved reverse warp field as {rev_warp_file}")
    if rev_affine_file:
        shutil.copyfile(transforms["invtransforms"][1], rev_affine_file)
        print(f"Saved reverse affine transform as {rev_affine_file}")
        

    # # Rigid registration
    # rigid_reg = ants.registration(
    #     fixed=atlas_ants,
    #     moving=b0_ants,
    #     type_of_transform='QuickRigid'
    # )
    # # Non-linear registration (SyNOnly) using the rigid transform as initial
    # quicksyn_reg = ants.registration(
    #     fixed=atlas_ants,
    #     moving=rigid_reg['warpedmovout'],
    #     initial_transform=rigid_reg['fwdtransforms'][0],
    #     type_of_transform='SyNOnly'
    # )

  
    # # If specified, save the transform files
    # # Typically, transforms["fwdtransforms"][0] is the warp field, and [1] is the affine.
    # if warp_file:
    #     shutil.copyfile(quicksyn_reg["fwdtransforms"][0], warp_file)
    #     print(f"Saved warp field as {warp_file}")
    # if affine_file:
    #     shutil.copyfile(rigid_reg["fwdtransforms"][0], affine_file)
    #     print(f"Saved affine transform as {affine_file}")
    # if rev_warp_file:
    #     shutil.copyfile(quicksyn_reg["invtransforms"][0], rev_warp_file)
    #     print(f"Saved reverse warp field as {rev_warp_file}")
    # if rev_affine_file:
    #     shutil.copyfile(rigid_reg["invtransforms"][0], rev_affine_file)
    #     print(f"Saved reverse affine transform as {rev_affine_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform linear registration of bias-corrected DWI to an atlas."
    )
    parser.add_argument("--moving", type=str, required=True,
                        help="Path to the bias-corrected DWI image (NIfTI file).")
    parser.add_argument("--fixed", type=str, required=True,
                        help="Path to the atlas image (NIfTI file).")
    parser.add_argument("--affine", type=str, required=True,
                        help="Path for the affine output.")
    parser.add_argument("--rev_affine", type=str, required=True,
                        help="Path for the affine output.")
    parser.add_argument("--warpfield", type=str, required=True,
                        help="Path for the affine output.")
    parser.add_argument("--rev_warpfield", type=str, required=True,
                        help="Path for the affine output.")
    
    args = parser.parse_args()
    run(args.moving, args.fixed, args.warpfield, args.affine, args.rev_warpfield, args.rev_affine)
    print("Registration complete.")
    