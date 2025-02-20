from dipy.align.imaffine import AffineMap
from dipy.align.imwarp import DiffeomorphicMap
import nibabel as nib
import numpy as np
import argparse

# ----- Function: Apply Registration to FA/MD Maps -----
def apply_registration_to_fa_md(fa_path, md_path, atlas, reg_affine, mapping, md_out_path, fa_out_path):
    MNI_atlas = nib.load(atlas)
    fa_map = nib.load(fa_path)
    md_map = nib.load(md_path)
    
    affmap = AffineMap(reg_affine, MNI_atlas.shape, MNI_atlas.affine,
                        fa_map.shape, fa_map.affine)
    fa_affine_trans = affmap.transform(fa_map.get_fdata()).astype(np.float32)
    md_affine_trans = affmap.transform(md_map.get_fdata()).astype(np.float32)
    nib.save(nib.Nifti1Image(fa_affine_trans, MNI_atlas.affine), "fa_MNI_aff.nii.gz")
    nib.save(nib.Nifti1Image(md_affine_trans, MNI_atlas.affine), "md_MNI_aff.nii.gz")
    # Apply nonlinear warp using the provided forward field via DiffeomorphicMap.
    NLmapping = DiffeomorphicMap(3, mapping.shape)
    NLmapping.forward = mapping.get_fdata().astype(np.float32)

    fa_nonlinear = NLmapping.transform(fa_affine_trans)
    md_nonlinear = NLmapping.transform(md_affine_trans)
    
    nib.save(nib.Nifti1Image(fa_nonlinear, MNI_atlas.affine), fa_out_path)
    nib.save(nib.Nifti1Image(md_nonlinear, MNI_atlas.affine), md_out_path)
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
                        help="Path to the registration affine matrix text file.")
    parser.add_argument("--mapping", type=str, required=True,
                        help="Path to the nonlinear mapping (NIfTI file).")
    parser.add_argument("--out_fa", type=str, required=True,
                        help="Output path for the registered FA maps.")
    parser.add_argument("--out_md", type=str, required=True,
                        help="Output path for the registered MD maps.")
    
    args = parser.parse_args()
    
    # Load the affine matrix and the nonlinear mapping
    reg_affine = np.loadtxt(args.reg_affine)
    mapping = nib.load(args.mapping)
    
    apply_registration_to_fa_md(args.fa, args.md, args.atlas, reg_affine, mapping, args.out_md, args.out_fa)