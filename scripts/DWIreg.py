from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
from dipy.align.metrics import CCMetric
import nibabel as nib
import argparse
import numpy as np


def load(moving, fixed, output_forward, output_backward, output):
    # Load moving and fixed images
    moving_img = nib.load(moving)
    fixed_img = nib.load(fixed)

    # Set registration metric (Cross-Correlation for DWI)
    metric = CCMetric(3)
    sdr = SymmetricDiffeomorphicRegistration(metric, [10, 5, 2])  # Multi-resolution
    data = fixed_img.get_fdata()
    data = np.expand_dims(data, axis=-1)
    # Register
    mapping = sdr.optimize(data, moving_img.get_fdata())

    # Forward warp field
    forward_warp = mapping.forward
    forward_warp_img = nib.Nifti1Image(forward_warp, fixed_img.affine)
    nib.save(forward_warp_img, output_forward)

    # Backward warp field
    backward_warp = mapping.backward
    backward_warp_img = nib.Nifti1Image(backward_warp, moving_img.affine)
    nib.save(backward_warp_img, output_backward)

    warped = mapping.transform(moving_img.get_fdata())
    warped_img = nib.Nifti1Image(warped, fixed_img.affine)
    nib.save(warped_img, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform N4 Bias Field Correction")
    parser.add_argument("--fixed", "-f", required=True, help="Input image file")
    parser.add_argument(
        "--moving", "-m", required=True, help="Output corrected image file"
    )
    parser.add_argument(
        "-of",
        "--output_forward",
        required=True,
        help="Save forward warp field to path.",
    )
    parser.add_argument(
        "-ob",
        "--output_backward",
        required=True,
        help="Save backward warp field to path.",
    )
    parser.add_argument("-o", "--output", help="Save corrected image to path.")
    args = parser.parse_args()

    load(
        args.moving, args.fixed, args.output_forward, args.output_backward, args.output
    )
