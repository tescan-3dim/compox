# A general template for creating a segmentation algorithm

This guide will cover the specifics needed to develop an image image segmentation algorithm. To see how the compox algorithm should generally be structured, please refer to the algorithms/readme.md file.

The algorithm folder is structured as follows:

```plaintext
template_segmentation_algorithm/
    ├── __init__.py
    ├── Runner.py
    ├── pyproject.toml
    └── image_segmentation/
        ├── __init__.py
        └── segmentation_utils.py
    └── README.md
```

## The pyproject.toml file

The `pyproject.toml` is a file that contains the algorithm metadata. This file is used by the compox to properly deploy the algorithm as a service. The `pyproject.toml` file should be placed in the root directory of the algorithm.

First, let's create the `pyproject.toml` file. Under the [project] section, you should provide the name and version of the algorithm. The name should be unique and should not contain any spaces. The version should be in the format `major.minor.patch`. The algorithm name and versions is used to identify the algorithm in the compox so it is important to provide a unique name and version.

```toml
[project]
name = "template_segmentation_algorithm"
version = "1.0.0"
```

Next, we will fill out the [tool.compox] section. This section contains the metadata that the compox uses to deploy the algorithm as a service. `algorithm_type` defines the algorithm input and output types, you may either use some predefined algorithm types or define your own. The predefined algorithm types are located in `compox.algorithm_utils`. For an image segmentation algorithm, we will use the the `Image2Segmentation` type. This type is suitable for image segmentation as the input is a sequence of images and the output is a sequence of segmentation masks.

```toml
[tool.compox]
algorithm_type = "Image2Segmentation"
```

Each algorithm type has a set of potential tags, which are used to specify the general algorithm functionality. These tags can be found and modified in the `compox\algorithm_utils\algorithm_tags.yaml` file. Mutliple tags can be provided for one algorithm. For image segmentation algorithms, we will use the `image-segmentation` tag. 
 
 ```toml
tags = ["image-segmenation"]
```

The `description` field should contain a brief description of the algorithm.

```toml
description = "Performs a binary segmentation of a 3-D image using a skimage filter."
```

We can also specify additional parameters in the `additional_parameters` field. The `additional_parameters` field should contain a list of dictionaries, where each dictionary represents an additional parameter. Each parameter should have a `name`, `description` and `config` field. The `name` field should contain the name of the parameter. The `description` field should contain a brief description of the parameter, that should be concise and descriptive enough to show to the user as a tooltip or help text. The `config` field should contain a dictionary with the following fields: `type`, `default`, `adjustable` and type-specific fields. To see more information about the possible parameter types see the `How to create an algorithm module` section.

Here we will add a `thresholding_algorithm` parameter that will allow the user to select the thresholding algorithm to use. The `type` field is set to `string_enum` to specify that the parameter is a string with a predefined set of values. The `default` field is set to `otsu` to specify the default value of the parameter. The `options` field is set to a list of strings that specify the possible values of the parameter. The `adjustable` field is set to `true` to specify that the user should be able to select the thresholding algorithm to apply.

```toml
additional_parameters = [
    {name = "thresholding_algorithm", description = "The thresholding algorithm to use.", config = {type = "string_enum", default = "otsu", options = ["otsu", "yen", "li", "minimum", "mean", "triangle", "isodata", "local"], adjustable = true}},
]
```

The `check_importable` field is used to check if the algorithm can be imported. If set to `true`, the compox will check if the algorithm can be imported before deploying it as a service. (NOTE: THIS CURRENTLY DOES NOT WORK).

```toml
check_importable = false
```

The `obfuscate` field is used to obfuscate the algorithm code. If set to `true`, the compox will obfuscate the algorithm code before deploying it as a service. The obfuscation is currently implemented as minimization of the code. It is recommended to set this field to `true` to reasonably protect the algorithm code.

```toml
obfuscate = true
```

You can use the `hash_module` and `hash_assets` fields to check if the algorithm module or assets have already been deployed. If they have been deployed, the compox will not redeploy them, but reuse them for the current algorithm deployment. This can reduce the deployment time and the amount of data that needs to be stored.

```toml
hash_module = true
hash_assets = true
```

## The algorithm dependencies

The algorithm can use any libraries from the global compox environment. Additional dependencies can be provided as python submodules. Here we will use the `numpy` library to handle the image data. We also implemented a simple `image_segmentation` module that contains an `__init__.py` file and a `segmentation_utils.py` file. The `segmentation_utils.py` file contains the `threshold_image` function that performs segmentation of an image using a selected algorithm. The `image_segmentation` module should be placed in the root directory of the algorithm.

