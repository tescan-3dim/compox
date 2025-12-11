# FlowDenoising Deployment
This tutorial shows how to prepare and deploy an algorithm to **Compox** and run it in **TESCAN 3D Viewer** (and optionally **TESCAN Picannto**). We’ll use the **FlowDenoising** algorithm from [GitHub](https://github.com/ElsevierSoftwareX/SOFTX-D-23-00180?tab=readme-ov-file) as an example. The **FlowDenoising** algorithm suppresses high-frequency noise using an **optical-flow-driven Gaussian kernel**. The **FlowDenoising** source code is distributed under the terms of the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.html).

> **V. González-Ruiz, M.R. Fernández-Fernández, J.J. Fernández.**  
> *Structure-preserving Gaussian denoising of FIB-SEM volumes.*  
> *Ultramicroscopy* **246**, 113674 (2023).  
> DOI: [10.1016/j.ultramic.2022.113674](https://doi.org/10.1016/j.ultramic.2022.113674)

![Visualization](tutorial_images/visualization.png)

## 1. Compox Installation

For managing dependencies, we recommend using **`uv`** — it's fast and automatically handles both your environment and package versions. You can install it by this command:

```bash
pip install uv
```

You can set up your project and environment by running this command in your project’s root directory:

```bash
uv init
```

Once the environment is ready, install **Compox** using:

```bash
uv add compox
```

Generate a server config:

```bash
uv run compox generate-config --path app_server.yaml
```

Config `app_server.yaml` should appear in project’s root directory. Now create an empty folder called **`algorithms`** in your project’s root directory. You now have everything ready to start creating algorithms.

```plaintext
project_root/
├── algorithms/
└── app_server.yaml
```

## 2. Importing **FlowDenoising** as submodule ##
Create an algorithm root directory inside **`algorithms`** directory. We’ll call it flow_denoising:

From within this new directory, you can download the algorithm’s source code from GitHub into a subfolder named **`files`** by running:

```bash
git submodule add https://github.com/ElsevierSoftwareX/SOFTX-D-23-00180.git files
```

After importing the submodule, your project structure should look like this:

```plaintext
project_root/
├── algorithms/
│   └── flow_denoising/
│       └── files/
│           ├── manual/...
│           ├── src/...
│           └── LICENCE.txt
└── app_server.yaml
```

The repository includes a `requirements.txt` at `algorithms/flow_denoising/files/src/requirements.txt`. Install the dependencies:

```bash
uv add --requirements algorithms/flow_denoising/files/src/requirements.txt
```

## 3. Creating the `pyproject.toml` file

The **`pyproject.toml`** file contains metadata and configuration for your algorithm. It is used by **Compox** during the deployment process to register the algorithm as a service. Place it in the **`flow_denoising`** directory:

```plaintext
project_root/
├── algorithms/
│   └── flow_denoising/
│       ├── files/
│       │   ├── manual/...
│       │   ├── src/...
│       │   └── LICENCE.txt
│       └── pyproject.toml
└── app_server.yaml
```

### [project] section – basic package information ###

This section defines general information about your algorithm. At minimum, you must include the **name** and **version** fields. The version follows the major.minor.patch format (e.g. 0.1.0).

```toml
[project]
name = "flow_denoising"
version = "0.1.0"
```

### [tool.compox] section – Algorithm-specific configuration ###

This section contains settings used by **Compox** itself — how your algorithm behaves, what devices it supports, and which parameters users can configure. Although all fields here are optional, it’s recommended to include them for better integration and usability.

```toml
[tool.compox]
algorithm_type = "Image2Image"
tags = ["image-denoising", "Image2Image"]
description = "Removes most of the high-frequency components of the data using a Optical-Flow-driven Gaussian kernel with abilities to preserve the structures and avoid blurring, and outputs the filtered volume"
supported_devices = ["cpu", "gpu"]
default_device = "cpu"
additional_parameters = [
    {name = "sigmas", description = "Standard deviations of the Gaussian kernel in each dimension.", config = {type = "int_list", default = [1, 1, 1], adjustable = true}},
    {name = "level", description = "Level parameter for optical flow filtering.", config = {type = "int", default = 3, adjustable = true}},
    {name = "winsize", description = "Window size parameter for optical flow filtering.", config = {type = "int", default = 7, adjustable = true}},
    {name = "optical_flow", description = "Enable or disable optical flow filtering.", config = {type = "bool", default = true, adjustable = true}},]

check_importable = false
obfuscate = true
hash_module = true
hash_assets = true
```

#### Explanation of key fields: ####

For a detailed explanation of all `[tool.compox]` fields, see the
[How to create an algorithm module](../README.md#the-pyprojecttoml-file).


## 4. Creating `Runner.py` ##

`Runner.py` is the entry point **Compox** calls to execute your algorithm. Place it in `algorithms/flow_denoising`:

```plaintext
project_root/
├── algorithms/
│   └── flow_denoising/
│       ├── files/
│       │   ├── manual/...
│       │   ├── src/...
│       │   └── LICENCE.txt
│       ├── pyproject.toml
│       └──Runner.py
└── app_server.yaml
```

### Importing dependencies ###
For this example, we’ll use **NumPy** for numerical operations. Make sure it is installed in your environment (if not, you can add it with):

```bash
uv add numpy
```

Since this algorithm is of type **Image2Image**, we will inherit from **Image2ImageRunner**, which can be imported from `compox.algorithm_utils.Image2ImageRunner`.

For debugging, we can also import the helper function **debug** from `compox.algorithm_debug`.

From the **FlowDenoising** source code (in the submodule `files/src/flowdenoising_sequential`), we will use three main functions:

* **get_gaussian_kernel**
* **OF_filter**
* **no_OF_filter**

Here’s the complete set of imports:

```python
import numpy as np

from files.src.flowdenoising_sequential import get_gaussian_kernel, OF_filter, no_OF_filter
from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner
from compox.algorithm_debug import debug
```

### Initializing the `Runner` class ###
As mentioned earlier, the `Runner` class should inherit from **Image2ImageRunner**. This base class already handles data fetching, preprocessing, and uploading the results back. For this algorithm, you only need to override the `inference` method. It receives the input data as an **np.ndarray** together with a **dict** of parameters, and must return the processed data as an **np.ndarray**. If you want to customize how data is fetched or uploaded, you can override these methods yourself or inherit directly from **BaseRunner**. For more details, see [How to create an algorithm module](../README.md#the-runnerpy-file).

 A minimal skeleton looks like this:

```python
class Runner(Image2ImageRunner):

    def inference(self, input_data: np.ndarray, args: dict = {}) -> np.ndarray:
        pass
```

### Implementing FlowDenoising in the `inference` method ###
First, extract all user-defined parameters from the input dictionary `args`:

```python
# Extract parameters
sigmas = args["sigmas"]
l = args["level"] 
w =  args["winsize"]
optical_flow = args["optical_flow"]
```

Next, compute Gaussian kernels for each dimension:

```python
# Create Gaussian kernels for each dimension
k_x = get_gaussian_kernel(int(sigmas[0]))
k_y = get_gaussian_kernel(int(sigmas[1]))
k_z = get_gaussian_kernel(int(sigmas[2]))
kernel = [k_x, k_y, k_z]
```

Depending on the boolean value of `optical_flow`, apply the appropriate FlowDenoising function to the input data:

```python
# Apply filtering
if optical_flow == True:
    filtered_vol = OF_filter(input_data, kernel, l, w)
else:
    filtered_vol = no_OF_filter(input_data, kernel)
```

Finally, ensure the output is of type `float32` and normalized to the range `[0, 1]`:

```python
# Ensure output data is float32
out_data = filtered_vol.astype(np.float32).copy()

# Normalize output data to [0, 1]
vmin = float(np.nanmin(out_data))
vmax = float(np.nanmax(out_data))
if vmax > vmin:
    out_data = (out_data - vmin) / (vmax - vmin)
else:
    out_data[:] = 0.0

return out_data
```
Full example: `Runner.py`

```python
import numpy as np

from files.src.flowdenoising_sequential import get_gaussian_kernel, OF_filter, no_OF_filter
from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner
from compox.algorithm_debug import debug

class Runner(Image2ImageRunner):

    def inference(self, input_data: np.ndarray, args: dict = {}) -> np.ndarray:

        # Extract parameters
        sigmas = args["sigmas"]
        l = args["level"] 
        w =  args["winsize"]
        optical_flow = args["optical_flow"]

        # Create Gaussian kernels for each dimension
        k_x = get_gaussian_kernel(int(sigmas[0]))
        k_y = get_gaussian_kernel(int(sigmas[1]))
        k_z = get_gaussian_kernel(int(sigmas[2]))
        kernel = [k_x, k_y, k_z]

        # Apply filtering
        if optical_flow == True:
            filtered_vol = OF_filter(input_data, kernel, l, w)
        else:
            filtered_vol = no_OF_filter(input_data, kernel)

        # Ensure output data is float32
        out_data = filtered_vol.astype(np.float32).copy()

        # Normalize output data to [0, 1]
        vmin = float(np.nanmin(out_data))
        vmax = float(np.nanmax(out_data))
        if vmax > vmin:
            out_data = (out_data - vmin) / (vmax - vmin)
        else:
            out_data[:] = 0.0

        return out_data
```

## 5. Debugging `Runner.py`
Once your first implementation is ready, you will likely want to run it on a small data sample with debugging support to verify its behavior. The `compox.algorithm_debug.debug` function allows you to test your algorithm **without launching TESCAN 3D Viewer**. It does not load data the same way as the Viewer — the debug tool simply reads the input files directly from disk. However, the rest of the execution pipeline behaves the same: the data is stored in the database, then the `preprocess`, `inference`, and `postprocess` steps run in the same order, and the results are uploaded back to the database. If everything completes successfully, you should see an output similar to this:

```plaintext
2025-11-27 15:04:58.393 | INFO     | compox.algorithm_utils.BaseRunner:run:244 - Starting execution.
2025-11-27 15:04:58.395 | INFO     | compox.algorithm_utils.BaseRunner:preprocess_base:287 - Data preprocessing finished in 0.0 seconds
2025-11-27 15:04:58.395 | INFO     | compox.algorithm_utils.BaseRunner:inference_base:336 - Running inference.
2025-11-27 15:05:00.192 | INFO     | compox.algorithm_utils.BaseRunner:inference_base:339 - Inference finished in 1.8 seconds
2025-11-27 15:05:00.192 | INFO     | compox.algorithm_utils.BaseRunner:postprocess_base:386 - Postprocessing output data.
2025-11-27 15:05:00.192 | INFO     | compox.tasks.TaskHandler:post_data:904 - Uploading 6 results to the database.
2025-11-27 15:05:00.192 | INFO     | compox.algorithm_utils.BaseRunner:postprocess_base:389 - Postprocessing finished in 0.0 seconds
2025-11-27 15:05:00.192 | INFO     | compox.algorithm_utils.BaseRunner:run:253 - Execution completed in 1.8 seconds.
2025-11-27 15:05:00.192 | INFO     | compox.tasks.TaskHandler:_log_file_stats:402 - File fetching stats: 6.0 files fetched in 0.0010 seconds.
2025-11-27 15:05:00.192 | INFO     | compox.tasks.TaskHandler:_log_file_stats:406 - File posting stats: 6.0 files posted in 0.0000 seconds.
```

### Debug function inputs ###
The debug function accepts four inputs:

- **data** – path to a dataset on your local disk. This can be either path to folder containing image slices (**.jpg**, **.png**, **.tiff**), or a 3D volume (**.tiff**, **.npy**, **.hdf5**).

- **algo** – path to the root directory of your algorithm.

- **params** – a dictionary containing additional algorithm parameters.

- **device** – compute device to run the algorithm on (e.g., `"cpu"` or `"gpu"`).

You can use your own data, or you can use one of the sample datasets included in **TESCAN 3D Viewer**.  
For example, the **Oscillatoria** dataset can be downloaded from the **Welcome Page** of the Viewer.

![Sample Dataset](tutorial_images/sample_dataset.png)

Its default location is: 

```plaintext
`...\User\Documents\TESCAN 3DIM, s.r.o\TESCAN 3D Viewer\Sample projects and datasets\Oscillatoria_dataset\Oscillatoria3D.tif`. 
```
You can also import any dataset into the Viewer, crop it, export it, and then use that exported data for debugging.


### Running debug tool ###

You have two main options for debugging:
* Running your script in debug mode with `compox.algorithm_debug.debug()`
* Debug through the CLI

#### Option 1: Use the `debug()` Function ####
Add this code block at the bottom of your **`Runner.py`** and run it in your IDE (e.g. VS Code, PyCharm). When running `Runner.py` directly, the `algo` argument can be omitted because the debug tool detects the algorithm folder automatically.

```python
if __name__ == "__main__":
    debug(
        data="path to data",
        params={"sigmas": [1, 1, 1], "level": 3, "winsize": 7, "optical_flow": True},
        device="cpu",
    )
```

You can also use Python’s built-in debugger — simply insert a `breakpoint()` wherever you want to pause execution and run script manually:

```bash
uv run .\algorithms\flow_denoising\Runner.py
```

#### Option 2: Debug through the CLI ####
Just insert `breakpoint()` wherever you want to pause execution. Then run your algorithm from the terminal like this:

```bash
uv run compox debug run --data "path to data" --algo "path to Flowdenoising algorithm" --params '{"sigmas": [1, 1, 1], "level": 3, "winsize": 7, "optical_flow": true}' --device "cpu"
```

### Visualization of filtered data ###
If you want to visually compare the original and filtered data during debugging, you can add a small helper method to your Runner class. For example:

```python
import matplotlib.pyplot as plt

def visualize(self, input_data, filtered_vol):
        plt.subplot(1, 2, 1)
        plt.imshow(input_data[input_data.shape[0] // 2, :, :], cmap='gray')
        plt.title("Original")
        plt.axis('off')

        plt.subplot(1, 2, 2)
        plt.imshow(filtered_vol[filtered_vol.shape[0] // 2, :, :], cmap='gray')
        plt.title("Filtered")
        plt.axis('off')

        plt.show()
```

To show this result only when debugging, we recommend using an environment variable. You can set it in the `__main__` block:

```python
import os

if __name__ == "__main__":
    os.environ["COMPOX_DEBUG_SHOW"] = "1"
    debug(
        data="path to data",
        params={"sigmas": [1, 1, 1], "level": 3, "winsize": 7, "optical_flow": True},
        device="cpu",
    )
```

Then, in your `inference` method, call the `visualize` function only when this environment variable is set:

```python
if os.getenv("COMPOX_DEBUG_SHOW") == "1":
    self.visualize(input_data, filtered_vol)
```

This way, the visualization will appear when you run `Runner.py` directly for debugging, but it will not show any extra windows when the algorithm is executed from **TESCAN 3D Viewer**. After running, you should see a side-by-side comparison of the original and filtered slices:

![Visualization](tutorial_images/visualization.png)

## 6. Algorithm Deployment ##
Once your algorithm is implemented and ready, you can deploy it to **Compox** using two options:
* **Single command**
* **GUI**

### Option 1: Deploy with single command ###
Simply run this command:

```bash
uv run compox deploy-algorithms --config app_server.yaml
```

If you are running the server for the first time, the process might take a bit longer because **Compox** needs to download and initialize the **MinIO** service.

### Option 2: Deploy with GUI ###

As an alternative, you can use the built-in **Compox** GUI to manage algorithms more conveniently. First, edit your `app_server.yaml` file and enable GUI controls by setting the following values in the `gui` section:

```yaml
gui:
  algorithm_add_remove_in_menus: true
  use_systray: true
```

Then start the **Compox** server with:

```bash
uv run compox run --config app_server.yaml
```

After running this command, you should see the **Compox** icon appear in the **system tray**:

![SysTray](tutorial_images/SysTray.png)

Right-click the icon to open the context menu.
From there, you can:
* View all currently deployed algorithms
* Add a new algorithm by selecting its folder (in our case, choose `algorithms/flow_denoising`)

### Stopping the Server ###
* If you are using the GUI, right-click the tray icon and select **Quit** to stop the server. Using `Ctrl + C` in the terminal will not close the server properly when the GUI mode is active.
* If you are running from the terminal (without GUI), you can simply press `Ctrl + C`.

## 7. Running FlowDenoising in **`TESCAN 3D Viewer`** ##
After deploying the algorithm to **Compox**, you can run it directly on data loaded in **TESCAN 3D Viewer**.

### Step 1: Start the Compox server

Before launching `TESCAN 3D Viewer`, make sure the **Compox** is running. Start the server with:

```bash
uv run compox run --config app_server.yaml
```

### Step 2: Connect `TESCAN 3D Viewer` to **Compox** ###

After starting the server, open `TESCAN 3D Viewer`.
If you see an error saying that the Compox backend connection failed, don’t worry — you can fix this by adding a new backend manually:

1. Go to **Menu → Tools → Preferences**
2. Click **Add new backend**
3. Set the **Protocol** type to `HTTP`
4. Check the **Custom** checkbox
5. Set the **Port** number based on your `app_server.yaml` file
    * The default port is 5461
    * If you changed it, you can verify the value in the first line of `app_server.yaml`

Your **Preferences** window should now look like this:

![Preferences](tutorial_images/Preferences.png)

### Step 3: Run the algorithm from the **Compox** extension

Once the backend is connected, import your dataset in `TESCAN 3D Viewer`.

Then open the **Compox Backend Extension** by clicking the **Compox** icon in the upper-right corner of the interface.

![Preferences](tutorial_images/Compox_Extension.png)

In the **Compox Backend Extension** window you can:
* Select the algorithm you want to run
* Read its description
* Adjust parameters defined in your `pyproject.toml` file

After setting the parameters, click **Run** to start the inference. A progress bar should appear, and the algorithm will run on your dataset.