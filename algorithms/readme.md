# How to create an algorithm module

In the following sections, we will describe how to create an algorithm module for the computing backend. The algorithm module is a Python package that contains the algorithm code. The algorithm module should be structured in a specific way in order to work properly with the computing backend.

The algorithm should be structured as follows:

```plaintext
algorithm_name/
    ├── __init__.py
    ├── Runner.py
    ├── pyproject.toml
    └── files/
        ├── file1
        └── file2
    └── some_internal_submodule/
        ├── __init__.py
        ├── module1.py
        └── module2.py

```
## The Runner.py file
The Runner.py file is a mandatory component of the algorithm module. It serves as the entry point for the python computing backend to run the algorithm. It must define a class named Runner. The Runner class should inherit either from the BaseRunner class, or a Runner class specific to the algorithm type (see more in the algorithm types section). The Runner classes can be imported from the t3d_server.algorithm_utils module. There are several mandatory methods that the Runner class must implement in order to work properly. The Runner class can also implement additional methods and functions that are not mandatory. But these can also be included as a submodule in the algorithm directory.

### Algorithm types
There are several types of algorithms that can be implemented in the computing backend. The main difference between the algorithm types is in the way input and output data is handled. The algorihtm type is defined in the algorithm's `pyproject.toml` file and the class, from which the Runner class should inherit. An example of algorithm type is e.g. and Image2Image algorithm, which receives an image as input and returns an image as output. The pyproject.toml file should thus contain the following line:
    
```toml
[tool.t3dserver]
algorithm_type = "Image2Image"
```

Furthermore the algotihm's Runner class should inherit from the Image2ImageRunner class, which is imported from the t3d_server.algorithm_utils module:

```python
from t3d_server.algorithm_utils.Image2ImageRunner import Image2ImageRunner

class Runner(Image2ImageRunner):
    """
    The runner class for the denoiser algorithm.
    """
```

The following algorithm types are currently supported:
- Image2Image: The algorithm receives an image as input and returns an image as output.
- Image2Embedding: The algorithm receives an image as input and returns a deep learning embedding as output.
- Image2Segmentation: The algorithm receives an image as input and returns a segmentation mask as output.
- Image2Alignment: The algorithm receives two images as input and returns an alignment transformation matrix as output.

If the algorithm does not fit into any of the above categories, the Runner class can either inherit from the BaseRunner class, and the data schemas can be defined manually (more on that in the next section), or a new algorithm type can be defined in the t3d_server.algorithm_utils module.

### Algorithm tags
The algorithm tags are a useful tool to categorize the algorithms for the users in the frontend application. Each algorithm type has a set of predefined tags, which are used to categorize the algorithms. This is important, because when several algorithms are tagged by a specific tag, the frontend developer can then operate with the assumption, that the algorithms with the same tag have the same input and output data schemas. The tags are defined in the `t3d_server/src/t3d_server/algorithm_utils/algorithm_tags.yaml` file. This file can be edited by the developer to add new tags or modify the existing ones.

### The `preprocess`, `inference` and `postprocess` methods
The methods are `preprocess`, `inference` and `postprocess`. In general it does not matter which part of the algorithm is implemented in which method, because the run method will call them sequentially in the order they are listed above. The separation is mostly for readability and maintainability.

Each of the methods must have exactly two inputs. The first input is some data that is passed between the methods (except for the preprocess method, which receives the input data identifiers defined by the user). The second input is a dictionary of arguments that the user has passed to the algorithm.

The `preprocess` method in general should serve for fetching the data using the `fetch_data` method, processing the data and returning the result. The preprocess method will receive the input_data and args as arguments. The first input is a dictionary currently containing only one key: `input_dataset_ids`. The value of the `input_dataset_ids` key is a list of dataset ids. The args is a dictionary containing the arguments that the user has passed to the algorithm. The output of the preprocess method does not have a set format, but it will be passed to the inference method, so it must be compatible with the inference method. The `inference` method should serve for running the actual algorithm on the data. The input of the inference method is the output of the preprocess method and the output is the result of the algorithm's inference phase. The `postprocess` method should postprocess the result of the algorithm and pass it to the `post_data` method. The output of the postprocess method is a list strings, where each string is a dataset identifier of the posted data. This list will be returned to the user, who can then use these dataset identifiers to fetch the posted data from the database.

