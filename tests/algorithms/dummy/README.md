# A general template for creating a denoising algorithm

Here a working template for developing a denoising algorithm will be presented. This guide will cover the specifics needed to develop an image denoising algorithm. To see how compox algorithm should generally be structured, please refer to the algorithms/readme.md file.

The algorithm folder is structured as follows:

```plaintext
template_denoising_algorithm/
    ├── __init__.py
    ├── Runner.py
    ├── pyproject.toml
    └── image_denoising/
        ├── __init__.py
        └── denoising_utils.py
    └── README.md
```

## The pyproject.toml file

The `pyproject.toml` is a file that contains the algorithm metadata. This file is used by compox to properly deploy the algorithm as a service. The `pyproject.toml` file should be placed in the root directory of the algorithm.

First, let's create the `pyproject.toml` file. Under the [project] section, you should provide the name and version of the algorithm. The name should be unique and should not contain any spaces. The version should be in the format `major.minor.patch`. The algorithm name and versions is used to identify the algorithm in compox so it is important to provide a unique name and version.

```toml
[project]
name = "template_denosing_algorithm"
version = "1.0.0"
```

Next, you should fill out the [tool.compox] section. This section contains the metadata that compox uses to deploy the algorithm as a service. `algorithm_type` defines the algorithm input and output types, you may either use some predefined algorithm types or define your own. The predefined algorithm types are located in `compox.algorithm_utils`. For an image denoising algorithm, we will use the the `Image2Image` type. This type is suitable for image denoising as both our input and output is an image (or a sequence of images).

```toml
[tool.compox]
algorithm_type = "Image2Image"
```

 Each algorithm type has a set of potential tags, which are used to specify the general algorithm functionality. These tags can be found and modified in the `compox\algorithm_utils\algorithm_tags.yaml` file. Mutliple tags can be provided for one algorithm. For image denoising algorithms, we will use the `image-denoising` tag. 
 
 ```toml
tags = ["image-denoising"]
```

The `description` field should contain a brief description of the algorithm.

```toml
description = "Denoises a sequence of images using the total variation denoising algorithm."
```

We can also specify additional parameters in the `additional_parameters` field. The `additional_parameters` field should contain a list of dictionaries, where each dictionary represents an additional parameter. Each parameter should have a `name`, `description` and `config` field. The `name` field should contain the name of the parameter. The `description` field should contain a brief description of the parameter. The `config` field should contain a dictionary with the following fields: `type`, `default`, `adjustable` and type-specific fields. To see more information about the possible parameter types see the `How to create an algorithm module` section. 

For the denoising algorithm, we will add a `denoising_weight` parameter that will control the denoising strength. Because we want to set a range for the denoising weight, we will use the `float_range` parameter type. The `default` field should contain the default value of the parameter. The `min` and `max` fields should contain the minimum and maximum values of the parameter. The `step` field should contain the step size of the parameter. The `adjustable` field should be set to `true` if the parameter should be exposed to the user to adjust.

```toml
additional_parameters = [
    {name = "denoising_weight", description = "The weight of the denoising term between 0 and 1. Higher values will result in more denoising, but can distort the image.", config = {type = "float_range", default = 0.1, min = 0.0, max = 1.0, step = 0.05, adjustable = true}}
]
```

The `check_importable` field is used to check if the algorithm can be imported. If set to `true`, compox will check if the algorithm can be imported before deploying it as a service.

```toml
check_importable = false
```

The `obfuscate` field is used to obfuscate the algorithm code. If set to `true`, compox will obfuscate the algorithm code before deploying it as a service. The obfuscation is currently implemented as minimization of the code. It is recommended to set this field to `true` to reasonably protect the algorithm code.

```toml
obfuscate = true
```

You can use the `hash_module` and `hash_assets` fields to check if the algorithm module or assets have already been deployed. If they have been deployed, compox will not redeploy them, but reuse them for the current algorithm deployment. This can reduce the deployment time and the amount of data that needs to be stored.

```toml
hash_module = true
hash_assets = true
```

## The algorithm dependencies

The algorithm can use any libraries from the global compox environment. Additional dependencies can be provided as python submodules. Here we will use the `numpy` library to handle the image data. We also implemented a simple `image_denoising` module that contains an `__init__.py` file and a `denosing_utils.py` file. The `denoising_utils.py` file contains the `denoise_image` function that performs the denoising of the images. The `image_denoising` module should be placed in the root directory of the algorithm.

```python
from skimage.restoration import (
    denoise_tv_chambolle,
)

def denoise_image(image, weight=0.1):
    """
    Denoise the image using the total variation denoising algorithm.

    Parameters
    ----------
    image : np.ndarray
        The image to denoise.
    weight: float
        The weight parameter for the denoising algorithm.
    Returns
    -------
    np.ndarray
        The denoised image.
    """

    return denoise_tv_chambolle(image, weight=weight)
```
## The Runner.py file

