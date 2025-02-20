from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeVar

from tqdm import tqdm
from typing_extensions import Self

from nifreeze.data.base import BaseDataset
from nifreeze.model.base import BaseModel, ModelFactory
from nifreeze.utils import iterators
import numpy as np
DatasetT = TypeVar("DatasetT", bound=BaseDataset)


class Filter:
    """Alters an input data object (e.g., downsampling)."""

    def run(self, dataset: DatasetT, **kwargs) -> DatasetT:
        return dataset


class Estimator:
    """Simplified estimator that only runs model predictions (fit_predict)."""

    __slots__ = ("_model", "_strategy", "_prev", "_model_kwargs", "_align_kwargs")

    def __init__(
        self,
        model: BaseModel | str,
        strategy: str = "random",
        prev: Estimator | Filter | None = None,
        model_kwargs: dict | None = None,
        **kwargs,
    ):
        self._model = model
        self._prev = prev
        self._strategy = strategy
        self._model_kwargs = model_kwargs or {}
        self._align_kwargs = kwargs or {}
        

    def run(self, dataset: DatasetT, **kwargs) -> Self:
        """
        Run only the model prediction (fit_predict) for each volume.

        Parameters
        ----------
        dataset : BaseDataset
            The input dataset.
        
        Returns
        -------
        self : Estimator
        """
        if self._prev is not None:
            result = self._prev.run(dataset, **kwargs)
            if hasattr(self._prev, "run"):
                dataset = result

        n_jobs = kwargs.get("n_jobs", None)
        iterfunc = getattr(iterators, f"{self._strategy}_iterator")
        index_iter = iterfunc(len(dataset), seed=kwargs.get("seed", None))
        dataset_length = len(dataset)
        # Initialize model
        if isinstance(self._model, str):
            # Factory creates the appropriate model and pipes arguments
            self._model = ModelFactory.init(
                model=self._model,
                dataset=dataset,
                **self._model_kwargs,
            )
        outputdata = np.zeros([dataset[0][0].shape[0], dataset[0][0].shape[1], dataset[0][0].shape[2], dataset_length])
        with tqdm(total=dataset_length, unit="vols.") as pbar:
            for i in index_iter:
                pbar.set_description_str(f"Predicting vol. <{i}>")

                test_set = dataset[i]
                # Run prediction only (fit_predict)
                predicted = self._model.fit_predict(i, n_jobs=n_jobs)
                outputdata[...,i] = predicted
                pbar.update()

        return outputdata

    # Additional methods (if any) can be defined below.