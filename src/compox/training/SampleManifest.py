"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from __future__ import annotations
from typing import Any, Dict, List

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
)


class SampleManifest(BaseModel):
    model_config = ConfigDict(
        extra="ignore",  # ignore unknown top-level keys
        populate_by_name=True,
        str_max_length=10_000,
        json_schema_extra={
            "example": {
                "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
                "name": "segmentation-train-v1",
                "files": [
                    {
                        "input": ["fid_0001", "fid_0002"],
                        "target": ["fid_0001_y", "fid_0002_y"],
                    },
                    {
                        "input": ["fid_0003", "fid_0004", "fid_0005"],
                        "target": ["fid_0003_y", "fid_0004_y", "fid_0005_y"],
                    },
                ],
                "tags": ["segmentation:skull", "author:jan"],
                "time_created": "2025-09-02T11:42:00Z",
            }
        },
    )

    # Fields
    sample_id: str = Field(..., description="Sample identifier (UUID).")
    files: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "List of files in the sample. Each entry is a dictionary "
            "with arbitrary keys (e.g. 'input', 'target') mapping to lists of file IDs."
        ),
        min_length=1,
    )
    tags: List[str] = Field(
        default_factory=list,
        description=(
            "List of tags associated with the sample. Tags can be defined either "
            "as a list of strings (e.g. ['train', 'segmentation']) or as a key-value pair "
            "separated by colon (e.g. ['segmentation:skull', 'author:jan'])."
        ),
    )
    time_created: str = Field(
        ..., description="Creation time (ISO 8601 string)."
    )

    @field_validator("tags", mode="before")
    @classmethod
    def _norm_tags(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            raise TypeError("tags must be a list of strings")
        # strip, lower, drop empties, dedupe (preserve order)
        seen, out = set(), []
        for t in v:
            if not isinstance(t, str):
                raise TypeError("tags must be a list of strings")
            tt = t.strip().lower()
            if tt and tt not in seen:
                seen.add(tt)
                out.append(tt)
        return out

    @model_validator(mode="after")
    def _files_basic_check(self) -> "SampleManifest":
        if not isinstance(self.files, list):
            raise TypeError("files must be a list of dictionaries")
        for i, item in enumerate(self.files):
            if not isinstance(item, dict):
                raise TypeError(f"files[{i}] must be a dict")
        # the keys must be the same in all dicts
        if self.files:
            keys = set(self.files[0].keys())
            for i, item in enumerate(self.files[1:], start=1):
                if set(item.keys()) != keys:
                    raise ValueError(
                        f"files[{i}] has different keys than files[0]\n",
                        f"Expected keys: {keys}, got: {set(item.keys())}",
                    )
        return self


if __name__ == "__main__":
    raw = {
        "sample_id": "3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90",
        "files": [
            {
                "input": ["fid_0001", "fid_0002"],
                "target": ["fid_0001_y", "fid_0002_y"],
            },
            {
                "input": ["fid_0003", "fid_0004", "fid_0005"],
                "target": ["fid_0003_y", "fid_0004_y", "fid_0005_y"],
            },
        ],
        "tags": ["segmentation:skull", "author:jan"],
        "time_created": "2025-09-02T11:42:00+02:00",
    }

    m = SampleManifest(**raw)
    print(m.sample_id)  #'3f8b2b65-1c3d-4a55-8a1d-7c2d4c0b9a90'
    print(m.tags)  # ['train', 'segmentation']
    print(m.model_dump())
