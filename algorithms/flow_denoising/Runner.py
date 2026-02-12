import numpy as np
import matplotlib.pyplot as plt
import os

from files.src.flowdenoising_sequential import get_gaussian_kernel, OF_filter, no_OF_filter
from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner
from compox.algorithm_debug import debug

class Runner(Image2ImageRunner):

    def make_progress_callback(self, start, end):
        span = end - start

        def callback(frac):
            frac_clamped = max(0.0, min(1.0, float(frac)))
            self.set_progress(start + span * frac_clamped)
            
        return callback

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
        progress_callback = self.make_progress_callback(0.0, 1.0)
        if optical_flow == True:
            filtered_vol = OF_filter(input_data, kernel, l, w, 
                                     # progress_callback  # Optional progress reporting (see README, Section 6)
                                     )
        else:
            filtered_vol = no_OF_filter(input_data, kernel)

        # Visualization (if debugging)
        if os.getenv("COMPOX_DEBUG_SHOW") == "1": 
            self.visualize(input_data, filtered_vol)
        
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
    
if __name__ == "__main__":
    os.environ["COMPOX_DEBUG_SHOW"] = "1"
    debug(
        algo_dir ="algorithms/flow_denoising",
        data="C:\\Users\\jezek\\Documents\\Datasets\\T3D\\Algae\\PNG_Slices_test",
        params={"sigmas": [1, 1, 1], "level": 3, "winsize": 7, "optical_flow": True},
        device="cpu",
    )