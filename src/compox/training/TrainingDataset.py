"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from __future__ import annotations

from typing import Any
from compox.training.TrainingSample import TrainingSample


class TrainingDataset:
    """
    A class representing a dataset for training machine learning models. It
    is a collection of `TrainingSample` instances. Each sample in the dataset
    must have a consistent set of file keys.

    Parameters
    ----------
    samples : list[TrainingSample]
        A list of `TrainingSample` instances that make up the dataset.
    Raises
    ------
    ValueError
        If the samples have inconsistent file keys.
    """

    def __init__(self, samples: list[TrainingSample]):

        if not self._check_dataset_file_keys_consistency(samples):
            raise ValueError(
                "Inconsistent file keys across samples in the dataset"
            )

        self.samples = samples

    def _check_dataset_file_keys_consistency(
        self,
        samples: list[TrainingSample],
    ) -> bool:
        """
        Check if all samples have a consistent set of file keys.

        Parameters
        ----------
        samples : list[TrainingSample]
            The samples to check.
        Returns
        -------
        bool
            True if all samples have consistent file keys, False otherwise.
        """
        if len(samples) < 2:
            return True
        reference_keys = {
            file_key
            for file in samples[0].sample_manifest.files
            for file_key in file.keys()
        }
        for sample in samples[1:]:
            current_keys = {
                file_key
                for file in sample.sample_manifest.files
                for file_key in file.keys()
            }
            if current_keys != reference_keys:
                return False
        return True

    def _check_new_sample_file_keys_consistency(
        self, sample: TrainingSample
    ) -> bool:
        """
        Check if a new sample has a consistent set of file keys with the
        existing samples in the dataset. Returns True if the new sample is
        consistent, or if the dataset is currently empty (i.e., no samples to
        compare against).

        Parameters
        ----------
        sample : TrainingSample
            The new sample to check.
        Returns
        -------
        bool
            True if the new sample has consistent file keys, or if the dataset
            is empty; False otherwise.
        """
        if len(self.samples) == 0:
            return True
        else:
            reference_keys = {
                file_key
                for file in self.samples[0].sample_manifest.files
                for file_key in file.keys()
            }
            current_keys = {
                file_key
                for file in sample.sample_manifest.files
                for file_key in file.keys()
            }
            return current_keys == reference_keys

    def add_sample(self, sample: TrainingSample):
        """
        Add a new sample to the dataset.

        Parameters
        ----------
        sample : TrainingSample
            The new sample to add.
        Raises
        ------
        ValueError
            If the new sample has inconsistent file keys with the existing
            samples in the dataset.
        """
        if not self._check_new_sample_file_keys_consistency(sample):
            raise ValueError(
                "Inconsistent file keys across samples in the dataset"
            )
        self.samples.append(sample)

    def get_all_samples(self) -> list[TrainingSample]:
        """
        Get all samples in the dataset.
        Returns
        -------
        list[TrainingSample]
            A list of all samples in the dataset.
        """
        return self.samples

    def get_sample_by_id(self, sample_id: str) -> TrainingSample | None:
        """
        Get a sample by its ID.

        Parameters
        ----------
        sample_id : str
            The ID of the sample to retrieve.
        Returns
        -------
        TrainingSample | None
            The sample with the specified ID, or None if not found.
        """
        for sample in self.samples:
            if str(sample.sample_manifest.sample_id) == sample_id:
                return sample
        return None

    def get_sample_keys(self) -> list[str]:
        """
        Get the list of file keys from the samples.

        Returns
        -------
        list[str]
            A list of file keys.
        """
        if len(self.samples) == 0:
            return []
        return self.samples[0].get_key_list()

    def __getitem__(self, key: int | slice | tuple) -> Any:
        """
        Get samples or specific fields from samples using indexing.

        Parameters
        ----------
        key : int | slice | tuple
            The index or slice of samples to retrieve, or a tuple specifying
            sample selection and field selection.
        Returns
        -------
        Any
            The requested sample(s) or field(s).
        Raises
        ------
        TypeError
            If the key type is unsupported.
        """
        # single sample
        if isinstance(key, int):
            return self.samples[key]

        # slice of samples -> list[DatasetSample]
        if isinstance(key, slice):
            return self.samples[key]

        # tuple-based
        if isinstance(key, tuple) and len(key) == 2:
            samp_sel, subkey = key

            # apply to ONE sample
            if isinstance(samp_sel, int):
                s = self.samples[samp_sel]
                if isinstance(subkey, str):  # dataset[i, "field"]
                    return s[:, subkey]  # list[str] from that sample
                if isinstance(subkey, slice) and subkey == slice(
                    None
                ):  # dataset[i, :]
                    return s[:, :]  # list[...] from that sample
                return s[subkey]  # delegate as-is

            # apply to MANY samples -> always list-of-lists (no flatten)
            if isinstance(samp_sel, slice):
                subs = self.samples[samp_sel]

                if isinstance(
                    subkey, str
                ):  # dataset[i:j, "field"] or [:, "field"]
                    return [s[:, subkey] for s in subs]  # list[list[str]]

                if isinstance(subkey, slice) and subkey == slice(
                    None
                ):  # dataset[i:j, :]
                    return [s[:, :] for s in subs]  # list[list[Any]]

                # default: per-sample results (could be dict, str, list, etc.)
                return [s[subkey] for s in subs]

        raise TypeError(f"Unsupported key: {key!r}")

    def get_all_file_lists(self) -> list[list[dict[str, Any]]]:
        """
        Get the file lists from all samples in the dataset.

        Returns
        -------
        list[list[dict[str, Any]]]
            A list where each entry corresponds to a sample and contains a list
            of file dictionaries for that sample.
        """
        return [s.get_file_list() for s in self.samples]

    def __len__(self) -> int:
        """
        Get the number of samples in the dataset.

        Returns
        -------
        int
            The number of samples.
        """
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)

    def __repr__(self) -> str:
        # return a schematic representation of the dataset
        return f"TrainingDataset(num_samples={len(self.samples)}, schema={self.get_sample_keys()})"

    def __list__(self) -> list[dict]:
        return [s.get_file_list() for s in self.samples]

    def __add__(
        self, other: TrainingSample | TrainingDataset
    ) -> TrainingDataset:
        """
        Combine this dataset with another dataset or a single sample.

        Parameters
        ----------
        other : Type[TrainingSample] | Type[TrainingDataset]
            The other dataset or sample to combine with.
        Returns
        -------
        TrainingDataset
            A new dataset containing samples from both datasets.
        Raises
        ------
        TypeError
            If the other object is not a `TrainingDataset` or `TrainingSample`.
        ValueError
            If the samples have inconsistent file keys.
        """
        if isinstance(other, TrainingDataset):
            for sample in other.samples:
                if not self._check_new_sample_file_keys_consistency(sample):
                    raise ValueError(
                        "Inconsistent file keys across samples in the combined dataset"
                    )
            return TrainingDataset(samples=self.samples + other.samples)
        elif isinstance(other, TrainingSample):
            if not self._check_new_sample_file_keys_consistency(other):
                raise ValueError(
                    "Inconsistent file keys across samples in the combined dataset"
                )
            return TrainingDataset(samples=self.samples + [other])
        else:
            raise TypeError(
                "Can only add TrainingDataset or TrainingSample instances"
            )


