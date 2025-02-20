import nibabel as nib
import numpy as np
from dipy.align.imaffine import AffineRegistration, MutualInformationMetric, AffineMap
from dipy.align.transforms import TranslationTransform3D, RigidTransform3D, AffineTransform3D
from nibabel.processing import resample_from_to
import subprocess
import sys
from dipy.io.image import load_nifti
from dipy.io.gradients import read_bvals_bvecs

def pad_to_multiple(data, divisor):
    """
    Pad the data symmetrically so that each dimension is a multiple of the given divisor.
    The padding is centered (i.e. extra pixel is added at the end if the padding is odd).
    """
    pad_width = []
    for d in data.shape:
        target = int(np.ceil(d / divisor) * divisor)
        pad_total = target - d
        pad_before = pad_total // 2
        pad_after = pad_total - pad_before
        pad_width.append((pad_before, pad_after))
    return np.pad(data, pad_width, mode='constant', constant_values=0)

# Load DWI NIfTI file
dwi_img, dwi_affine = load_nifti("sub-HC131_ses-01_dir-PA_dwi.nii.gz")

# Load b-values and b-vectors
bvals, bvecs = read_bvals_bvecs("sub-HC131_ses-01_dir-PA_dwi.bval", None)


print("DWI shape:", dwi_img.shape)
print("B-values:", np.unique(bvals))


from dipy.data import get_fnames
from dipy.denoise.patch2self import patch2self

denoised_dwi = patch2self(
dwi_img,
bvals,
model="ols",
shift_intensity=True,
clip_negative_vals=False,
b0_threshold=50,
b0_denoising=True
)

nib.save(nib.Nifti1Image(denoised_dwi, dwi_affine), "dwi_denoised.nii.gz")

# Load fixed and moving images
fixed_img = nib.load("mni_icbm152_t2_relx_tal_nlin_sym_09a.nii")
moving_img = nib.load("dwi_denoised.nii.gz")


moving_img = nib.Nifti1Image(moving_img.get_fdata()[..., 0], moving_img.affine, moving_img.header)
moving_img.to_filename("sub-HC131_ses-01_dir-PA_dwi_singlechannel.nii.gz")

subprocess.run(['hd-bet -i sub-HC131_ses-01_dir-PA_dwi_singlechannel.nii.gz -o moving_BET.nii.gz --save_bet_mask'], shell=True)
subprocess.run(['hd-bet -i mni_icbm152_t2_relx_tal_nlin_sym_09a.nii -o fixed_BET.nii.gz --save_bet_mask'], shell=True)

fixed_mask = nib.load("fixed_BET_bet.nii.gz")
fixed_img = nib.load("fixed_BET.nii.gz")
moving_mask = nib.load("moving_BET_bet.nii.gz")
moving_img = nib.load("moving_BET.nii.gz")





fixed_data = fixed_img.get_fdata()
fixed_data_mask = fixed_mask.get_fdata()
fixed_data[fixed_data_mask == 0] = 0
moving_data = moving_img.get_fdata()
moving_data_mask = moving_mask.get_fdata()
moving_data[moving_data_mask == 0] = 0

# Robustly scale fixed_data using the 1st and 99th percentiles.
p1_fixed, p99_fixed = np.percentile(fixed_data, (1, 99))
fixed_data = np.clip(fixed_data, p1_fixed, p99_fixed)
fixed_data = (fixed_data - p1_fixed) / (p99_fixed - p1_fixed + 1e-8)

# Robustly scale moving_data similarly.
p1_moving, p99_moving = np.percentile(moving_data, (1, 99))
moving_data = np.clip(moving_data, p1_moving, p99_moving)
moving_data = (moving_data - p1_moving) / (p99_moving - p1_moving + 1e-8)

moving_img = nib.Nifti1Image(moving_data, moving_img.affine, moving_img.header)
fixed_img = nib.Nifti1Image(fixed_data, fixed_img.affine, fixed_img.header)

# Resample moving image to fixed image space (same dimensions/affine)
moving_resampled_img = resample_from_to(moving_img, fixed_img)

# If the moving image still has 4 channels, select the first channel.
if moving_data.ndim == 4:
    moving_data = moving_data[..., 0]


# Pad both images so that each dimension is divisible by 16.
divisor = 16
fixed_data_padded = pad_to_multiple(fixed_data, divisor)
moving_data_padded = pad_to_multiple(moving_data, divisor)

# Save padded images to files (these paths are later used by register_tf.py).
fixed_padded_path = "fixed_padded.nii.gz"
moving_padded_path = "moving_padded.nii.gz"
new_fixed_img = nib.Nifti1Image(fixed_data_padded, fixed_img.affine, fixed_img.header)
nib.save(new_fixed_img, fixed_padded_path)
new_moving_img = nib.Nifti1Image(moving_data_padded, fixed_img.affine, moving_img.header)
nib.save(new_moving_img, moving_padded_path)

# ----- Start Affine Registration using DIPY -----

# Set up registration parameters.
nbins = 32
metric = MutualInformationMetric(nbins, None)
level_iters = [1000, 100, 10]
sigmas = [3.0, 1.0, 0.0]
factors = [4, 2, 1]
affreg = AffineRegistration(metric=metric,
                            level_iters=level_iters,
                            sigmas=sigmas,
                            factors=factors)

# Rigid registration as a starting point.
starting_affine = np.eye(4)
rigid = affreg.optimize(fixed_data_padded, moving_data_padded, RigidTransform3D(), None,
                        fixed_img.affine, moving_img.affine, starting_affine=starting_affine)
rigid_affine = rigid.affine

# Full affine registration.
affine = affreg.optimize(fixed_data_padded, moving_data_padded, AffineTransform3D(), None,
                         fixed_img.affine, moving_img.affine, starting_affine=rigid_affine)
affine_registered = affine.transform(moving_data_padded)

# Save the affine-registered moving image.
affine_registered_path = "affine_registered.nii.gz"
affine_registered_img = nib.Nifti1Image(affine_registered, fixed_img.affine)
nib.save(affine_registered_img, affine_registered_path)

print("Affine registration complete. Saved registered moving image to", affine_registered_path)

# ----- Call registration subprocess using the padded images -----
subprocess.run([
    sys.executable, "register_tf.py",
    "--moving", affine_registered_path, 
    "--fixed", fixed_padded_path,
    "--moved", "registered.nii.gz",
    "--model", "scripts/models/vxm_dense_brain_T1_3D_mse.h5",
    "--gpu", "0",
    "--warp", "warp.nii.gz",
])