from dipy.align.imaffine import AffineMap
from dipy.align.imwarp import DiffeomorphicMap
import nibabel as nib
import numpy as np
import ants
import argparse

# ----- Function: Apply Registration to FA/MD Maps -----
def apply_registration_to_fa_md(fa_path, md_path, atlas, reg_affine, mapping, md_out_path, fa_out_path):
    # Load the images
    MNI_atlas = ants.image_read(atlas)
    fa_map = ants.image_read(fa_path)
    md_map = ants.image_read(md_path)
    
    # Apply the affine transformation
    fa_affine_trans = ants.apply_transforms(fixed=MNI_atlas, moving=fa_map, transformlist=[reg_affine])
    md_affine_trans = ants.apply_transforms(fixed=MNI_atlas, moving=md_map, transformlist=[reg_affine])
    
    # Save the affine transformed images
    ants.image_write(fa_affine_trans, "fa_MNI_aff.nii.gz")
    ants.image_write(md_affine_trans, "md_MNI_aff.nii.gz")
    
    # Apply the nonlinear warp using the provided forward field
    fa_nonlinear = ants.apply_transforms(fixed=MNI_atlas, moving=fa_affine_trans, transformlist=[mapping])
    md_nonlinear = ants.apply_transforms(fixed=MNI_atlas, moving=md_affine_trans, transformlist=[mapping])
    
    # Save the final registered images
    ants.image_write(fa_nonlinear, fa_out_path)
    ants.image_write(md_nonlinear, md_out_path)
    
    print("FA and MD maps registered and saved as fa_MNI.nii.gz and md_MNI.nii.gz.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply registration to FA/MD maps using affine and nonlinear warps."
    )
    parser.add_argument("--fa", type=str, required=True,
                        help="Path to the FA map (NIfTI file).")
    parser.add_argument("--md", type=str, required=True,
                        help="Path to the MD map (NIfTI file).")
    parser.add_argument("--atlas", type=str, required=True,
                        help="Path to the atlas image (NIfTI file).")
    parser.add_argument("--reg_affine", type=str, required=True,
                        help="Path to the registration affine matrix file (ANTs .mat file).")
    parser.add_argument("--mapping", type=str, required=True,
                        help="Path to the nonlinear mapping (ANTs warp field).")
    parser.add_argument("--out_fa", type=str, required=True,
                        help="Output path for the registered FA maps.")
    parser.add_argument("--out_md", type=str, required=True,
                        help="Output path for the registered MD maps.")
    
    args = parser.parse_args()
    
    apply_registration_to_fa_md(args.fa, args.md, args.atlas, args.reg_affine, args.mapping, args.out_md, args.out_fa)