import subprocess
import sys
import time


def main():
    # Define input file paths
    start = time.time()
    moving_path = (
        "/home/ian/GitHub/testdata/sub-HC131_ses-01_acq-b700-41_dir-AP_dwi.nii.gz"
    )
    dwi_bval_path = (
        "/home/ian/GitHub/testdata/sub-HC131_ses-01_acq-b700-41_dir-AP_dwi.bval"
    )
    dwi_bvec_path = (
        "/home/ian/GitHub/testdata/sub-HC131_ses-01_acq-b700-41_dir-AP_dwi.bvec"
    )
    b0_path = "/home/ian/GitHub/testdata/sub-HC131_ses-01_dir-PA_dwi.nii.gz"
    b0_bval_path = "/home/ian/GitHub/testdata/sub-HC131_ses-01_dir-PA_dwi.bval"
    b0_bvec_path = "/home/ian/GitHub/testdata/sub-HC131_ses-01_dir-PA_dwi.bvec"
    atlas_path = "mni_icbm152_t2_tal_nlin_sym_09a.nii"

    # Define expected output filenames
    mask_path = "mask.nii.gz"
    denoised_output = "denoised_moving.nii.gz"
    motion_corrected_output = "moving_motion_corrected.nii.gz"
    warp_output = "warp.nii.gz"
    topup_mask_output = "mask.nii.gz"
    bias_corrected_output = "denoised_moving_corrected.nii.gz"
    linear_reg_output = "registered.nii.gz"
    affine_matrix_file = "reg_affine.txt"
    fa_map_file = "fa_map.nii.gz"
    md_map_file = "md_map.nii.gz"
    nonlinear_forward_warp = "backward_MNI_warp.nii.gz"

    # Step 1: Denoise
    print("Running dwi_denoise.py ...")
    subprocess.run([
        sys.executable, "dwi_denoise.py",
        "--moving", moving_path,
        "--bval", dwi_bval_path,
        "--bvec", dwi_bvec_path
    ], check=True)

    # Step 2: Motion Correction on denoised image
    print("Running dwi_motioncorrection.py ...")
    subprocess.run([
        sys.executable, "dwi_motioncorrection.py",
        "--denoised", denoised_output,
        "--bval", dwi_bval_path,
        "--bvec", dwi_bvec_path
    ], check=True)

    # Step 3: Compute topup (warp field and mask)
    print("Running dwi_topup.py ...")
    subprocess.run([
        sys.executable, "dwi_topup.py",
        "--moving", moving_path,
        "--b0", b0_path,
        "--b0_bval", b0_bval_path,
        "--b0_bvec", b0_bvec_path,
        "--warp_out", warp_output,
        "--mask_out", topup_mask_output
    ], check=True)

    # Step 4: Apply Topup Correction using the warp field
    print("Running dwi_applytopup.py ...")
    subprocess.run([
        sys.executable, "dwi_applytopup.py",
        "--motion_corr", motion_corrected_output,
        "--warp", warp_output,
        "--affine", moving_path
    ], check=True)

    # Step 5: Bias Field Correction
    print("Running dwi_biascorrection.py ...")
    subprocess.run([
        sys.executable, "dwi_biascorrection.py",
        "--image", denoised_output,
        "--mask", topup_mask_output
    ], check=True)

    # Step 6: Linear Registration to Atlas
    print("Running dwi_linearreg.py ...")
    subprocess.run([
        sys.executable, "dwi_linearreg.py",
        "--bias_corr", bias_corrected_output,
        "--bval", dwi_bval_path,
        "--bvec", dwi_bvec_path,
        "--atlas", atlas_path
    ], check=True)

    # Step 7: Nonlinear Registration
    print("Running dwi_nonlinearreg.py ...")
    subprocess.run([
        sys.executable, "dwi_nonlinearreg.py",
        "--atlas", atlas_path,
        "--fixed", linear_reg_output
    ], check=True)

    # Step 8: Compute FA and MD maps
    print("Running dwi_compute_fa_md.py ...")
    subprocess.run([
        sys.executable, "dwi_compute_fa_md.py",
        "--bias_corr", bias_corrected_output,
        "--mask", mask_path,
        "--bval", dwi_bval_path,
        "--bvec", dwi_bvec_path
    ], check=True)

    # Step 9: Register FA/MD maps into MNI space
    print("Running dwi_fa_md_registration.py ...")
    subprocess.run(
        [
            sys.executable,
            "dwi_fa_md_registration.py",
            "--fa",
            fa_map_file,
            "--md",
            md_map_file,
            "--atlas",
            atlas_path,
            "--reg_affine",
            affine_matrix_file,
            "--mapping",
            nonlinear_forward_warp,
        ],
        check=True,
    )

    end = time.time()
    print(f"Total processing time: {end - start:.2f} seconds")
    print("All processing steps complete.")


if __name__ == "__main__":
    main()
