"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
import numpy as np
import h5py
import io

from compox.training.TrainingSample import TrainingSample
from compox.training.TrainingDataset import TrainingDataset
from compox.database_connection.InMemoryConnection import InMemoryConnection
from compox.algorithm_utils.io_schemas import DataSchema


@pytest.fixture
def db_connection():
    return InMemoryConnection()


class MySchema(DataSchema):
    array: np.ndarray


def _post_file(r, name, db_connection) -> str:
    r = MySchema.model_validate(r)
    r = r.model_dump()
    bio = io.BytesIO()
    with h5py.File(bio, "w") as f:
        for key in r.keys():
            if r[key] is not None:
                f.create_dataset(
                    key,
                    data=r[key],
                )
    # upload response to minio
    db_connection.put_objects(
        "data-store",
        [name],
        [bio.getvalue()],
    )


def test_empty_dataset():
    """Test creating an empty training dataset."""
    dataset = TrainingDataset([])
    assert len(dataset) == 0, "Dataset length should be 0."
    assert dataset.get_sample_keys() == [], "Sample keys should be empty."
    assert dataset.get_all_file_lists() == [], "File lists should be empty."


def test_valid_dataset(db_connection):
    """Test creating a training dataset with valid samples."""
    sample_manifests = [
        {
            "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
            "files": [
                {"input": ["fid1", "fid2"], "target": ["fid1_y", "fid2_y"]},
                {"input": ["fid3"], "target": ["fid3_y"]},
            ],
            "tags": ["segmentation:skull", "author:jan"],
            "time_created": "2025-09-02T11:42:00Z",
        },
        {
            "sample_id": "4a9b2b65-1c3d-4a55-8a1d-7c2d4c0b9b91",
            "files": [
                {"input": ["fid4", "fid5"], "target": ["fid4_y", "fid5_y"]},
            ],
            "tags": ["segmentation:brain", "author:jane"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]

    samples = []
    for manifest in sample_manifests:
        samples.append(TrainingSample(db_connection, sample_manifest=manifest))

    dataset = TrainingDataset(samples)
    assert len(dataset) == 2, "Dataset length should be 2."
    assert dataset.get_sample_keys() == [
        "input",
        "target",
    ], "Sample keys mismatch."
    file_list = dataset.get_all_file_lists()
    assert len(file_list) == 2, "File list length should be 2."


def test_invalid_sample_in_dataset(db_connection):
    """Test creating a training dataset with an invalid sample."""
    valid_manifest = {
        "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
        "files": [
            {"input": ["fid1", "fid2"], "target": ["fid1_y", "fid2_y"]},
            {"input": ["fid3"], "target": ["fid3_y"]},
        ],
        "tags": ["segmentation:skull", "author:jan"],
        "time_created": "2025-09-02T11:42:00Z",
    }
    invalid_manifest = {
        "sample_id": "4a9b2b65-1c3d-4a55-8a1d-7c2d4c0b9b91",
        "files": [
            {"input": ["fid4", "fid5"], "invalid_field": ["fid4_y", "fid5_y"]},
        ],
        "tags": ["segmentation:brain", "author:jane"],
        "time_created": "2025-09-02T11:42:00Z",
    }

    valid_sample = TrainingSample(db_connection, sample_manifest=valid_manifest)
    invalid_sample = TrainingSample(
        db_connection, sample_manifest=invalid_manifest
    )
    with pytest.raises(ValueError):
        _ = TrainingDataset([valid_sample, invalid_sample])


def test_add_two_valid_datasets(db_connection):
    """Test creating a training dataset with valid samples."""
    sample_manifests_1 = [
        {
            "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
            "files": [
                {"input": ["fid1", "fid2"], "target": ["fid1_y", "fid2_y"]},
                {"input": ["fid3"], "target": ["fid3_y"]},
            ],
            "tags": ["segmentation:skull", "author:jan"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]
    sample_manifests_2 = [
        {
            "sample_id": "4a9b2b65-1c3d-4a55-8a1d-7c2d4c0b9b91",
            "files": [
                {"input": ["fid4", "fid5"], "target": ["fid4_y", "fid5_y"]},
            ],
            "tags": ["segmentation:brain", "author:jane"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]

    samples_1 = []
    for manifest in sample_manifests_1:
        samples_1.append(
            TrainingSample(db_connection, sample_manifest=manifest)
        )
    dataset_1 = TrainingDataset(samples_1)

    samples_2 = []
    for manifest in sample_manifests_2:
        samples_2.append(
            TrainingSample(db_connection, sample_manifest=manifest)
        )
    dataset_2 = TrainingDataset(samples_2)

    dataset = dataset_1 + dataset_2
    assert len(dataset) == 2, "Dataset length should be 2."
    assert dataset.get_sample_keys() == [
        "input",
        "target",
    ], "Sample keys mismatch."
    file_list = dataset.get_all_file_lists()
    assert len(file_list) == 2, "File list length should be 2."


def test_add_invalid_datasets(db_connection):
    """Test creating a training dataset with invalid file keys."""
    sample_manifests_1 = [
        {
            "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
            "files": [
                {"input": ["fid1", "fid2"], "target": ["fid1_y", "fid2_y"]},
                {"input": ["fid3"], "target": ["fid3_y"]},
            ],
            "tags": ["segmentation:skull", "author:jan"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]
    sample_manifests_2 = [
        {
            "sample_id": "4a9b2b65-1c3d-4a55-8a1d-7c2d4c0b9b91",
            "files": [
                {"input": ["fid4", "fid5"], "invalid_field": ["fid4_y"]},
            ],
            "tags": ["segmentation:brain", "author:jane"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]

    samples_1 = []
    for manifest in sample_manifests_1:
        samples_1.append(
            TrainingSample(db_connection, sample_manifest=manifest)
        )
    dataset_1 = TrainingDataset(samples_1)
    samples_2 = []
    for manifest in sample_manifests_2:
        samples_2.append(
            TrainingSample(db_connection, sample_manifest=manifest)
        )
    dataset_2 = TrainingDataset(samples_2)
    with pytest.raises(ValueError):
        _ = dataset_1 + dataset_2


def test_get_sample_keys(db_connection):
    """Test getting sample keys from the dataset."""
    sample_manifests = [
        {
            "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
            "files": [
                {"input": ["fid1", "fid2"], "target": ["fid1_y", "fid2_y"]},
                {"input": ["fid3"], "target": ["fid3_y"]},
            ],
            "tags": ["segmentation:skull", "author:jan"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]

    samples = []
    for manifest in sample_manifests:
        samples.append(TrainingSample(db_connection, sample_manifest=manifest))

    dataset = TrainingDataset(samples)
    keys = dataset.get_sample_keys()
    assert keys == ["input", "target"], "Sample keys mismatch."


def test_indexing(db_connection):
    """Test indexing into the dataset."""
    sample_manifests = [
        {
            "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
            "files": [
                {"input": ["fid1", "fid2"], "target": ["fid1_y", "fid2_y"]},
                {"input": ["fid3"], "target": ["fid3_y"]},
            ],
            "tags": ["segmentation:skull", "author:jan"],
            "time_created": "2025-09-02T11:42:00Z",
        },
        {
            "sample_id": "4a9b2b65-1c3d-4a55-8a1d-7c2d4c0b9b91",
            "files": [
                {"input": ["fid4", "fid5"], "target": ["fid4_y", "fid5_y"]},
            ],
            "tags": ["segmentation:brain", "author:jane"],
            "time_created": "2025-09-02T11:42:00Z",
        },
    ]

    samples = []
    for manifest in sample_manifests:
        samples.append(TrainingSample(db_connection, sample_manifest=manifest))

    dataset = TrainingDataset(samples)
    assert isinstance(dataset[0], TrainingSample), "Indexing by int failed."

    assert dataset[:, "input"] == [
        ["fid1", "fid2", "fid3"],
        ["fid4", "fid5"],
    ], "Indexing by slice and key failed."

    assert dataset[:, :] == [
        ["fid1", "fid2", "fid1_y", "fid2_y", "fid3", "fid3_y"],
        ["fid4", "fid5", "fid4_y", "fid5_y"],
    ], "Indexing by slice failed."
