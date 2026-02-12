import numpy as np
import zarr
import pytorch_lightning as pl
from pathlib import Path
import tempfile
import json
import shutil
import pickle
import os
import matplotlib.pyplot as plt
import io
import torch
import torch.nn as nn

from compox.algorithm_utils.Image2SegmentationRunner import Image2SegmentationRunner
from particleseg3d.inference.inference import predict_cases
from particleseg3d.inference.model_nnunet import Nnunet
from compox.algorithm_debug import debug


class ParticleSegNnUNet(Nnunet):
    def __init__(self, folds_assets, json_assets, device: str = "cuda") -> None:
        pl.LightningModule.__init__(self)

        self.nnunet_trainer = "nnUNetTrainerV2__nnUNetPlansv2.1"
        self.network = self._load_from_assets(folds_assets, json_assets)
        self.final_activation = nn.Softmax(dim=2)
        self.tta = True

    def _load_from_assets(self, folds_assets, json_assets) -> nn.ModuleList:
        ensemble = []
        for ckpt_obj, json_obj in zip(folds_assets, json_assets):
            # Load model config from json
            json_stream = io.TextIOWrapper(json_obj, encoding="utf-8")
            model_config = json.load(json_stream)

            # Initialize network
            network = self.initialize_network(model_config, "3d_fullres")

            # Load model state dict from checkpoint
            state = torch.load(
                ckpt_obj,
                map_location=self._device,
                weights_only=False,
            )

            # Load state dict into network
            network.load_state_dict(state["state_dict"])
            ensemble.append(network)

        ensemble = nn.ModuleList(ensemble)
        return ensemble


class Runner(Image2SegmentationRunner):

    def make_progress_callback(self, start, end):
        span = end - start

        def callback(frac):
            frac = max(0.0, min(1.0, float(frac)))
            self.set_progress(start + span * frac)

        return callback


    def inference(self, input_data: np.ndarray, args: dict = {}) -> np.ndarray:

        # Prepare data and setup model
        zarr_path, output_path = self.prepare_data(input_data, args)

        # Run prediction
        progress_callback = self.make_progress_callback(0.00, 1.00)
        predict_cases(load_dir = zarr_path, 
                      save_dir = output_path,
                      names = None,
                      trainer = self.trainer,
                      model = self.model,
                      config = self.config,
                      target_particle_size = 60,
                      target_spacing = 0.1,
                      batch_size = 6,
                      processes=4,
                      min_rel_particle_size = 0.0005,
                      zscore=(5850.29762143569, 7078.294543817302),
                      # progress_callback=progress_callback  # Optional progress reporting (see README, Section 6)
        )
        # Load output as numpy array
        mask_zarr = output_path / "data" / "data.zarr"
        mask_np = zarr.open(mask_zarr, mode="r")[:]

        if os.getenv("COMPOX_DEBUG_SHOW") == "1":
            self.visualize(input_data, mask_np)


        # Delete temporary Zarr store
        shutil.rmtree(zarr_path, ignore_errors=True)

        return mask_np.astype(np.uint8)


    def load_assets(self) -> None:
        model_dir = "assets/Task310_particle_seg/nnUNetTrainerV2_slimDA5_touchV5__nnUNetPlansv2.1/"
        # Load model config
        pkl_path = os.path.join(model_dir, "plans.pkl")
        asset_pkl = self.fetch_asset(pkl_path)
        self.config = pickle.load(asset_pkl)

        # prepare Trainer
        self.trainer = pl.Trainer(gpus=1, precision=16, logger=False)

        # prepare Mode
        folds_assets = []
        json_assets = []
        for fold in range(5):
            # Load model for each fold
            fold_path = os.path.join(model_dir, f"fold_{fold}/model_best.model")
            fold_asset = self.fetch_asset(fold_path)
            folds_assets.append(fold_asset)
            
            # Load json config for each fold
            json_path = os.path.join(model_dir, f"fold_{fold}/debug.json")
            json_asset = self.fetch_asset(json_path)
            json_assets.append(json_asset)
        self.model = ParticleSegNnUNet(folds_assets, json_assets)
        self.model.eval()

    
    def prepare_data(self, input_data: np.ndarray, args: dict) -> tuple[Path, Path]:

        # Temp directory for Zarr store
        tmpdir = tempfile.mkdtemp()
        zarr_path = Path(tmpdir)

        # Save input data as Zarr
        images_path = (zarr_path / "images/data.zarr")
        images_path.parent.mkdir(parents=True, exist_ok=True)
        zarr.save(images_path, input_data.astype("float64"))

        # Create JSON metadata
        metadata = {
            "data": {
                "spacing": args["spacing"],
                "particle_size": args["particle_size"],
            }
        }
        metadata_path = zarr_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        # Prepare output path
        output_path = (zarr_path / "output")
        output_path.mkdir(parents=True, exist_ok=True)

        return zarr_path, output_path
    
    def visualize(self, input_data: np.ndarray, mask: np.ndarray) -> None:

        # Visualize the middle slice of the input data and the segmented mask
        mask_slice = mask[:, :, mask.shape[2] // 2]
        input_data_slice = input_data[:, :, input_data.shape[2] // 2]

        # Create random colors for each unique particle ID
        rng = np.random.default_rng(seed=42)
        rgb = np.zeros((*mask_slice.shape, 3), dtype=np.float32)
        ids = np.unique(mask_slice)
        ids = ids[ids != 0]
        colors = rng.random((len(ids), 3))
        for i, c in zip(ids, colors):
            rgb[mask_slice == i] = c

        # Plot input data and segmented mask
        plt.subplot(1, 2, 1)
        plt.imshow(input_data_slice, cmap='gray')
        plt.title("Input data")
        plt.axis('off')

        plt.subplot(1, 2, 2)
        plt.imshow(input_data_slice, cmap='gray')
        plt.imshow(rgb, alpha=(mask_slice > 0) * 0.5)
        plt.title("Segmented mask")
        plt.axis('off')
        plt.show()

    
if __name__ == "__main__":
    random_data = np.random.rand(100, 200, 50)
    np.save("data.npy", random_data)

    os.environ["COMPOX_DEBUG_SHOW"] = "1"
    debug(
        algo_dir="algorithms/particle_seg_3d/",
        data="data.npy",
        params={"particle_size": 1.0, "spacing": 0.01},
        device="gpu",
    )