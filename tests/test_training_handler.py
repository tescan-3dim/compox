"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
import numpy as np
import io
import h5py
import json

from compox.training.DebuggingTrainingHandler import (
    DebuggingTrainingHandler,
)
from compox.database_connection.InMemoryConnection import InMemoryConnection
from compox.training.TempStore import TempStore
from compox.training.TrainingSample import TrainingSample
from compox.algorithm_utils.io_schemas import DataSchema


class MySchema(DataSchema):
    array: np.ndarray


# function to upload a file to the in memory database
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


@pytest.fixture
def db_connection():
    db_connection = InMemoryConnection()
    files_ids = [
        "fid1",
        "fid1b",
        "fid1_y",
        "fid2",
        "fid2_y",
        "fid3",
        "fid3_y",
        "fid4",
        "fid4_y",
        "fid5",
        "fid5b",
        "fid5_y",
        "fid6",
        "fid6_y",
        "fid7",
        "fid7_y",
        "fid8",
        "fid8_y",
        "fid9",
        "fid9_y",
    ]
    data_arrays = [
        {"array": np.random.rand(10, 10, 10).astype(np.float32)}
        for _ in files_ids
    ]
    for fid, data in zip(files_ids, data_arrays):
        _post_file(data, fid, db_connection)
    # here we create a training with three samples composed of the above files
    sample1 = TrainingSample(
        db_connection,
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
        db_connection,
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
        db_connection,
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

    # this saves the sample manifests to the storage
    sample1.save_sample_manifest()
    sample2.save_sample_manifest()
    sample3.save_sample_manifest()
    training_record = {
        "training_id": "test_training",
        "status": "PENDING",
        "progress": 0.0,
        "time_started": str("2025-09-02T11:42:00+02:00"),
        "time_completed": None,
        "log": None,
        "training_data": [
            str(sample1.sample_id),
            str(sample2.sample_id),
            str(sample3.sample_id),
        ],
        "state": {},
        "algorithm_id": "algid1",
        "output_algorithm_id": None,
    }
    db_connection.put_objects(
        "training-store",
        [training_record["training_id"]],
        [json.dumps(training_record)],
    )
    return db_connection


def test_handler_initialization(db_connection):
    """Test initializing the DebuggingTrainingHandler."""
    with TempStore() as temp_store:
        handler = DebuggingTrainingHandler(
            database_connection=db_connection,
            training_id="test_training",
            temp_store=temp_store,
        )
        assert handler.database_connection == db_connection
        assert handler.task_id == "test_training"
        assert handler.temp_store == temp_store
