#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys


def main():
    os.environ["FREESURFER_HOME"] = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="MICAFLOW: A processing pipeline.")
    parser.add_argument("--subject", required=True, help="Subject ID")
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--out_dir", required=True, help="Output directory")
    parser.add_argument("--threads", required=True, help="Number of threads")
    parser.add_argument(
        "--data_directory", required=True, help="BIDS-compatible data directory"
    )
    args = parser.parse_args()

    # Define atlas paths
    atlas_mni152 = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz",
    )
    atlas_mni152_seg = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "atlas/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz",
    )

    # Define image types and paths
    image_types = [
        (
            os.path.join(
                args.data_directory,
                args.subject,
                args.session,
                "anat",
                f"{args.subject}_{args.session}_run-1_T1w.nii.gz",
            ),
            "T1w",
        ),
        (
            os.path.join(
                args.data_directory,
                args.subject,
                args.session,
                "anat",
                f"{args.subject}_{args.session}_FLAIR.nii.gz",
            ),
            "FLAIR",
        ),
    ]

    for image_path, img_type in image_types:
        # Brain Segmentation
        synthseg_output = brain_segmentation(image_path, img_type, args)

        # Bias Field Correction
        n4_output = bias_field_correction(image_path, img_type, args)

        # Registration
        fwd_field, bak_field = registration(
            image_path, img_type, synthseg_output, atlas_mni152, atlas_mni152_seg, args
        )

        # Apply Warp
        warped_image = apply_warp(image_path, img_type, n4_output, fwd_field, args)

        # Calculate Metrics
        calculate_metrics(image_path, img_type, warped_image, atlas_mni152, args)


def brain_segmentation(image, img_type, args):
    output_dir = os.path.join(args.out_dir, args.subject, args.session, "anat")
    os.makedirs(output_dir, exist_ok=True)
    synthseg_output = f"{args.subject}_{args.session}_desc-synthseg_{img_type}.nii.gz"
    volumes_output = f"{args.subject}_{args.session}_desc-volumes_{img_type}.csv"
    qc_output = f"{args.subject}_{args.session}_desc-qc_{img_type}.csv"
    cmd = [
        sys.executable,
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "scripts", "mri_synthseg.py"
        ),
        "--i",
        image,
        "--o",
        os.path.join(output_dir, synthseg_output),
        "--robust",
        "--vol",
        os.path.join(output_dir, volumes_output),
        "--qc",
        os.path.join(output_dir, qc_output),
        "--threads",
        args.threads,
        "--cpu",
        "--parc",
    ]
    env = os.environ.copy()
    subprocess.run(cmd, env=env, check=True)
    return os.path.join(output_dir, synthseg_output)


def bias_field_correction(image, img_type, args):
    output_dir = os.path.join(args.out_dir, args.subject, args.session, "anat")
    output_file = f"{args.subject}_{args.session}_desc-N4_{img_type}.nii.gz"
    output_file_dir = os.path.join(output_dir, output_file)
    print("Running N4BiasFieldCorrection")
    cmd = [
        sys.executable,
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "scripts",
            "N4BiasFieldCorrection.py",
        ),
        "-i",
        image,
        "-o",
        output_file_dir,
    ]
    subprocess.run(cmd, check=True)
    # N4BiasFieldCorrection.bias_field_correction(image, output_file_dir)

    print("N4BiasFieldCorrection done")
    return os.path.abspath(output_file_dir)


def registration(image, img_type, segmentation, atlas_mni152, atlas_mni152_seg, args):
    output_dir = os.path.join(args.out_dir, args.subject, args.session, "xfm")
    os.makedirs(output_dir, exist_ok=True)
    fwd_field = f"{args.subject}_{args.session}_from-{img_type}_to-MNI152_desc-easyreg_fwdfield.nii.gz"
    bak_field = f"{args.subject}_{args.session}_from-{img_type}_to-MNI152_desc-easyreg_bakfield.nii.gz"
    cmd = [
        sys.executable,
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "scripts", "mri_easyreg.py"
        ),
        "--ref",
        atlas_mni152,
        "--ref_seg",
        atlas_mni152_seg,
        "--flo",
        image,
        "--flo_seg",
        segmentation,
        "--fwd_field",
        os.path.join(output_dir, fwd_field),
        "--bak_field",
        os.path.join(output_dir, bak_field),
        "--threads",
        args.threads,
    ]
    subprocess.run(cmd, check=True)
    return os.path.join(output_dir, fwd_field), os.path.join(output_dir, bak_field)


def apply_warp(image, img_type, n4_image, warp_field, args):
    output_dir = os.path.join(args.out_dir, args.subject, args.session, "anat")
    os.makedirs(output_dir, exist_ok=True)
    warped_image = f"{args.subject}_{args.session}_space-MNI152_{img_type}.nii.gz"
    cmd = [
        sys.executable,
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "scripts", "mri_easywarp.py"
        ),
        "--i",
        n4_image,
        "--o",
        os.path.join(output_dir, warped_image),
        "--field",
        warp_field,
        "--threads",
        args.threads,
    ]
    subprocess.run(cmd, check=True)
    return os.path.join(output_dir, warped_image)


def calculate_metrics(image, img_type, warped_image, atlas_mni152, args):
    output_dir = os.path.join(args.out_dir, args.subject, args.session, "metrics")
    os.makedirs(output_dir, exist_ok=True)
    output_csv = f"{args.subject}_{args.session}_jaccard.csv"
    cmd = [
        sys.executable,
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "scripts",
            "calculate_metrics.py",
        ),
        warped_image,
        atlas_mni152,
        os.path.join(output_dir, output_csv),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
