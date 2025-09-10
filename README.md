# T3D server
T3D server is a simple Python REST API execution engine with a MinIO storage backend. It allows storing data, deploying algorithms, submitting execution requests and retrieving the results. It can be used to extend functionality of Tescan 3D software suite (e.g. 3D Viewer, Picannto)

## Installation
T3D server can be installed through PyPI: 
```bash
pip install t3d-server
```

You can also install the server by cloning this repository and installing it from source.

Note that some additional dependencies, such as MinIO executable for your operating system, will be downloaded on the first run of the server.

## Running the server
Once installed into your Python environment, it's recommended to generate an initial configuration file with `t3d-server generate-config`. 
To see the available options for the `generate-config` command, you can run:

```bash
t3d-server generate-config --help
```

The T3D server can be run using the `t3d-server` command. This command is available in the virtual environment created during the setup process. Run the following command to list the available commands:

```bash
t3d-server --help
```

To run the T3D server, use the following command:

```bash
t3d-server run --config /path/to/config.yaml
```

### Deploy algorithms
See the T3D server algorithm development tutorial [TBD]. Once your algorithm is ready, you can use the `t3d-server deploy-algorithms` command to deploy it to your server. This command will read the algorithm definitions from the specified configuration file and deploy them to the server. For example:

```bash
t3d-server deploy-algorithms --config /path/to/config.yaml
```

To see the available options for the `deploy-algorithms` command, you can run:

```bash
t3d-server deploy-algorithms --help
```

## Configuration
The server uses pydantic settings for configuration. The configuration can be either set in a yaml file or as arguments when running the server.

