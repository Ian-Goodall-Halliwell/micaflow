import nibabel as nib
from dipy.align.metrics import CCMetric  # cross-correlation metric
from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
import argparse

# ----- Function: Nonlinear Registration -----
def run_nonlinear_registration(MNI_atlas, fixed_xformed_path, warp_path):
    fixed_xformed = nib.load(fixed_xformed_path)
    metric = CCMetric(3)
    level_iters = [1000, 100, 10]
    sdr = SymmetricDiffeomorphicRegistration(metric, level_iters)
    mapping = sdr.optimize(MNI_atlas.get_fdata(), fixed_xformed.get_fdata())
    nonlinear_transform = mapping.transform(fixed_xformed.get_fdata())
    nib.save(nib.Nifti1Image(nonlinear_transform, MNI_atlas.affine), "nonlinear_transform.nii.gz")
    nib.save(nib.Nifti1Image(mapping.forward, MNI_atlas.affine), "forward_MNI_warp.nii.gz")
    nib.save(nib.Nifti1Image(mapping.backward, MNI_atlas.affine), warp_path)
    return mapping

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run nonlinear registration using a provided MNI atlas and fixed transformed image."
    )
    parser.add_argument("--atlas", type=str, required=True,
                        help="Path to the MNI atlas (NIfTI file).")
    parser.add_argument("--fixed", type=str, required=True,
                        help="Path to the fixed transformed image (NIfTI file).")
    parser.add_argument("--warp", type=str, required=True,
                        help="Path to the fixed transformed image (NIfTI file).")
    args = parser.parse_args()
    
    MNI_atlas = nib.load(args.atlas)
    run_nonlinear_registration(MNI_atlas, args.fixed, args.warp)
    print("Nonlinear registration complete. Outputs saved as:")
    print(" - nonlinear_transform.nii.gz")
    print(" - forward_MNI_warp.nii.gz")
    print(" - backward_MNI_warp.nii.gz")