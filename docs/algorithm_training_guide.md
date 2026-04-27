## Developing `train()` in Compox algorithm runners

This guide is for algorithm developers implementing training logic in their Runner classes.
---

### Where `train()` is called

- Training is started by `POST /api/v0/train-algorithm`.
- The server creates a `TrainingHandler` and calls `runner.run_training(...)`.
- `BaseRunner.run_training()` sets status to `RUNNING`, calls `self.train(...)`, and on success calls `TrainingHandler.mark_as_completed()`.

Key implications:
- If `train()` raises, the training job is marked `FAILED`.
- If a stop request is posted, `TaskHandler` raises `TaskStoppedException` and status becomes `STOPPED`.

---

### Required method: `train(self, training_data, args)`

In `BaseRunner`, `train()` is the method you must override. It should **not** return anything.
The training task is considered complete when `train()` finishes without error.

Signature in `BaseRunner`:
```python
def train(self, training_data: list[str], args: dict | None = None) -> None:
    ...
```
---

### Fetching training data

You receive `training_data` as a list of **training sample IDs**.
Use the `TrainingHandler` helpers (available through `BaseRunner`) to load datasets:

```python
dataset = self.get_training_dataset(training_sample_ids)
```

From there, you can use these **training-specific save/load helpers** on the runner.
All of them are implemented by `TrainingHandler` and surfaced via `BaseRunner`.

### Saving / downloading to TempStore

**save_training_files_to_temp_store(folder_path, files, schema, parallel=True)**
- Use when you already have **in‑memory** data (e.g., numpy arrays) and want to
  persist them to the TempStore before training.
- Inputs:
  - `folder_path`: target subfolder in TempStore
  - `files`: list of dicts (each dict is a logical file with HDF5 keys/values)
  - `schema`: Pydantic `DataSchema` for validation
- Output:
  - list of `Path` objects pointing to saved files in TempStore

**download_files_to_temp_store(folder_path, file_ids, schema, batch_size=8, *keys)**
- Use when you have a **flat list** of file IDs from `data-store`.
- Inputs:
  - `file_ids`: list of object IDs in `data-store`
  - `schema`: Pydantic `DataSchema` for validation
  - `*keys`: optional HDF5 keys to extract (if omitted, all keys)
- Output:
  - list of `Path` objects in TempStore
- Notes:
  - Downloads in batches to reduce memory spikes.

**download_dataset_to_temp_store(dataset, schemas)**
- Use when you have **training samples** and want the full manifest structure preserved.
- Inputs:
  - `dataset`: a `TrainingDataset` created from sample IDs
  - `schemas`: dict mapping sample keys to Pydantic schemas
    (e.g. `{"input": InputSchema, "target": TargetSchema}`)
- Output:
  - `local_samples`: list of samples, each sample is a list of dicts whose values are
    **local Paths** in TempStore.
- Temp layout:
  - `<temp>/<sample_id>/<file_index>/<key>/...`

### Loading from TempStore

**load_files_from_temp_store(paths, parallel=True, *keys)**
- Use when you already have a list of TempStore paths.
- Inputs:
  - `paths`: list of file paths in TempStore
  - `*keys`: optional HDF5 keys to extract (if omitted, all keys)
- Output:
  - list of dicts (in‑memory data)

**load_dataset_from_temp_store(local_samples)**
- Use with the output from `download_dataset_to_temp_store(...)`.
- Input:
  - `local_samples`: list-of-list-of-dict structure with TempStore paths
- Output:
  - Same structure, but values are **loaded data dicts** instead of paths.

### Schema validation

All save/download methods validate against Pydantic `DataSchema` definitions
(see `compox.algorithm_utils.io_schemas`). The schema defines expected HDF5 keys,
their types, and any validation rules.

---

### Reporting progress and state

Use these methods during training:

```python
self.set_progress(0.5)  # float in [0.0, 1.0]
self.set_state({"epoch": 3, "loss": 0.12})
self.log_message("Epoch 3/10", logging_level="INFO")
```

- `set_progress` updates `TrainingRecord.progress`.
- `set_state` overwrites the current `TrainingRecord.state`.
- `log_message` appends to the training log.

---

### Saving checkpoints (training outputs)

To persist a trained model or intermediate state, call:
```python
checkpoint_id = self.save_checkpoint(
    {"my_asset.pt": model_bytes},
    properties={"stage": "intermediate", "epoch": 3, "loss": 0.12},
)
```

Important rules:
- Keys in the checkpoint dict **must match asset paths** already defined in the algorithm.
  `TrainingHandler.save_checkpoint()` validates this against the algorithm’s assets.
- The checkpoint is stored in `algorithm-checkpoint-store`.
- Each saved checkpoint ID is appended to `TrainingRecord.output_checkpoint_ids`.

Training completion:
- `TrainingHandler.mark_as_completed()` **requires at least one checkpoint**.
  If none were saved, the training is marked failed.

---

### Stopping behavior

If a stop request is posted:
- `TaskHandler._check_for_stop_request()` raises `TaskStoppedException`.
- Training is marked `STOPPED`.

Recommendation: Keep your training loop responsive so stop requests can be detected quickly.

---

### Example skeleton

```python
from compox.algorithm_utils.BaseRunner import BaseRunner
from compox.algorithm_utils.io_schemas import DataSchema
import numpy as np

class InputSchema(DataSchema):
    image: np.ndarray

class TargetSchema(DataSchema):
    mask: np.ndarray

class Runner(BaseRunner):
    def load_assets(self):
        # load model weights defined in algorithm assets
        self.weights = self.fetch_asset("model.pt")

    def train(self, training_data: list[str], args: dict | None = None):
        # 1) Build dataset from sample IDs
        dataset = self.get_training_dataset(training_data)

        # 2) Download full dataset to TempStore using schemas for each key
        schemas = {"input": InputSchema, "target": TargetSchema}
        local_samples = self.download_dataset_to_temp_store(dataset, schemas)

        # 3) Load the dataset into memory
        in_memory = self.load_dataset_from_temp_store(local_samples)

        # 4) Optional: derive extra files and save them to TempStore
        derived = []
        for sample in in_memory:
            for file_dict in sample:
                if "input" in file_dict:
                    img = file_dict["input"]["image"]
                    norm = (img - img.min()) / (img.max() - img.min() + 1e-8)
                    derived.append({"image": norm.astype(np.float32)})
        derived_paths = self.save_training_files_to_temp_store(
            "derived", derived, InputSchema, parallel=True
        )

        # 5) Load derived files back (flat load)
        derived_loaded = self.load_files_from_temp_store(derived_paths)

        epochs = args.get("num_epochs", 10)
        for epoch in range(epochs):
            # training step...
            self.log_message(f"Epoch {epoch+1}/{epochs}")
            self.set_progress(float(epoch + 1) / epochs)
            self.set_state(
                {
                    "epoch": epoch + 1,
                    "samples": len(in_memory),
                    "derived": len(derived_loaded),
                }
            )

            # intermediate checkpoint
            self.save_checkpoint(
                {"model.pt": b"model-bytes"},
                properties={
                    "stage": "intermediate",
                    "epoch": epoch + 1,
                },
            )

        # final checkpoint (required)
        self.save_checkpoint(
            {"model.pt": b"final-model-bytes"},
            properties={"stage": "final", "epoch": epochs},
        )
```

---

### Common pitfalls

- **No checkpoints saved:** training will fail at completion.
- **Checkpoint keys don’t match assets:** `save_checkpoint()` raises.
- **Long loops without progress/logs:** client sees “stalled” training.
- **Mutating cached assets:** assets loaded in `load_assets()` are protected from reassignment.
