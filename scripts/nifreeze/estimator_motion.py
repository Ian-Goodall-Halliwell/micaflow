from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from tqdm import tqdm

from nifreeze.data.base import BaseDataset
from nifreeze.registration.ants import _prepare_registration_data, _run_registration

class Estimator:
    """Simplified estimator that only runs registration."""

    def run(self, dataset: BaseDataset, **kwargs) -> Estimator:
        """
        Run registration on every volume of the dataset.

        Parameters
        ----------
        dataset : BaseDataset
            The input dataset.
        kwargs
            Additional keyword arguments passed to the registration functions.
        
        Returns
        -------
        self : Estimator
        """
        # Use a plain iterator over all volumes
        n_vols = len(dataset)

        with TemporaryDirectory() as tmp_dir:
            print(f"Processing in <{tmp_dir}>")
            ptmp_dir = Path(tmp_dir)

            # Prepare brain mask (if available) for registration
            bmask_path = None
            if dataset.brainmask is not None:
                import nibabel as nb
                bmask_path = ptmp_dir / "brainmask.nii.gz"
                nb.Nifti1Image(dataset.brainmask.astype("uint8"), dataset.affine).to_filename(bmask_path)
            b0 = dataset.bzero
            with tqdm(total=n_vols, unit="vols.") as pbar:
                for i in range(n_vols):
                    pbar.set_description_str(f"Registering vol. <{i}>")
                    # For this simplified version, we use the original volume
                    # as both the fixed and moving image.
                    vol = dataset[i][0]
                    
                    # Prepare data for registration
                    # Here, we treat the input volume as its own synthetic target.
                    predicted_path, volume_path, init_path = _prepare_registration_data(
                        b0,
                        vol,
                        dataset.affine,
                        i,
                        ptmp_dir,
                        kwargs.pop("clip", "both")
                    )
                    
                    # Run registration (ANTs)
                    xform = _run_registration(
                        predicted_path,
                        volume_path,
                        i,
                        ptmp_dir,
                        init_affine=init_path,
                        fixedmask_path=bmask_path,
                        output_transform_prefix=f"ants-{i:05d}",
                        **kwargs,
                    )
                    
                    # Update dataset with the computed transform.
                    dataset.set_transform(i, xform.matrix)
                    pbar.update()
        return self