### The `fetch_data` method for BaseRunner
Because the preprocess does not directly receive any data, only the data identifiers, the Runner class can use the `fetch_data` method to retrieve the data from the database. The `fetch_data` method receives a list of dataset identifiers and a pydantic model as arguments. The pydantic model is used to validate the fetched data. The output of the `fetch_data` method is a list of dictionaries, where each dictionary contains the data of one dataset.

Example of fetching data:
```python
embeddings = self.fetch_data(input_data["input_dataset_ids"], EmbeddingSchema)
```

The EmbeddingSchema is a pydantic model that is used to validate the fetched data. The pydantic schemas are defined in the fastapi/app/algorithms/io_schemas.py file. The EmbeddingSchema is defined as:

```python
class EmbeddingSchema(DataSchema):
    features: np.ndarray
    input_size: tuple
    original_size: tuple
```

### The `fetch_data` method for specific algorithm types
The `fetch_data` for Runners inherited from specific algorithm types is a bit different. The `fetch_data` method does not accept a pydantic model as an argument, because the data schemas are predefined for each algorithm type. The `fetch_data` method receives a list of dataset identifiers as an argument. The output of the `fetch_data` method is a list of dictionaries, where each dictionary contains the data of one dataset.

Example of fetching data with a Runner inherited from the Image2ImageRunner class:
```python
input_data = self.fetch_data(input_data["input_dataset_ids"])
```

### The `post_data` method for BaseRunner
After the computation is done, the Runner class can use the `post_data` method of the class to post the result of the computation to the database. The `post_data` method receives the result of the computation and a pydantic model as arguments. The result is expected to be a list of dictionaries, where each dictionary contains the data of one dataset. The pydantic model is used to validate the result before posting it to the database. Output of the `post_data` method is a list of dataset identifiers of the posted data.

Example of posting data:
```python
output_dataset_ids = self.post_data(output, MaskSchema)
```

The output is a list of dictionaries, where each dictionary contains the data of one dataset. The MaskSchema is a pydantic model that is used to validate the posted data. The MaskSchema is defined as:

```python
class MaskSchema(DataSchema):
    mask: np.ndarray
```

### The `post_data` method for specific algorithm types
The `post_data` method for Runners inherited from specific algorithm types follows the same pattern as the `fetch_data` method. The `post_data` method does not accept a pydantic model as an argument, because the data schemas are predefined for each algorithm type. The `post_data` method receives the result of the computation as an argument. The result is expected to be a list of dictionaries, where each dictionary contains the data of one dataset. The output of the `post_data` method is a list of dataset identifiers of the posted data.

Example of posting data with a Runner inherited from the Image2ImageRunner class:
```python
output_dataset_ids = self.post_data(output)
```


### The `load_assets` method
Is expected that the Runner class will work with a machine learning model. Because loading of model weights can be time consuming, the BaseRunner gives the developer an option to implement the `load_assets` method. The `load_assets` method is called during the instantiation of the Runner class in the computing backend and the attributes set in the `load_assets` will get cached together with the Runner instance. This will make repeated calls to the Runner class faster, because the model weights will not have to be loaded again as long as the cache is not invalidated.

Any file present in the algorithm directory can be loaded in the `load_assets` method (other than .py files). The `load_assets` should receive a relative path to the file that should be loaded as an argument. A bytes object will be returned, which can be loaded e.g. using the the torch.load method in the case of PyTorch state dicts.

Example of loading a PyTorch state dict:
```python
state_dict = self.fetch_asset("files/vit_b.pt")
state_dict = torch.load(state_dict)
```

### The `log_message` method
The log_message method can be used to log messages to the computing backend. The log_message method receives a message and a logging level as arguments. The logging level can be one of the following: "DEBUG", "INFO", "WARNING", "ERROR". The default logging level is "INFO".

