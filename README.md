# Compox
Compox is a simple Python execution engine based on FastAPI with a MinIO object storage and Celery task queue. The app is designed to run algorithms written in Python on the server and report the results to the user.
## Installation
Compox can be installed through PyPI: 
```bash
pip install compox
```

You can also install the server by cloning this repository and installing it from source.

Note that some additional dependencies, such as MinIO executable for your operating system, will be downloaded on the first run of the server.

## Running the server
Once installed into your Python environment, it's recommended to generate an initial configuration file with `compox generate-config`. 
To see the available options for the `generate-config` command, you can run:

```bash
compox generate-config --help
```

The Compox can be run using the `compox` command. This command is available in the virtual environment created during the setup process. Run the following command to list the available commands:

```bash
compox --help
```

To run the Compox, use the following command:

```bash
compox run --config /path/to/config.yaml
```

### Deploying algorithms
A future release of this package will include a detailed tutorial on how to prepare a data processing algorithm for T3D applications. 

Once your algorithm is ready, you can use the `compox deploy-algorithms` command to deploy it to your server. This command will read the algorithm definitions from the specified configuration file and deploy them to the server. For example:

```bash
compox deploy-algorithms --config /path/to/config.yaml
```

To see the available options for the `deploy-algorithms` command, you can run:

```bash
compox deploy-algorithms --help
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
| `info`                           | `version`                   | `"0.1"`                            | Semantic version of the server release.                                   |
| `gui`                            | `algorithm_add_remove_in_menus` | `False`                        | Enables/disables GUI menu for algorithm management.                        |
| `gui`                            | `use_systray`               | `False`                            | Enables/disables systray GUI integration.                                  |
| `gui`                            | `icon_path`                 | `"../compox/resources/compoxbackend.ico"` | Path to the systray icon (supports dynamic prefixes)               |
| `storage`                        | `collection_prefix`         | `""`                               | Prefix applied to object store collections. (useful for AWS s3 store, where unique bucket names are needed)|
| `storage`                        | `data_store_expire_days`    | `1`                                | Number of days until stored datasets expire.                               |
| `storage`                        | `access_key_id`             | `UUIDv4`                           | Generated access key for storage backend. If `null` is provided, random UUIDv4 is generated. |
| `storage`                        | `secret_access_key`         | `UUIDv4`                           | Generated secret key for storage backend. If `null` is provided, random UUIDv4 is generated. |S
| `storage.backend_settings` (minio) | `provider`                | `"minio"`                          | Selected backend provider.                                                 |
| `storage.backend_settings` (minio) | `start_instance`         | `True`                             | Whether to start a local MinIO server.                                     |
| `storage.backend_settings` (minio) | `port`                   | `9091`                             | MinIO service port.                                                        |
| `storage.backend_settings` (minio) | `console_port`           | `9090`                             | MinIO admin console port.                                                  |
| `storage.backend_settings` (minio) | `executable_path`        | `"minio/minio_bin"`                | Path to the MinIO binary (accepts dynamic prefixes).                |
| `storage.backend_settings` (minio) | `storage_path`           | `"minio/compox_store"`         | Storage directory used by MinIO (accepts dynamic prefixes).         |
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
| `inference.backend_settings` (celery) | `worker_name`         | `"compox_worker"`                     | Name of the Celery worker.                                                 |
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


Some fields in the Compox configuration (such as `log_path`, `icon_path`, `ssl_keyfile`, etc.) support **dynamic prefixes** that resolve to OS-specific or runtime-specific paths. This allows for portability across platforms (e.g., Windows, Linux) and between development and production environments.

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
log_path: "LOG_DEFAULT:compox.log"
ssl:
  use_ssl: true
  ssl_keyfile: "PROGRAMDATA_DEFAULT:ssl/server.key"
  ssl_certfile: "PROGRAMDATA_DEFAULT:ssl/server.crt"
gui:
  icon_path: "RELATIVE_DEFAULT:resources/icon.ico"
```

## Server Execution and Tooling

The Compox can be run using the `compox` command. This command is available in the virtual environment created during the setup process. Run the following command to list the available commands:

```bash
compox --help
```

### Running the Server
To run the Compox, use the following command:

```bash
compox run --config config.yaml
```

Replace `config.yaml` with the path to your configuration file. The server will start and listen on the port specified in the configuration.
You can also specify the configuration file directly in the command line, which will override the default configs and the configuarion field in the config file. Nested configuration fields can be specified using dot notation. For example, to set the executor to `celery` and the worker name to `my_worker`, you can run:

```bash
compox run --config config.yaml --inference.backend_settings.executor celery --inference.backend_settings.worker_name my_worker
```

To see the available options for the `run` command, you can run:

```bash
compox run --help
```

### Worker spawning (for Celery)
To spawn a Celery worker, you can use the `compox spawn-worker` command. This command will start a Celery worker with the specified configuration. You can specify the worker name and other settings as needed. For example:

```bash
compox spawn-worker --config config.yaml --inference.backend_settings.worker_name my_worker
```

To see the available options for the `spawn-worker` command, you can run:

```bash
compox spawn-worker --help
```

### Running tests
To run the tests, you can use the `compox test` command. This command will run the tests defined in the `tests` directory. You should provide the path to the folder containing the tests (`--test-path`), which is `tests` by default. You can either provide a path to a specific configuration file (`--config`), which will spawn a server instance and run the tests against it, or you can run the tests against a running server instance by providing the `--server-url` argument. For example:

```bash
compox test --test-path tests --config config.yaml
```

To see the available options for the `test` command, you can run:

```bash
compox test --help
```

### Deploy algorithms
To deploy algorithms to the server, you can use the `compox deploy-algorithms` command. This command will read the algorithm definitions from the specified configuration file and deploy them to the server. For example:

```bash
compox deploy-algorithms --config app_server.yaml
```

To see the available options for the `deploy-algorithms` command, you can run:

```bash
compox deploy-algorithms --help
```

### Generate configuration
If you don't have a configuration file, you can generate a default configuration file using the `compox generate-config` command. This command will create a default configuration file in the specified path. You can also override the default fields in the configuration file by providing them as command line arguments. You will be prompted if you try to generate a configuration file that already exists. For example:

```bash
compox generate-config --path app_server.yaml --port 8888 --gui.use_systray True
```

To see the available options for the `generate-config` command, you can run:

```bash
compox generate-config --help
```

### Serving documentation
You can update documentation by navigating to the `python-computing-backend/compox/docs` directory and running the following command:

```bash
make.bat html
```

This will generate the documentation in the `_build/html` directory. After the documentation is built, you can serve it using the `compox serve-docs` command. This command will start a simple HTTP server to serve the documentation files. You can specify the directory where the documentation is located and the port on which to serve it. For example:

```
compox serve-docs --directory docs/_build/html --port 8000
```

To see the available options for the `serve-docs` command, you can run:

```bash
compox serve-docs --help
```