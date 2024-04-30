import sys
import numpy as np
import nibabel as nib

def dice_score(image1, image2):
    intersection = np.sum(image1 & image2)
    size_i1 = np.sum(image1)
    size_i2 = np.sum(image2)
    return 2 * intersection / (size_i1 + size_i2)

def jaccard_index(image1, image2):
    intersection = image1 & image2
    union = image1 | image2
    return np.mean(intersection / union)

def main(seg_path, ref_seg_path):
    seg_img = nib.load(seg_path).get_fdata() > 0
    ref_seg_img = nib.load(ref_seg_path).get_fdata() > 0
    dice = dice_score(seg_img, ref_seg_img)
    jaccard = jaccard_index(seg_img, ref_seg_img)
    print(f"Dice Score for {seg_path}: {dice:.4f}")
    print(f"Jaccard Index for {seg_path}: {jaccard:.4f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
