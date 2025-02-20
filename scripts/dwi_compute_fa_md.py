import argparse
from dipy.reconst.dti import TensorModel
from dipy.core.gradients import gradient_table
import nibabel as nib

# ----- Function: FA/MD Estimation -----
def compute_fa_md(bias_corr_path, mask_path, moving_bval, moving_bvec):
    bias_corr = nib.load(bias_corr_path)
    mask = nib.load(mask_path)
    masked_data = bias_corr.get_fdata() * mask.get_fdata()[..., None]
    gtab = gradient_table(moving_bval, moving_bvec)
    tensor_model = TensorModel(gtab)
    tensor_fit = tensor_model.fit(masked_data)
    fa = tensor_fit.fa
    md = tensor_fit.md
    fa_path = "fa_map.nii.gz"
    md_path = "md_map.nii.gz"
    nib.save(nib.Nifti1Image(fa, bias_corr.affine), fa_path)
    nib.save(nib.Nifti1Image(md, bias_corr.affine), md_path)
    return fa_path, md_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute FA and MD maps using bias-corrected DWI and a brain mask."
    )
    parser.add_argument("--bias_corr", type=str, required=True,
                        help="Path to the bias-corrected DWI image (NIfTI file).")
    parser.add_argument("--mask", type=str, required=True,
                        help="Path to the brain mask image (NIfTI file).")
    parser.add_argument("--bval", type=str, required=True,
                        help="Path to the bvals file.")
    parser.add_argument("--bvec", type=str, required=True,
                        help="Path to the bvecs file.")
    args = parser.parse_args()
    
    fa_path, md_path = compute_fa_md(args.bias_corr, args.mask, args.bval, args.bvec)
    print("FA map saved as:", fa_path)
    print("MD map saved as:", md_path)