- Ensure all paths and URLs are correctly set before running the application.
- Adjust CUDA settings based on hardware capabilities.
- Logging paths should be accessible by the application to prevent errors.
- MinIO settings must align with whether it is run locally or through an external S3 service.
- See the [configuration reference](#configuration-reference) below for detailed configuration options.

<details><summary>Configuration reference</summary>

<br>

### T3D Server Configuration Reference

| Section                         | Field                      | Default                            | Description                                                                 |
|----------------------------------|-----------------------------|------------------------------------|-----------------------------------------------------------------------------|
|                                  | `port`                    | `5461`                             | The main server port used to make requests                                 |
|                                  | `deploy_algorithms_from`  | `"./algorithms"`                   | Directory for algorithm deployment sources.                                |
|                                  | `log_path`                | `"LOG_DEFAULT:t3d_server.log"`     | Path to the main log file (supports dynamic prefixes).                     |
|                                  | `config`                  | `None`                             | Optional config path override.                                             |
| `info`                           | `product_name`              | `"TESCAN 3D Backend"`              | Product display name.                                                      |
| `info`                           | `server_tags`               | `[]` → auto appends `"t3d_server"` | Tags attached to the server. `"t3d_server"` is added automatically.        |
| `info`                           | `group_name`                | `"TESCAN GROUP, a.s."`             | Name of the corporate group.                                               |
| `info`                           | `organization_name`         | `"TESCAN 3DIM, s.r.o."`            | Full name of the organization.                                             |
| `info`                           | `organization_domain`       | `"tescan3dim.com"`                 | Domain used in server configuration.                                       |
| `info`                           | `version`                   | `"0.1"`                            | Semantic version of the server release.                                   |
| `gui`                            | `algorithm_add_remove_in_menus` | `False`                        | Enables/disables GUI menu for algorithm management.                        |
| `gui`                            | `use_systray`               | `False`                            | Enables/disables systray GUI integration.                                  |
| `gui`                            | `icon_path`                 | `"../t3d_server/resources/t3dbackend.ico"` | Path to the systray icon (supports dynamic prefixes)               |
| `storage`                        | `collection_prefix`         | `""`                               | Prefix applied to object store collections. (useful for AWS s3 store, where unique bucket names are needed)|
| `storage`                        | `data_store_expire_days`    | `1`                                | Number of days until stored datasets expire.                               |
| `storage`                        | `access_key_id`             | `UUIDv4`                           | Generated access key for storage backend. If `null` is provided, random UUIDv4 is generated. |
| `storage`                        | `secret_access_key`         | `UUIDv4`                           | Generated secret key for storage backend. If `null` is provided, random UUIDv4 is generated. |S
| `storage.backend_settings` (minio) | `provider`                | `"minio"`                          | Selected backend provider.                                                 |
| `storage.backend_settings` (minio) | `start_instance`         | `True`                             | Whether to start a local MinIO server.                                     |
| `storage.backend_settings` (minio) | `port`                   | `9091`                             | MinIO service port.                                                        |
| `storage.backend_settings` (minio) | `console_port`           | `9090`                             | MinIO admin console port.                                                  |
| `storage.backend_settings` (minio) | `executable_path`        | `"minio/minio_bin"`                | Path to the MinIO binary (accepts dynamic prefixes).                |
| `storage.backend_settings` (minio) | `storage_path`           | `"minio/t3d_server_store"`         | Storage directory used by MinIO (accepts dynamic prefixes).         |
| `storage.backend_settings` (minio) | `aws_region`             | `None`                             | Optional AWS compatibility region.                                         |
| `storage.backend_settings` (minio) | `s3_domain_name`         | `None`                             | Optional domain override for S3 compatibility.                             |
| `storage.backend_settings` (minio) | `s3_endpoint_url`        | Derived from `port`                | Computed as `http://localhost:{port}`.                                     |
| `storage.backend_settings` (aws)   | `provider`                | `"aws"`                            | AWS backend selection.                                                     |
| `storage.backend_settings` (aws)   | `s3_endpoint_url`        | `None`                             | Optional override for S3 endpoint URL.                                     |
| `storage.backend_settings` (aws)   | `aws_region`             | `None`                             | AWS region (e.g. `us-east-1`).                                             |
| `storage.backend_settings` (aws)   | `s3_domain_name`         | `None`                             | Domain used for S3-style URLs.                                             |
| `inference`                       | `device`                   | `"cuda"`                           | Device used for model inference (`"cpu"`, `"cuda"`, `"mps"`).              |
| `inference`                       | `cuda_visible_devices`     | `"0"`                              | Comma-separated list of visible CUDA GPUs.                                 |
| `inference.backend_settings` (fastapi) | `executor`           | `"fastapi_background_tasks"`       | Task executor type.                                                        |
| `inference.backend_settings` (fastapi) | `worker_number`       | `1`                                | Number of worker threads for FastAPI tasks.                                |
| `inference.backend_settings` (celery) | `executor`            | `"celery"`                         | Task executor type.                                                        |
| `inference.backend_settings` (celery) | `worker_name`         | `"t3d_worker"`                     | Name of the Celery worker.                                                 |
| `inference.backend_settings` (celery) | `broker_url`          | **Required**                       | URL of the message broker (e.g. `amqp://`, `redis://`).                    |
| `inference.backend_settings` (celery) | `result_backend`      | `"rpc://"`                         | Backend used to store task results.                                        |
| `inference.backend_settings` (celery) | `run_flower`          | `False`                            | Whether to start a Flower dashboard.                                       |
| `inference.backend_settings` (celery) | `flower_port`         | `None`                             | Port for Flower UI (if `run_flower` is True).                              |
| `ssl`                              | `use_ssl`                 | `False`                            | Enables HTTPS if True.                                                     |
| `ssl`                              | `ssl_keyfile`             | `None`                             | Optional path to the SSL key file (accepts dynamic prefixes).         |
| `ssl`                              | `ssl_certfile`            | `None`                             | Optional path to the SSL certificate file (accepts dynamic prefixes). |
| `middleware`                       | `allow_origins`           | `[]`                               | List of allowed CORS origins.                                              |
| `middleware`                       | `allow_methods`           | `["GET"]`                          | HTTP methods permitted in CORS.                                            |
| `middleware`                       | `allow_headers`           | `[]`                               | Custom headers permitted in CORS.                                          |
| `middleware`                       | `allow_credentials`       | `False`                            | Whether to allow credentials in CORS.                                      |
| `middleware`                       | `expose_headers`          | `[]`                               | Headers exposed to browsers.                                               |
| `middleware`                       | `max_age`                 | `3600`                             | Cache time (in seconds) for CORS preflight.                                |


Some fields in the T3D Server configuration (such as `log_path`, `icon_path`, `ssl_keyfile`, etc.) support **dynamic prefixes** that resolve to OS-specific or runtime-specific paths. This allows for portability across platforms (e.g., Windows, Linux) and between development and production environments.

#### Supported Prefixes

| Prefix                   | Meaning (Resolved To...)                                                                 |
|--------------------------|------------------------------------------------------------------------------------------|
| `LOG_DEFAULT:`           | A platform-dependent log directory:                                                     |
|                          | - Windows: `%TEMP%/<organization>/<product>`                                            |
|                          | - Linux/macOS: `/var/log/<organization>/<product>`                                      |
| `PROGRAMDATA_DEFAULT:`   | A system-wide data directory (Windows only):                                            |
|                          | - e.g., `%PROGRAMDATA%/<organization>/<product>`                                        |
|                          | - On Linux/macOS, defaults to `"."` (current dir)                                       |
| `RELATIVE_DEFAULT:`      | A relative path to the current executable (PyInstaller compatible):                     |
|                          | - If bundled: `sys._MEIPASS/<path>`                                                     |
|                          | - Otherwise: `"./<path>"`                                                               |

> These are resolved **at runtime** in the `Settings.parse_paths()` validator method.

#### Example

```yaml
log_path: "LOG_DEFAULT:t3d_server.log"
ssl:
  use_ssl: true
  ssl_keyfile: "PROGRAMDATA_DEFAULT:ssl/server.key"
  ssl_certfile: "PROGRAMDATA_DEFAULT:ssl/server.crt"
gui:
  icon_path: "RELATIVE_DEFAULT:resources/icon.ico"
```

</details>

