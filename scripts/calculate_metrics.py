import sys
import csv
import os
from nipype.algorithms.metrics import Overlap
import nibabel as nib


def apply_threshold(image_path, threshold=0.5):
    img = nib.load(image_path)
    data = img.get_fdata()
    data[data < threshold] = 0
    # Write to a new file to avoid in-place modifications that may cause issues
    new_image_path = image_path.replace(".nii", "_thr.nii")
    nib.save(nib.Nifti1Image(data, img.affine), new_image_path)
    return new_image_path


def main(image, reference, output_file, threshold=0.5, mask_path=None):

    # Apply threshold and use the new file paths
    image_thr = apply_threshold(image, threshold)
    reference_thr = apply_threshold(reference, threshold)

    overlap = Overlap()
    overlap.inputs.volume1 = image_thr
    overlap.inputs.volume2 = reference_thr

    if mask_path:
        # Optionally process mask similarly if thresholding is required
        mask_thr = apply_threshold(mask_path, threshold)
        overlap.inputs.mask_volume = mask_thr

    res = overlap.run()

    # Print the number of ROIs
    num_rois = len(res.outputs.roi_ji)
    print("Number of ROIs:", num_rois)

    with open(output_file, "w", newline="") as file:
        csvwriter = csv.writer(file)
        csvwriter.writerow(["ROI", "Jaccard Index"])
        for i, ji in enumerate(res.outputs.roi_ji):
            csvwriter.writerow([i + 1, ji])


if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print(
            "Usage: python calculate_metrics.py <volume1> <volume2> <output_csv> [<mask_path>]"
        )
        sys.exit(1)

    volume1 = sys.argv[1]
    volume2 = sys.argv[2]
    output_csv = sys.argv[3]
    mask_path = sys.argv[4] if len(sys.argv) == 5 else None

    main(volume1, volume2, output_csv, mask_path=mask_path)