Example of logging a message:
```python
self.log_message("This is an info message.", logging_level="INFO")
```

### The `set_progress` method
The set_progress method can be used to report the progress of the algorithm to the computing backend. The set_progress method receives a float value between 0 and 1 as an argument. The starting progress is automatically set to 0 and if the computation is done, or fails, the progress is automatically set to 1.

Example of reporting the progress:
```python
self.set_progress(0.5)
```

## The `pyproject.toml` file
The `pyproject.toml` is a file that contains the algorithm metadata. This file is used by the t3dserver to properly deploy the algorithm as a service. The `pyproject.toml` file should be placed in the root directory of the algorithm.

### Mandatory fields

The `pyproject.toml` file should contain the following fields mandatory fields:

```toml
[project]
name = "algorithm_name"
version = "major.minor.patch"
```

Even though the following fields are not mandatory, it is recommended to include them in the `pyproject.toml` file to make the algorithm as user-friendly and compatible with the t3dserver as possible.

The algorithm type should be specified in the `tool.t3dserver` section. The algorithm type is used to specify the general algorithm functionality. The algorithm type is used to determine the input and output data schemas, and the general algorithm behavior. The algorithm type is defined in the t3d_server.algorithm_utils module.

### Algorithm type, tags, and description

```toml
[tool.t3dserver]
algorithm_type = "AlgorithmType"
```

Each algorithm type has a set of potential tags, which are used to specify the general algorithm functionality. These tags can be found and modified in the `t3d_server\algorithm_utils\algorithm_tags.yaml` file. Multiple tags can be provided for one algorithm. For image denoising algorithms, we will use the `image-denoising` tag. 
 
```toml
tags = ["tag1", "tag2", "tag3", ...]
```

The `description` field should contain a brief description of the algorithm.

```toml
description = "This is a super cool algorithm that does super cool things."
```

### Algorithm supported devices
The server allows algorithms to be run on both CPU and GPU devices. The `supported_devices` field is used to specify which devices the algorithm supports. The `supported_devices` field should contain a list of strings, where each string specifies a device that the algorithm supports, ["cpu"], ["gpu"], or ["cpu", "gpu"]. Additionally, a `default_device` field must be specified, which specifies the default device that the algorithm will run on. The `default_device` field should be a string, either "cpu" or "gpu". Do not specify a `default_device` that's not included in the `supported_devices` list as this will cause a warning and the algorithm will run on the CPU by default.

This setting will cause the algorithm to run on the CPU by default, but the user can override this setting in the execution request and run the algorithm on the GPU.
```toml
supported_devices = ["cpu", "gpu"]
default_device = "cpu"
```

### Additional parameters

We can also specify additional parameters in the `additional_parameters` field. The `additional_parameters` field should contain a list of dictionaries, where each dictionary contains the parameter name, type, default value, and description. The `additional_parameters` field is optional, and can be omitted if the algorithm does not require any additional parameters.

Each additional parameter must contain the following fields:
* `name`: The name of the parameter.
* `description`: The description of the parameter. This field is used to describe the purpose of the parameter. It should be a short, human-readable description of the parameter that can be displayed by the client application as a tooltip or help text.
* `config`: The configuration of parameter `type`, `default`, and `adjustable`. The `type` field specifies the type of the parameter. The `default` field specifies the default value of the parameter. The `adjustable` field specifies whether the parameter can be adjusted by the user. If set to `true`, the parameter can be adjusted by the user. If set to `false`, the parameter is to be specified from within the client application without exposing it to the user.

The following parameter types and configuration fields are supported:

| Parameter type | Configuration fields |
| --- | --- |
| string | type, default, adjustable |
| int | type, default, adjustable |
| float | type, default, adjustable |
| bool | type, default, adjustable |
| int_range | type, default, min, max, step, adjustable |
| float_range | type, default, min, max, step, adjustable |
| string_enum | type, default, options, adjustable |
| int_enum | type, default, options, adjustable |
| float_enum | type, default, options, adjustable |
| string_list | type, default, adjustable |
| int_list | type, default, adjustable |
| float_list | type, default, adjustable |
| bool_list | type, default, adjustable |

