import numpy as np
import nibabel as nib
from scipy.ndimage import map_coordinates
from EPI_MRI.EPIMRIDistortionCorrection import DataObject, EPIMRIDistortionCorrection
from optimization.ADMM import myAvg1D, myDiff1D, myLaplacian1D, JacobiCG, ADMM
import torch
import ants
import argparse


def run(data_image, reverse_image, output_name):
    # Fix dimensions
    im1 = nib.load(data_image)
    affine = im1.affine
    im1 = im1.get_fdata()
    im2 = nib.load(reverse_image).get_fdata()

    im1 = im1[:, :, :, 0]
    im2 = im2[:, :, :, 0]

    # Convert images to ANTsImage
    ants_im1 = ants.from_numpy(im1)
    ants_im2 = ants.from_numpy(im2)

    # Perform affine + rigid registration
    registration = ants.registration(
        fixed=ants_im1, moving=ants_im2, type_of_transform="Affine"
    )

    # Get the registered image
    registered_im2 = registration["warpedmovout"].numpy()

    # Save the registered image
    registered_im2_nifti = nib.Nifti1Image(registered_im2, affine)
    nib.save(registered_im2_nifti, "registered_im2.nii.gz")
    nib.save(nib.Nifti1Image(im1, affine), "registered_im1.nii.gz")
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    # load the image and domain information
    # change this function call to be the filepath for your data
    data = DataObject(
        "registered_im1.nii.gz",
        "registered_im2.nii.gz",
        2,
        device=device,
    )
    # set-up the objective function
    loss_func = EPIMRIDistortionCorrection(
        data,
        300,
        1e-4,
        averaging_operator=myAvg1D,
        derivative_operator=myDiff1D,
        regularizer=myLaplacian1D,
        rho=1e3,
        PC=JacobiCG,
    )
    # initialize the field map
    B0 = loss_func.initialize(blur_result=True)
    # set-up the optimizer
    # change path to be where you want logfile and corrected images to be stored
    resultspath = f"topup-warp"
    opt = ADMM(
        loss_func,
        max_iter=500,
        rho_max=1e6,
        rho_min=1e1,
        max_iter_gn=1,
        max_iter_pcg=20,
        verbose=True,
        path=resultspath,
    )
    # optimize!
    opt.run_correction(B0)
    # save field map and corrected images
    opt.apply_correction()
    # save the field map

    fieldmap = nib.load(resultspath + "-EstFieldMap.nii.gz").get_fdata()

    # Ensure the warpfield has the same dimensions as the image
    if fieldmap.shape[1] > im1.shape[1]:
        fieldmap = fieldmap[:, : im1.shape[1], :]

    def apply_warpfield_y(image, warpfield):
        """
        Apply a warpfield to an image along the second dimension (y-axis).

        Parameters
        ----------
        image : numpy.ndarray
            The input image to be warped.
        warpfield : numpy.ndarray
            The warpfield to apply to the image.

        Returns
        -------
        warped_image : numpy.ndarray
            The warped image.
        """
        # Create a grid of coordinates
        coords = np.meshgrid(
            np.arange(image.shape[0]),
            np.arange(image.shape[1]),
            np.arange(image.shape[2]),
            indexing="ij",
        )

        # Apply the warpfield to the coordinates along the second dimension (y-axis)
        warped_coords = [coords[0], coords[1] + warpfield, coords[2]]

        # Interpolate the image at the warped coordinates
        warped_image = map_coordinates(image, warped_coords, order=1, mode="nearest")

        return warped_image

    # Apply the warpfield to the image along the second dimension
    warped_im1_y = apply_warpfield_y(im1, fieldmap)

    # Save the warped image
    warped_im1_y_nifti = nib.Nifti1Image(warped_im1_y, affine)
    nib.save(warped_im1_y_nifti, output_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run distortion correction on DWI images.")
    parser.add_argument("--data_image", type=str, required=True, help="Path to the data image (NIfTI file).")
    parser.add_argument("--reverse_image", type=str, required=True, help="Path to the reverse phase-encoded image (NIfTI file).")
    parser.add_argument("--output_name", type=str, required=True, help="Output name for the corrected image (NIfTI file).")

    args = parser.parse_args()
    
    run(args.data_image, args.reverse_image, args.output_name)
