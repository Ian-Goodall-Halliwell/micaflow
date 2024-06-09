import sys
import nipype.algorithms.metrics as nm

def main(image, reference, output_file):
    
    overlap = nm.Overlap()
    overlap.inputs.volume1 = image
    overlap.inputs.volume2 = reference
    res = overlap.run()

    with open(output_file, 'w') as file:
        file.write(f"Overall Jaccard Index: {res.outputs.jaccard}\n")
        file.write("Jaccard Indices per ROI:\n")
        for i, roi_ji in enumerate(res.outputs.roi_ji):
            file.write(f"ROI {i}: {roi_ji}\n")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

# python3 calculate_metrics.py
#   /Users/cerys/Documents/MICA/test_data/test_outputs/sub-HC062/sub-HC062_ses-03_space-MNI152_T1w.nii.gz
#   /Users/cerys/Documents/MICA/micaflow/micaflow/atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz
#   /Users/cerys/Documents/MICA/test_data/test_outputs/sub-HC062/ses-03/sub-HC062_ses-03_jaccard_indices.csv