Here you can see an example of how to define additional parameters in the `pyproject.toml` file:

To define an user-adjustable `string` parameter, use the following configuration:

```toml
additional_parameters = [
    {name = "some_string_parameter", description = "This parameter strings.", config = {type = "string", default = "hello", adjustable = true}},
]
```

To define an user-adjustable `int` parameter, use the following configuration:

```toml
{name = "some_int_parameter", description = "This paramete ints.", config = {type = "int", default = 42, adjustable = true}},
```

To define an user-adjustable `float` parameter, use the following configuration:

```toml
{name = "some_float_parameter", description = "This parameter floats.", config = {type = "float", default = 3.14, adjustable = true}},
```

To define an user-adjustable `bool` parameter, use the following configuration:

```toml
{name = "some_bool_parameter", description = "This parameter bools.", config = {type = "bool", default = true, adjustable = true}},
```

To define an user-adjustable `int_range` parameter, use the following configuration:

```toml
{name = "some_int_range_parameter", description = "This parameter ranges ints.", config = {type = "int_range", default = 42, min = 0, max = 100, step = 1, adjustable = true}},
```

To define an user-adjustable `float_range` parameter, use the following configuration:

```toml
{name = "some_float_range_parameter", description = "This parameter ranges floats.", config = {type = "float_range", default = 3.14, min = 0.0, max = 10.0, step = 0.1, adjustable = true}},
```

To define an user-adjustable `string_enum` parameter, use the following configuration:

```toml
{name = "some_string_enum_parameter", description = "This parameter enums strings.", config = {type = "string_enum", default = "hello", options = ["hello", "world"], adjustable = true}},
```

To define an user-adjustable `int_enum` parameter, use the following configuration:

```toml
{name = "some_int_enum_parameter", description = "This parameter enums ints.", config = {type = "int_enum", default = 42, options = [42, 43, 44], adjustable = true}},
```

To define an user-adjustable `float_enum` parameter, use the following configuration:

```toml
{name = "some_float_enum_parameter", description = "This parameter enums floats.", config = {type = "float_enum", default = 3.14, options = [3.14, 3.15, 3.16], adjustable = true}},
```

To define an user-adjustable `string_list` parameter, use the following configuration:

```toml
{name = "some_string_list_parameter", description = "This parameter lists strings.", config = {type = "string_list", default = ["hello", "world"], adjustable = true}},
```

To define an user-adjustable `int_list` parameter, use the following configuration:

```toml
{name = "some_int_list_parameter", description = "This parameter lists ints.", config = {type = "int_list", default = [42, 43, 44], adjustable = true}},
```

To define an user-adjustable `float_list` parameter, use the following configuration:

```toml
{name = "some_float_list_parameter", description = "This parameter lists floats.", config = {type = "float_list", default = [3.14, 3.15, 3.16], adjustable = true}},
```

To define an user-adjustable `bool_list` parameter, use the following configuration:

```toml
{name = "some_bool_list_parameter", description = "This parameter lists bools.", config = {type = "bool_list", default = [true, false, true], adjustable = true}},
```

### Other fields

The `check_importable` field is used to check if the algorithm can be imported. If set to `true`, the t3dserver will check if the algorithm can be imported before deploying it as a service. (NOTE: THIS CURRENTLY DOES NOT WORK).

```toml
check_importable = false
```

The `obfuscate` field is used to obfuscate the algorithm code. If set to `true`, the t3dserver will obfuscate the algorithm code before deploying it as a service. The obfuscation is currently implemented as minimization of the code. It is recommended to set this field to `true` to reasonably protect the algorithm code.

```toml
obfuscate = true
```

You can use the `hash_module` and `hash_assets` fields to check if the algorithm module or assets have already been deployed. If they have been deployed, the t3dserver will not redeploy them, but reuse them for the current algorithm deployment. This can reduce the deployment time and the amount of data that needs to be stored.

