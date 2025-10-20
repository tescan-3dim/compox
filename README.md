# Compox
Compox is a simple Python execution engine for Tescan applications. It's purpose is to run data processing algorithms written in Python on the server and report the results to the client application such as Tescan 3D Viewer or Picannto.
## Installation
Compox can be installed through PyPI: 
```bash
pip install compox
```

You can also install the server by cloning this repository and installing it from source.

Note that some additional dependencies, such as MinIO executable for your operating system, will be downloaded on the first run of the server.

## Running the server
Once installed into your Python environment, Compox can be run using the `compox` command. This command is available in the virtual environment 
created during the setup process. Run the following command to list the available commands:

```bash
compox --help
```

It's recommended to start with generating an initial configuration file with `compox generate-config`. See the configuration options section below.
To see the usage of the `generate-config` command, you can run:

```bash
compox generate-config --help
```

To run the Compox, use the following command:

```bash
compox run --config /path/to/config.yaml
```

### Deploying algorithms
See Algorithm development tutorial for information about target structure of the deployable algorithms.

Once your algorithm is ready, you can use the `compox deploy-algorithms` command to deploy it to your server. 
To see the usage of the `deploy-algorithms` command, you can run:

```bash
compox deploy-algorithms --help
```

This command will read the algorithm definitions from the folder specified in your configuration file with the `deploy_algorithms_from` key
and deploy them to the server. For example:

```bash
compox deploy-algorithms --config /path/to/config.yaml
```

Note that the server does not need to be running in order to deploy the algorithms.


## Configuration
The server uses pydantic settings for configuration. The options can be either set as runtime arguments, in a yaml file, or using the `COMPOX__` environment variables, in corresponding order of precedence.

- Ensure all paths and URLs are correctly set before running the application.
- Adjust CUDA settings based on hardware capabilities.
- Logging paths should be accessible by the application to prevent errors.
- See the [configuration reference](#configuration-reference) below for detailed configuration options.

<details><summary>Configuration reference</summary>

<br>

### Compox Configuration Reference

| Section                         | Field                      | Default                            | Description                                                                 |
|----------------------------------|-----------------------------|------------------------------------|-----------------------------------------------------------------------------|
|                                  | `port`                    | `5461`                             | The main server port used to make requests                                 |
|                                  | `deploy_algorithms_from`  | `"./algorithms"`                   | Directory for algorithm deployment sources.                                |
|                                  | `log_path`                | `"LOG_DEFAULT:compox.log"`     | Path to the main log file (supports dynamic prefixes).                     |
|                                  | `config`                  | `None`                             | Optional config path override.                                             |
| `info`                           | `product_name`              | `"TESCAN 3D Backend"`              | Product display name.                                                      |
| `info`                           | `server_tags`               | `[]` → auto appends `"compox"` | Tags attached to the server. `"compox"` is added automatically.        |
| `info`                           | `group_name`                | `"TESCAN GROUP, a.s."`             | Name of the corporate group.                                               |
| `info`                           | `organization_name`         | `"TESCAN 3DIM, s.r.o."`            | Full name of the organization.                                             |
| `info`                           | `organization_domain`       | `"tescan3dim.com"`                 | Domain used in server configuration.                                       |
| `gui`                            | `algorithm_add_remove_in_menus` | `False`                        | Enables/disables GUI menu for algorithm management.                        |
| `gui`                            | `use_systray`               | `False`                            | Enables/disables systray GUI integration.                                  |
| `gui`                            | `icon_path`                 | Path to the installed package resource | Path to the systray icon (supports dynamic prefixes)               |
| `inference`                       | `device`                   | `"cuda"`                           | Device used for model inference (`"cpu"`, `"cuda"`, `"mps"`).              |
| `inference`                       | `cuda_visible_devices`     | `"0"`                              | Comma-separated list of visible CUDA GPUs.                                 |
| `storage`                        | `collection_prefix`         | `""`                               | Prefix applied to object store collections. (useful for AWS s3 store, where unique bucket names are needed)|
| `storage`                        | `data_store_expire_days`    | `1`                                | Number of days until stored datasets expire.                               |
| `storage`                        | `access_key_id`             | generated with `UUIDv4`            | Generated access key for storage backend. If `null` is provided, random UUIDv4 is generated. |
| `storage`                        | `secret_access_key`         | generated with `UUIDv4`            | Generated secret key for storage backend. If `null` is provided, random UUIDv4 is generated. |S
| `storage.backend_settings` (minio) | `provider`                | `"minio"`                          | Selected backend provider.                                                 |
| `storage.backend_settings` (minio) | `start_instance`         | `True`                              | Whether to start a local MinIO server.                                     |
| `storage.backend_settings` (minio) | `port`                   | `9091`                              | MinIO service port.                                                        |
| `storage.backend_settings` (minio) | `console_port`           | `9090`                              | MinIO admin console port.                                                  |
| `storage.backend_settings` (minio) | `executable_path`        | `"minio/minio_bin"`                 | Path to the MinIO binary (accepts dynamic prefixes).                |
| `storage.backend_settings` (minio) | `storage_path`           | `"minio/compox_store"`              | Storage directory used by MinIO (accepts dynamic prefixes).         |
| `storage.backend_settings` (minio) | `aws_region`             | `None`                              | Optional AWS compatibility region.                                         |
| `storage.backend_settings` (minio) | `s3_domain_name`         | `None`                              | Optional domain override for S3 compatibility.                             |
| `storage.backend_settings` (minio) | `s3_endpoint_url`        | Derived from `port`                 | Computed as `http://localhost:{port}`.                                     |
| `storage.backend_settings` (aws)   | `provider`                | `"aws"`                            | AWS backend selection.                                                     |
| `storage.backend_settings` (aws)   | `s3_endpoint_url`        | `None`                             | Optional override for S3 endpoint URL.                                     |
| `storage.backend_settings` (aws)   | `aws_region`             | `None`                             | AWS region (e.g. `us-east-1`).                                             |
| `storage.backend_settings` (aws)   | `s3_domain_name`         | `None`                             | Domain used for S3-style URLs.                                             |


Some fields in the Compox configuration (such as `log_path`, `icon_path`, etc.) support **dynamic prefixes** that resolve to OS-specific or runtime-specific paths. This allows for portability across platforms (e.g., Windows, Linux) and between development and production environments.

#### Supported Prefixes

| Prefix                   | Meaning (Resolved To...)                                                                 |
|--------------------------|------------------------------------------------------------------------------------------|
| `LOG_DEFAULT:`           | A platform-dependent log directory:                                                     |
|                          | - Windows: `%TEMP%/<organization>/<product>`                                            |
|                          | - Linux/macOS: `/var/log/<organization>/<product>`                                      |
| `PROGRAMDATA_DEFAULT:`   | A system-wide data directory (Windows only):                                            |
|                          | - e.g., `%PROGRAMDATA%/<organization>/<product>`                                        |
|                          | - On Linux/macOS, defaults to `"."` (current dir)                                       |

These are resolved **at runtime** in the `Settings.parse_paths()` validator method.
