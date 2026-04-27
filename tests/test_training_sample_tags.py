"""
Copyright 2026 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from __future__ import annotations

import json

import pytest

from compox.database_connection.InMemoryConnection import InMemoryConnection
from compox.training.TrainingSample import TrainingSample


@pytest.fixture
def db():
    db = InMemoryConnection()
    return db


def _seed_data_store(db: InMemoryConnection, file_ids: list[str]) -> None:
    db.put_objects("data-store", file_ids, [b"x" for _ in file_ids])


def _make_sample_manifest(sample_id: str, file_ids: list[str]) -> dict:
    return {
        "sample_id": sample_id,
        "files": [{"input": file_ids}],
        "tags": [],
        "time_created": "2026-01-01T00:00:00Z",
    }


def test_put_objects_sets_training_ref_zero(db):
    """
    Storing data-store objects should default training_ref=0 tags.
    """
    _seed_data_store(db, ["f1"])
    tags = db.get_object_tags("data-store", "f1")
    assert (
        tags.get("training_ref") == "0"
    ), "Expected training_ref=0 tag on new data-store object."


def test_promote_increments_training_ref(db):
    """
    Promoting a sample should increment training_ref for referenced files.
    """
    file_ids = ["f1", "f2"]
    _seed_data_store(db, file_ids)
    sample = TrainingSample(
        database_connection=db,
        sample_manifest=_make_sample_manifest("s1", file_ids),
    )

    sample._promote_files_to_training_files()

    for fid in file_ids:
        tags = db.get_object_tags("data-store", fid)
        assert (
            tags.get("training_ref") == "1"
        ), f"Expected training_ref=1 after promote for {fid}."


def test_promote_and_demote_reference_count(db):
    """
    Promote twice increments, demote decrements and removes tag at zero.
    """
    file_ids = ["f1"]
    _seed_data_store(db, file_ids)
    sample = TrainingSample(
        database_connection=db,
        sample_manifest=_make_sample_manifest("s1", file_ids),
    )

    sample._promote_files_to_training_files()
    sample._promote_files_to_training_files()
    tags = db.get_object_tags("data-store", "f1")
    assert (
        tags.get("training_ref") == "2"
    ), "Expected training_ref=2 after two promotions."

    sample._demote_files_from_training_files()
    tags = db.get_object_tags("data-store", "f1")
    assert (
        tags.get("training_ref") == "1"
    ), "Expected training_ref=1 after one demotion."