```toml
hash_module = true
hash_assets = true
```

## The `files` directory
The files directory is an optional component of the algorithm module. It should contain any files that the algorithm needs to run. The files directory can contain any type of file, such as images, text files, etc. The files directory can be accessed by calling the `self.fetch_asset` method from anywhere in the Runner class. The `fetch_asset` method receives a relative path to the file that should be fetched as an argument. A bytes object will be returned, which can be used to load the file.

## The `some_internal_submodule` directory
The some_internal_submodule directory is an optional component of the algorithm module. It should contain any internal submodules that the algorithm needs to run. The some_internal_submodule directory can contain any number of Python files. The some_internal_submodule directory can be accessed by importing the submodule from the Runner class. Note that the submodule will be deployed together with the algorithm, so it should not contain any sensitive information (even though the submodule is not accessible from the outside and there is an option to obfuscate the code).


# Example of a dummy algorithm

The file structure should look like this (this is just an untested example):

```plaintext
algorithm_name/
    ├── __init__.py
    ├── Runner.py
    ├── pyproject.toml
    └── files/
        ├── some_heavy_model.pt
    └── my_big_model/
        ├── __init__.py
        ├── utils.py
```

The Runner.py file should look like this:

```python
from my_big_model.utils import MyBigModel
from algorithms.BaseRunner import BaseRunner
from algorithms.io_schemas import MyDataSchema, MyOutputSchema
import numpy as np
import torch
class Runner(BaseRunner):
    """
    The runner class for the foo algorithm.
    """

    def load_assets(self):
        """
        The assets to load for the foo algorithm.
        """
        some_model = MyBigModel()
        self.log_message("Loading the Foo assets.")
        some_big_state_dict = self.fetch_asset("files/some_heavy_model.pt")¨
        some_big_state_dict = torch.load(some_big_state_dict)
        some_model.load_state_dict(some_big_state_dict)
        self.my_big_model = some_model


    def preprocess(self, input_data: dict, args: dict = {}) -> np.ndarray:
        """Preprocess the request data before feeding into model for inference.

        Parameters
        ----------
        input_data : ImageSchema
            The input data.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        tuple
            The preprocessed data.
        """
        self.log_message("Preprocessing the Foo input data.")
        my_data = self.fetch_data(input_data["input_dataset_ids"], MyDataSchema)
        input_data = np.array(my_data[0])
        return input_data

    def inference(self, data: np.ndarray,  args: dict = {}) -> torch.tensor:
        """Run the inference on the preprocessed data.

        Parameters
        ----------
        data : np.ndarray
            The preprocessed data.
        args : dict, optional
            The arguments, by default None


        Returns
        -------
        torch.tensor
            The inference output.
        """

        self.log_message("Running the Foo inference.")

        some_user_defined_args = args.get("some_user_defined_args", None)
        if some_user_defined_args is not None:
            self.log_message(f"User defined args: {some_user_defined_args}")
        output = self.my_big_model(input_data, some_user_defined_args)
        self.set_progress(0.5)
        self.log_message("The Foo inference is done.")
        return output

    def postprocess(self, inference_output: torch.tensor, args: dict = {}) -> list[str]:
        """Postprocess the inference output.

        Parameters
        ----------
        inference_output : dict
            The inference output.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        list[str]
            The output dataset ids.
        """

        self.log_message("Postprocessing the Foo output.")
        output = inference_output.detach().numpy()
        output = [
            {
                "output": output
            }
        ]
        output_dataset_ids = self.post_data(output, MyOutputSchema)
        return output_dataset_ids
```
The pyproject.toml file should look like this:

```toml
[project]
name = "foo"
version = "0.1.0"

[tool.t3dserver]
algorithm_type = "Generic"
tags = ["foo", "bar"]
description = "This algorithm does foo and bar."
additional_parameters = [
    {name = "some_user_defined_args", type = "str", default = "hello", description = "This is a user defined argument."},
]
check_importable = false
obfuscate = true
hash_module = true
hash_assets = true
```
