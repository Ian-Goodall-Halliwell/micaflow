import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import scipy as sp

def get_mode(Array):
    def calculate_mode(data):
        unique_values, counts = np.unique(data, return_counts=True)
        max_count_index = np.argmax(counts)
        mode_value = unique_values[max_count_index]
        return(mode_value)

    # Calculate mode
    mode_value = [sp.stats.mode(Array.flatten(), keepdims=False, axis=None)[0], calculate_mode(Array.flatten())]
    # mode_value = float(np.argmax(np.bincount(Array.flatten().astype(int)))

    return mode_value

# Normalize brain image values
def mode_normalization(GM_mode, WM_mode, array):
    ## Mean mode between GM and WM
    BG=(GM_mode+WM_mode)/2.0

    # mode difference
    mode_diff = np.abs(BG - WM_mode)
    # Normalize array
    norm_wm = 100.0 * (array - WM_mode)/(mode_diff)
    norm_gm = 100.0 * (array - GM_mode)/(mode_diff)

    return(norm_gm, norm_wm)

def main(flair):
    flair_data=nib.load(flair).get_fdata()
    flair_gmN, flair_wmN = mode_normalization(115, 87, flair_data)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python normalization.py <flair_path>")
        sys.exit(1)
    main(sys.argv[1])
