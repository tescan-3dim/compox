# Registration algorithm template

Here a working template for developing an image registration algorithm will be presented. To see how compox algorithm should generally be structured, please refer to the algorithms/readme.md file.

The algorithm folder is structured as follows:

```plaintext
template_registration_algorithm/
    ├── __init__.py
    ├── Runner.py
    ├── pyproject.toml
    └── image_registration/
        ├── __init__.py
        └── registration_utils.py
    └── README.md
```

## The pyproject.toml file

The `pyproject.toml` is a file that contains the algorithm metadata. This file is used by compox to properly deploy the algorithm as a service. The `pyproject.toml` file should be placed in the root directory of the algorithm.

First, let's create the `pyproject.toml` file. Under the [project] section, you should provide the name and version of the algorithm. The name should be unique and should not contain any spaces. The version should be in the format `major.minor.patch`. The algorithm name and versions is used to identify the algorithm in compox so it is important to provide a unique name and version.

```toml
[project]
name = "template_registration_algorithm"
version = "1.0.0"
```

Next, we will fill out the [tool.compox] section. This section contains the metadata that compox uses to deploy the algorithm as a service. `algorithm_type` defines the algorithm input and output types, you may either use some predefined algorithm types or define your own. The predefined algorithm types are located in `compox.algorithm_utils`. For an image registration algorithm, we will use the the `Image2Alignment` type. This type is suitable for image segmentation as the input is a sequence of images and the output is a sequence homography matrices.

```toml
[tool.compox]
algorithm_type = "Image2Alignment"
```

Each algorithm type has a set of potential tags, which are used to specify the general algorithm functionality. Mutliple tags can be provided for one algorithm. For image registration algorithms, we will use the `image-alignment` tag. 
 
 ```toml
tags = ["image-alignment"]
```

The `description` field should contain a brief description of the algorithm.

```toml
description = "Generates homography matrices for aligning a sequence of images."
```

Here we will add a `max_translation` parameter that defines the maximum translation as a fraction of the image size. Because we want to set a range for the parameter, we will use the `float_range` type. The `default` field should contain the default value of the parameter. The `min` and `max` fields should contain the minimum and maximum values of the parameter. The `step` field should contain the step size of the parameter. The `adjustable` field should be set to `true` if we want to expose the parameter to the user to adjust.

```toml
 {name = "max_translation", description = "Maximum translation as a fraction of the image size.", config = {type = "float_range", default = 0.25, min = 0.0, max = 1.0, step = 0.05, adjustable = true}}
```

To see more information about the possible parameter types see the [How to create an algorithm module](../README.md/#additional-parameters) section. 

## The algorithm dependencies

The algorithm can use any libraries from the global compox environment. Additional dependencies can be provided as python submodules. Here we will use the `numpy` library to handle the image data. We also implemented a simple `image_registration` module that contains an `__init__.py` file and a `registration_utils.py` file. The `registration_utils.py` file contains the `get_random_translation` function that generates a random homography matrix with a maximum translation defined by the `max_translation` parameters as a fraction of the input image size. The `image_registration` module should be placed in the root directory of the algorithm.

```python
import numpy as np

def get_random_translation(image: np.ndarray, max_translation: float = 0.25):
    """
    Get a random translation matrix.

    Parameters
    ----------
    image : np.ndarray
        The image.
    max_translation : float
        The maximum translation.

    Returns
    -------
    np.ndarray
        The translation matrix.
    """

    # get the image dimensions
    height, width = image.shape[:2]
    h = np.eye(3)

    # random translation
    h[0, 2] = np.random.uniform(
        -max_translation * width, max_translation * width
    )
    h[1, 2] = np.random.uniform(
        -max_translation * height, max_translation * height
    )

    return h
```
## The Runner.py file

The `Runner.py` file is the main file of the algorithm. This file should contain the algorithm implementation. The `Runner.py` file should be placed in the root directory of the algorithm.

Because we specified the algorithm type as `Image2Alignment`, the `Runner.py` file should contain a class that inherits from the `Image2AlignmentRunner` class. The `Image2AlignmentRunner` class is located in the `compox.algorithm_utils` module. The `Image2AlignmentRunner` class contains the necessary methods to handle the input and output of the algorithm.


```python
import numpy as np

from compox.algorithm_utils.Image2AlignmentRunner import (
    Image2AlignmentRunner,
)
from image_registration.registration_utils import get_random_translation

class Runner(Image2AlignmentRunner):
    """
    The runner class for the denoiser algorithm.
    """

    def __init__(self, task_handler, device: str = "cpu"):
        """
        The image registration runner.
        """
        super().__init__(task_handler, device)
```

We can implement a `load_assets` method to load any assets that the algorithm requires upon initilaization of the Runner. The important bit is that the attributes that are loaded in the `load_assets` method are cached with the algorithm and do not have to be reloaded for each algorithm call. This can greatly speed up the algorithm execution. Since we do not need any assets for the image registration algorithm, we can leave the `load_assets` method empty.

```python
def load_assets(self):
    """
    Here you can load the assets needed for the algorithm. This can be
    the model, the weights, etc. The assets are loaded upon the first
    call of the algorithm and are cached with the algorithm instance.
    """
    pass
```

Next, we can implement the `inference` method, where we perform the registration of the images. The data will be passed to the `inference` method as a numpy array. The `inference` method return a list of homography matrices represented by numpy arrays. You can also report the progress of the algorithm by calling the `set_progress` method. The `set_progress` method takes a float value between 0 and 1, where 0 is the start of the algorithm and 1 is the end of the algorithm. The `log_message` method can be used to log messages to the compox log.

```python
def inference(self, data: np.ndarray, args: dict = {}) -> list[np.ndarray]:
    """
    Run the inference.

    Parameters
    ----------
    data : np.ndarray
        The input images

    Returns
    -------
    list[np.ndarray]
        The output homography matrices.
    """
    self.log_message("Starting inference.")
    # now we retrieve the input data
    max_translation = args.get("max_translation", 0.25)
    # we can post messages to the log
    self.log_message(f"Registering {data.shape[0]} images.")

    # we will denoise the images
    matrices = []
    for i in range(data.shape[0] - 1):
        matrix = get_random_translation(
            data[i], max_translation=max_translation
        )
        matrices.append(matrix)
        self.set_progress(i / data.shape[0])
    # we will pass the homography matrices to the output
    return matrices
```
To customize the behavior of fetching and processing the input data, and postprocessing and uploading the output data, we can implement the `preprocess` and `postprocess` methods. The `preprocess` method is called before the `inference` method and is used to fetch the input data. The `postprocess` method is called after the `inference` method and is used to process the output data. In our case, we will not implement any custom behavior for these methods. You can refer to the `compox.algorithm_utils.Image2AlignmentRunner` class for more information about these methods.

## Deploying the algorithm

To deploy the finished algorithm, you can use the `pdm run deployment template_registration_algorithm` command. This command will deploy the algorithm to the compox. The algorithm can also be added through compox systray interface by clicking the "Add Algorithm" button and selecting the algorithm directory.