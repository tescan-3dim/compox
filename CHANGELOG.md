# v3.0.0 (27-04-2026)
## Added
- Algorithm training workflow: samples, training jobs, checkpoints, training state/progress/logging, and stop support.
- New API routes for `/api/v0/sample`, `/api/v0/train-algorithm`, `/api/v0/training/{id}`, `/api/v0/checkpoint/*`, and deploy management.
- Algorithm export support via zip streaming, including optional minor-version and checkpoint-based asset override.
- Local and async algorithm deployment endpoints, removable/exportable algorithm flags, and deletion of removable algorithms.
- `BaseRunner` training helpers: `train`, `run_training`, checkpoint saving, training dataset loading, temp-store file helpers, state handling, and progress/log methods.
- New `compox.training` package with `TrainingHandler`, `TrainingSample`, `TrainingDataset`, `TempStore`, checkpoint manifests, and training task runners.
- CLI commands for local deploy, algorithm delete, algorithm export, selective `deploy-algorithms`, config overrides, and improved test execution.
- Stop-request infrastructure for executions and training, with `STOPPED` status.
- Additional storage collections: `training-store`, `sample-store`, `algorithm-checkpoint-store`, `stop-requests`, and `deploy-store`.
- Logging configuration with separate console/file levels and reduced console noise for polling/file-transfer logs.
- Documentation for execution client workflow, training client workflow, algorithm training, updated deployment, and security notes.
- Test coverage for training, samples, checkpoints, deployment endpoints, export, versioning, stop execution, logging, CLI, and server utilities.

## Changed
- Algorithm metadata now tracks multiple minor versions plus `latest_algorithm_minor_version`.
- Algorithm config supports `training_parameters`, `removable`, `exportable`, `displayed_name`, and float `decimal_precision`.
- Execution requests and records now support `checkpoint_id`, `algorithm_minor_version`, and `resolved_execution_device`.
- Algorithm deployment now deduplicates modules/assets by content and supports zip deployment.
- Algorithm manager deletion now cleans related modules, assets, checkpoints, and minor versions more precisely.
- S3 lifecycle handling now applies separate expiration policies for data, execution, training, deploy, and stop-request stores.
- Default documented service ports changed to Compox `5481`, MinIO console `5482`, and MinIO API `5483`.
- Dependencies were relaxed/updated: `numpy>=1.26,<3`, `requests>=2.32.3`, added `tomli` for Python <3.11, removed `natsort`.

## Fixed
- Hotfix commits removed accidental merge-conflict markers and restored accidentally commented code.
- Improved systray/server shutdown handling, especially for frozen Windows builds.
- Improved task failure/stopped handling so records are updated with terminal status, completion time, logs, and file transfer stats.
- Improved algorithm import/export path handling with traversal checks and safer reconstruction.

## Compatibility Notes
- `AlgorithmRegisteredResponse` changed from a single `algorithm_minor_version` to `algorithm_minor_versions` plus `latest_algorithm_minor_version`.
- New API surfaces expose local-path deployment and algorithm deletion; these should be treated as administrative/trusted operations.

# v2.1.2 (16-02-2026)

- Updated links in README.md

# v2.1.1 (13-02-2026)

- Added ParticleSeg3D tutorial
- Critical bugfixes

# v2.1.0 (11-12-2025)

- Improved docs and tutorials section
- General data schema

# v2.0.0 (24-11-2025)

- Initial release