The `Runner.py` file is the main file of the algorithm. This file should contain the algorithm implementation. The `Runner.py` file should be placed in the root directory of the algorithm.

Because we specified the algorithm type as `Image2Image`, the `Runner.py` file should contain a class that inherits from the `Image2ImageRunner` class. The `Image2ImageRunner` class is located in the `compox.algorithm_utils` module. The `Image2ImageRunner` class contains the necessary methods to handle the input and output of the algorithm.


```python
from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner

class Runner(Image2ImageRunner):
    """
    The runner class for the denoiser algorithm.
    """

    def __init__(self, task_handler, device: str = "cpu"):
        """
        The denoising runner.
        """
        super().__init__(task_handler, device)
```

We can implement a `load_assets` method to load any assets that the algorithm requires upon initilaization of the Runner. The important bit is that the attributes that are loaded in the `load_assets` method are cached with the algorithm and do not have to be reloaded for each algorithm call. This can greatly speed up the algorithm execution. Since we do not need any assets for the denoising algorithm, we can leave the `load_assets` method empty.

```python
def load_assets(self):
    """
    Here you can load the assets needed for the algorithm. This can be
    the model, the weights, etc. The assets are loaded upon the first
    call of the algorithm and are cached with the algorithm instance.
    """
    pass
```

Next, we can implement the `preprocess` method, where we retrieve the data form the data storage and preprocess it. We can also load the the additional parameters that the algorithm requires.
    
```python
def preprocess(self, input_data: dict, args: dict = {}) -> tuple:
    """Preprocess the request data before feeding into model for inference.

    Parameters
    ----------
    input_data : dict
        The input data.
    args : dict, optional
        The arguments, by default None

    Returns
    -------
    tuple
        The preprocessed data.
    """

    # this fetches the image data from the data storage as a list of dictionaries
    input_images = self.fetch_data(input_data["input_dataset_ids"], "image")

    # this extracts the image data from the dictionaries
    for i in range(len(input_images)):
        input_images[i] = input_images[i]["image"]

    # this converts the list of images to a numpy array
    input_images = np.stack(input_images, axis=0)

    # we will min max normalize the images
    data_type = input_images.dtype
    min_val = np.min(input_images)
    max_val = np.max(input_images)
    input_images = (input_images - min_val) / (max_val - min_val)

    # here we will get the optional argument of denoising weight
    denosing_weight = args.get("denoising_weight", 0.1)

    # now we will pass the images and the denoising weight to the inference method
    return input_images, denosing_weight, min_val, max_val, data_type

```

Next, we can implement the `inference` method, where we perform the denoising of the images. The `inference` method should return the denoised images.

```python
def inference(self, data, args: dict = {}) -> dict:
    """
    Run the inference.

    Parameters
    ----------
    input_data : dict
        The input data.

    Returns
    -------
    torch.Tensor
        The output data.
    """
    self.log_message("Starting inference.")
    # now we retrieve the input data
    images, denoise_weight, min_val, max_val, data_type = data

    # we can post messages to the log
    self.log_message(
        f"Starting denoising of {images.shape[0]} images with weight {denoise_weight}."
    )

    # we will denoise the images
    denoised_images = np.zeros_like(images)
    for i in range(images.shape[0]):
        denoised_images[i] = denoise_image(images[i], weight=denoise_weight)
        # this will update the progress bar
        self.set_progress(i / images.shape[0])

    # we will pass the denoised images to the postprocess method

    return denoised_images, min_val, max_val, data_type

```

Finally, we can implement the `postprocess` method, where we convert the denoised images to the desired output format and post it to the data storage. We finally return the outputs data identifiers.

```python
def postprocess(self, data: np.array, args: dict = {}) -> list[str]:
    """
    Postprocess the output data.

    Parameters
    ----------
    data : np.array
        The input data.

    Returns
    -------
    list[str]
        The ids of the output datasets.

    """

    # we will denormalize the data
    denoised_images, min_val, max_val, data_type = data
    denoised_images = (denoised_images - denoised_images.min()) / (
        denoised_images.max() - denoised_images.min()
    )
    denoised_images = denoised_images * (max_val - min_val) + min_val
    # we will convert the data type back to the original data type
    denoised_images = denoised_images.astype(data_type)

    # this will convert the numpy array to a list of dictionaries
    output_dicts = [
        {"image": denoised_images[i]}
        for i in range(denoised_images.shape[0])
    ]
    # this will post the data to the data storage and return the ids
    output_dataset_ids = self.post_data(output_dicts)
    return output_dataset_ids
```

## Deploying the algorithm

To deploy the finished algorithm, you can use the `pdm run deployment template_denoising_algorithm` command. This command will deploy the algorithm to the compox. The algorithm can also be added through compox systray interface by clicking the "Add Algorithm" button and selecting the algorithm directory.