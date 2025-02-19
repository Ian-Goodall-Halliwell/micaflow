# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright The NiPreps Developers <nipreps@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# We support and encourage derived works from this project, please read
# about our expectations at
#
#     https://www.nipreps.org/community/licensing/
#
"""NiFreeze runner."""

from pathlib import Path

from nifreeze.cli.parser import parse_args
from nifreeze.data.base import BaseDataset
from nifreeze.estimator import Estimator


def main(argv=None) -> None:
    """
    Entry point.

    Returns
    -------
    None
    """
    args = parse_args(argv)

    # Open the data with the given file path
    dataset: BaseDataset = BaseDataset.from_filename(args.input_file)

    prev_model: Estimator | None = None
    for _model in args.models:
        estimator: Estimator = Estimator(
            _model,
            prev=prev_model,
        )
        prev_model = estimator

    _ = estimator.run(
        dataset,
        align_kwargs=args.align_config,
        omp_nthreads=args.nthreads,
        njobs=args.njobs,
        seed=args.seed,
    )

    # Set the output filename to be the same as the input filename
    output_filename: str = Path(args.input_file).name
    output_path: Path = Path(args.output_dir) / output_filename

    # Save the DWI dataset to the output path
    dataset.to_filename(output_path)


if __name__ == "__main__":
    main()
