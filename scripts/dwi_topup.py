import argparse
from topup_new import topup  # assuming topup is available from topup_new.py

def run_topup(moving, b0, b0_bval, b0_bvec):
    # topup returns a nonlinear warp and a mask
    warp, mask = topup(moving, b0, b0_bval, b0_bvec)
    return warp, mask

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run topup correction to compute a warp field and a mask."
    )
    parser.add_argument("--moving", type=str, required=True,
                        help="Path to the moving DWI image (NIfTI file).")
    parser.add_argument("--b0", type=str, required=True,
                        help="Path to the b0 image (NIfTI file).")
    parser.add_argument("--b0_bval", type=str, required=True,
                        help="Path to the b0 bvals file.")
    parser.add_argument("--b0_bvec", type=str, required=True,
                        help="Path to the b0 bvecs file.")
    parser.add_argument("--warp_out", type=str, default="warp.nii.gz",
                        help="Output path for the warp field (NIfTI file).")
    parser.add_argument("--mask_out", type=str, default="mask.nii.gz",
                        help="Output path for the mask (NIfTI file).")
    args = parser.parse_args()
    
    warp, mask = run_topup(args.moving, args.b0, args.b0_bval, args.b0_bvec)
    
    # Try saving outputs assuming they are nibabel image objects
    import nibabel as nib
    try:
        
        mask_loaded = nib.load(mask)
        nib.save(mask_loaded, args.mask_out)
        warp_image = nib.Nifti1Image(warp.forward, mask_loaded.affine)
        nib.save(warp_image, args.warp_out)
        print("Warp field saved as:", args.warp_out)
        print("Mask saved as:", args.mask_out)
    except Exception as e:
        print("Could not save warp and mask as NIfTI files.")
        print("Warp:", warp)
        print("Mask:", mask)