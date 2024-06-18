import sys
import csv
from nipype.algorithms.metrics import Overlap

def main(image, reference, output_file):
    
    overlap = Overlap()
    overlap.inputs.volume1 = image
    overlap.inputs.volume2 = reference
    #overlap.inputs.bg_overlap = True (Consider zeros as a label)
    res = overlap.run()

    with open(output_file, 'w', newline='') as file:
        csvwriter = csv.writer(file)
        csvwriter.writerow(['ROI', 'Jaccard Index'])
        for i, ji in enumerate(res.outputs.roi_ji):
            csvwriter.writerow([i + 1, ji]) 

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

'''
python3 calculate_metrics.py \
/Users/cerys/Documents/MICA/test_data/test_outputs/sub-HC062/sub-HC062_ses-03_space-MNI152_T1w.nii.gz \
/Users/cerys/Documents/MICA/micaflow/micaflow/atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz \
/Users/cerys/Documents/MICA/test_data/test_outputs/sub-HC062/ses-03/sub-HC062_ses-03_jaccard_indices.csv
'''