```python
import skimage.filters as skif


def threshold_image(image, thresholding_algorithm):
    """
    Threshold the image using the specified thresholding algorithm.

    Parameters
    ----------
    image : np.ndarray
        The image to threshold.
    thresholding_algorithm : str
        The thresholding algorithm to use.

    Returns
    -------
    np.ndarray
        The thresholded image.
    """
    if thresholding_algorithm == "otsu":
        threshold = skif.threshold_otsu(image)
    elif thresholding_algorithm == "yen":
        threshold = skif.threshold_yen(image)
    elif thresholding_algorithm == "li":
        threshold = skif.threshold_li(image)
    elif thresholding_algorithm == "minimum":
        threshold = skif.threshold_minimum(image)
    elif thresholding_algorithm == "mean":
        threshold = skif.threshold_mean(image)
    elif thresholding_algorithm == "triangle":
        threshold = skif.threshold_triangle(image)
    elif thresholding_algorithm == "isodata":
        threshold = skif.threshold_isodata(image)
    elif thresholding_algorithm == "local":
        threshold = skif.threshold_local(image)
    else:
        raise ValueError(
            f"Invalid thresholding algorithm: {thresholding_algorithm}"
        )

    return image > threshold
```
## The Runner.py file

The `Runner.py` file is the main file of the algorithm. This file should contain the algorithm implementation. The `Runner.py` file should be placed in the root directory of the algorithm.

Because we specified the algorithm type as `Image2Segmentation`, the `Runner.py` file should contain a class that inherits from the `Image2SegmentationRunner` class. The `Image2SegmentationRunner` class is located in the `compox.algorithm_utils` module. The `Image2SegmentationRunner` class contains the necessary methods to handle the input and output of the algorithm.


```python
import numpy as np
from compox.algorithm_utils.Image2SegmentationRunner import (
    Image2SegmentationRunner,
)
from image_segmentation.segmentation_utils import threshold_image


class Runner(Image2SegmentationRunner):
    """
    The runner class for the image segmentation algorithm.
    """

    def __init__(self, task_handler, device: str = "cpu") -> None:
        """
        The aligner runner.
        """
        super().__init__(task_handler, device=device)
```

We can implement a `load_assets` method to load any assets that the algorithm requires upon initilaization of the Runner. The important bit is that the attributes that are loaded in the `load_assets` method are cached with the algorithm and do not have to be reloaded for each algorithm call. This can greatly speed up the algorithm execution. Since we do not need any assets for the segmentation algorithm, we can leave the `load_assets` method empty.

```python
def load_assets(self):
    """
    Here you can load the assets needed for the algorithm. This can be
    the model, the weights, etc. The assets are loaded upon the first
    call of the algorithm and are cached with the algorithm instance.
    """
    pass
```

Next, we can implement the `inference` method, where we perform the segmentation of the images. The `inference` will receive a numpy array with the images to be segmented. The `inference` method must return a numpy array with the segmentation masks of the same
shape as the input images. The `inference` method can also receive a dictionary with the arguments for the algorithm. The arguments are passed to the algorithm from the compox and can be used to customize the behavior of the algorithm. In our case, we will use the `thresholding_algorithm` argument to specify the thresholding algorithm to use.
You can also report the progress of the algorithm by calling the `set_progress` method. The `set_progress` method takes a float value between 0 and 1, where 0 is the start of the algorithm and 1 is the end of the algorithm. The `log_message` method can be used to log messages to the compox log.

```python
def inference(self, data: np.ndarray, args: dict = {}) -> np.ndarray:
    """
    Run the inference.

    Parameters
    ----------
    data : np.ndarray
        The images to be segmented.
    args : dict
        The arguments for the algorithm.

    Returns
    -------
    np.ndarray
        The segmented images.
    """

    # now we retrieve the input data
    thresholding_algorithm = args.get("thresholding_algorithm", "otsu")
    # we can post messages to the log
    self.log_message(
        f"Starting inference with thresholding algorithm: {thresholding_algorithm}"
    )

    # here we will threshold the images
    mask = threshold_image(data, thresholding_algorithm)

    # we can also log progress
    self.set_progress(0.5)

    # pass the mask to the postprocess
    return mask
```
To customize the behavior of fetching and processing the input data, and postprocessing and uploading the output data, we can implement the `preprocess` and `postprocess` methods. The `preprocess` method is called before the `inference` method and is used to fetch the input data. The `postprocess` method is called after the `inference` method and is used to process the output data. In our case, we will not implement any custom behavior for these methods. You can refer to the `compox.algorithm_utils.Image2SegmentationRunner` class for more information about these methods.

## Deploying the algorithm

To deploy the finished algorithm, you can use the `pdm run deployment template_segmentation_algorithm` command. This command will deploy the algorithm to the compox. The algorithm can also be added through the compox systray interface by clicking the "Add Algorithm" button and selecting the algorithm directory.