if __name__ == "__main__":
    mock_db = "mock"

    sample1 = TrainingSample(
        database_connection=mock_db,
        sample_manifest={
            "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
            "files": [
                {"input": ["fid1", "fid1b"], "target": ["fid1_y"]},
                {"input": ["fid2"], "target": ["fid2_y"]},
                {"input": ["fid3"], "target": ["fid3_y"]},
            ],
            "tags": ["segmentation:skull", "author:jan"],
            "time_created": "2025-09-02T11:42:00+02:00",
        },
    )

    sample2 = TrainingSample(
        mock_db,
        sample_manifest={
            "sample_id": "4f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a91",
            "files": [
                {"input": ["fid4"], "target": ["fid4_y"]},
                {"input": ["fid5", "fid5b"], "target": ["fid5_y"]},
                {"input": ["fid6"], "target": ["fid6_y"]},
            ],
            "tags": ["modality:CT", "author:jana"],
            "time_created": "2025-09-02T11:42:00+02:00",
        },
    )
    sample3 = TrainingSample(
        database_connection=mock_db,
        sample_manifest={
            "sample_id": "5f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a92",
            "files": [
                {"input": ["fid7"], "target": ["fid7_y"]},
                {"input": ["fid8"], "target": ["fid8_y"]},
                {"input": ["fid9"], "target": ["fid9_y"]},
            ],
            "tags": ["modality:MRI", "author:janet"],
            "time_created": "2025-09-02T11:42:00+02:00",
        },
    )

    dataset = TrainingDataset(samples=[sample1, sample2])

    dataset = dataset + sample3
    print(f"Dataset has {len(dataset)} samples.")
