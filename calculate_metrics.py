import sys
import csv
from nipype.algorithms.metrics import Overlap
import nibabel as nib

def apply_threshold(image_path, threshold=0.5):
    img = nib.load(image_path)
    data = img.get_fdata()
    data[data < threshold] = 0
    nib.save(nib.Nifti1Image(data, img.affine), image_path)

def main(image, reference, output_file, threshold=0.5, mask_path=None):

    # Apply threshold to remove small regions
    apply_threshold(image, threshold)
    apply_threshold(reference, threshold)
    
    overlap = Overlap()
    overlap.inputs.volume1 = image
    overlap.inputs.volume2 = reference

    if mask_path:
        overlap.inputs.mask_volume = mask_path

    res = overlap.run()

    # Print the number of ROIs
    num_rois = len(res.outputs.roi_ji)
    print("Number of ROIs:", num_rois)

    with open(output_file, 'w', newline='') as file:
        csvwriter = csv.writer(file)
        csvwriter.writerow(['ROI', 'Jaccard Index'])
        for i, ji in enumerate(res.outputs.roi_ji):
            csvwriter.writerow([i + 1, ji]) 

if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python calculate_metrics.py <volume1> <volume2> <output_csv> [<mask_path>]")
        sys.exit(1)
    
    volume1 = sys.argv[1]
    volume2 = sys.argv[2]
    output_csv = sys.argv[3]
    mask_path = sys.argv[4] if len(sys.argv) == 5 else None

    main(volume1, volume2, output_csv, mask_path=mask_path)