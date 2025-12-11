import os, glob, io, uuid, h5py
import numpy as np
from PIL import Image, ImageSequence

from compox.tasks.DebuggingTaskHandler import DebuggingTaskHandler

class LocalDebugSession:
    """
    Helper class for running Compox algorithms locally in a simplified
    "debug" environment.

    It sets up a fake `TaskHandler`, uploads image data to an in-memory database, 
    and runs the specified algorithm. It allows developers to test and debug 
    algorithms without deploying them to a full Compox server.

    Parameters
    ----------
    task_id : str, optional
        Unique ID for the debugging task. Default is `"local-debug"`.
    device : str, optional
        Target device to run the algorithm on. Default is `"cpu"`.
    tmp_bucket : str, optional
        Temporary in-memory storage bucket name for the mock database.
        Default is `"data-store"`.
    """

    def __init__(self, task_id="local-debug", device="cpu", tmp_bucket="data-store"):
        self.task = DebuggingTaskHandler(task_id)
        self.task.set_as_current_task_handler()
        self.bucket = tmp_bucket
        self.device = device


    def _to_h5_bytes(self, arr):
        """
        Convert a NumPy array into an in-memory HDF5 file. Each image slice 
        is stored as a small binary HDF5 object (byte array), which mimics 
        the format expected by the Compox database.

        Parameters
        ----------
        arr : np.ndarray
            Image array to be serialized into HDF5 format.

        Returns
        -------
        bytes
            The in-memory representation of the HDF5 file.
        """

        bio = io.BytesIO()
        with h5py.File(bio, "w") as f:
            f.create_dataset("image", data=arr)
        return bio.getvalue()


    def load_data(self, source):
        """
        Load image data from a specified source into the local debug database.
        
        Parameters
        ----------
        source : str
            Path to the data source. Can be a folder containing image slices,
            a single image file (PNG/JPEG/TIFF), a .npy file, or an HDF5 file.

        Returns
        -------
        list[str]
            A list of generated object IDs (UUIDs) corresponding to the stored
            HDF5 image slices.
        """
        if os.path.isdir(source):
            return self.load_from_folder(source)
        else:
            ext = os.path.splitext(source)[1].lower()
            if ext in (".tif", ".tiff"):
                return self.load_from_tiff(source)
            elif ext in (".png", ".jpg", ".jpeg"):
                return self.load_from_pil_image(source)
            elif ext == ".npy":
                return self.load_from_npy(source)
            elif ext in (".h5", ".hdf5"):
                return self.load_from_h5(source)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            
    
    def load_from_npy(self, filepath: str) -> list[str]:
        """
        Load a .npy file and store it as individual 2D slices in the fake database.

        Parameters
        ----------
        filepath : str
            Path to the .npy file containing a 2D or 3D NumPy array.

        Returns
        -------
        list[str]
            A list of generated object IDs (UUIDs) corresponding to the stored
            HDF5 image slices.
        """
        arr = np.load(filepath)
        nd = arr.ndim

        slices_bytes: list[bytes] = []

        if nd == 3:
            for z in range(arr.shape[0]):
                slices_bytes.append(self._to_h5_bytes(arr[z]))
        elif nd == 2:
            slices_bytes.append(self._to_h5_bytes(arr))
        else:
            raise ValueError(
                f"Unsupported numpy array ndim={nd} in '{filepath}'. "
                "Expected 2D (H, W) or 3D (Z, H, W)."
            )

        ids = [str(uuid.uuid4()) for _ in slices_bytes]
        self.task.database_connection.put_objects(self.bucket, ids, slices_bytes)
        return ids
    

    def load_from_h5(self, filepath: str) -> list[str]:
        """
        Load a 2D or 3D dataset from an HDF5 file and store it as 2D slices.

        Parameters
        ----------
        filepath : str
            Path to the .h5/.hdf5 file.

        Returns
        -------
        list[str]
            List of object IDs corresponding to stored slices.

        Raises
        ------
        KeyError
            If no suitable 2D/3D dataset can be found in the file.
        ValueError
            If the selected dataset has unsupported number of dimensions.
        """
        slices_bytes: list[bytes] = []

        def _find_datasets(f):
            found = []
            def visitor(name, obj):
                if isinstance(obj, h5py.Dataset) and obj.ndim in (2, 3):
                    found.append((name, obj))
            f.visititems(visitor)
            return found

        with h5py.File(filepath, "r") as f:

            datasets = _find_datasets(f)

            if not datasets:
                raise KeyError(
                    f"No suitable 2D/3D dataset found anywhere in '{filepath}'. "
                    f"Available top-level groups: {list(f.keys())}"
                )

            _, dset = datasets[0]

            if dset.ndim == 2:
                slices_bytes.append(self._to_h5_bytes(dset[()]))

            elif dset.ndim == 3:
                for z in range(dset.shape[0]):
                    slices_bytes.append(self._to_h5_bytes(dset[z, ...]))
            else:
                raise ValueError("Internal error: filtered ndim != 2/3")

        ids = [str(uuid.uuid4()) for _ in slices_bytes]
        self.task.database_connection.put_objects(self.bucket, ids, slices_bytes)
        return ids


    def load_from_pil_image(self, filepath: str) -> list[str]:
        """
        Load a single image file (PNG/JPEG/...) and store it as one 2D slice
        in the debug database.

        Parameters
        ----------
        filepath : str
            Path to the image file.

        Returns
        -------
        list[str]
            List with a single object ID corresponding to the stored slice.
        """
        with Image.open(filepath) as img:
            arr = np.asarray(img)

        slice_bytes = self._to_h5_bytes(arr)
        obj_id = str(uuid.uuid4())

        self.task.database_connection.put_objects(self.bucket, [obj_id], [slice_bytes])
        return [obj_id]

    def load_from_tiff(self, filepath: str) -> list[str]:
        """
        Load a TIFF file (single-page or multi-page) and store each page
        as a separate 2D slice in the fake database.

        Parameters
        ----------
        filepath : str
            Path to the .tif/.tiff file.

        Returns
        -------
        list[str]
            List of object IDs corresponding to stored slices.
        """
        slices_bytes: list[bytes] = []

        with Image.open(filepath) as im:
            frames = list(ImageSequence.Iterator(im))

            if not frames:
                raise ValueError(f"TIFF file '{filepath}' contains no frames.")

            for frame in frames:
                arr = np.asarray(frame)
                slices_bytes.append(self._to_h5_bytes(arr))

        ids = [str(uuid.uuid4()) for _ in slices_bytes]
        self.task.database_connection.put_objects(self.bucket, ids, slices_bytes)
        return ids


    def load_from_folder(self, folder, exts=(".tif", ".tiff", ".png", ".jpg", ".jpeg")):
        """
        Load a folder of image slices (e.g., PNG/TIFF) into the local database.
        Each image is read from disk, converted to a NumPy array, serialized
        into an HDF5 byte object, and uploaded into the fake database.

        Parameters
        ----------
        folder : str
            Path to the folder containing image slices.
        exts : tuple of str, optional
            Allowed image extensions. Default is `(".tif", ".tiff", ".png", ".jpg", ".jpeg")`.

        Returns
        -------
        list[str]
            A list of generated object IDs (UUIDs) corresponding to the stored
            HDF5 image slices.

        Raises
        ------
        ValueError
            If no supported image slices are found in the folder.
        """

        paths = [p for p in sorted(glob.glob(os.path.join(folder, "*"))) if p.lower().endswith(exts)]
        if not paths:
            raise ValueError(
                f"No supported image slices found in folder '{folder}'. "
                f"Supported extensions: {exts}"
            )
        ext = os.path.splitext(paths[0])[1].lower()
        if ext not in exts:
            raise ValueError(
                f"Folder loader expects slice image formats {exts}, "
                f"but found '{ext}' in folder: {folder}. "
                "If you want to load numpy/HDF5 volumes, pass the file path directly "
                "instead of a folder."
            )
        files = []
        for p in paths:
            with Image.open(p) as img:
                files.append(self._to_h5_bytes(np.asarray(img)))
        ids = [str(uuid.uuid4()) for _ in files]
        self.task.database_connection.put_objects(self.bucket, ids, files)
        return ids


    def run(self, algo_dir, inputs: dict, args: dict | None = None):
        """
        Execute a Compox algorithm locally. This method fetches and runs the algorithm 
        from the specified folder.

        Parameters
        ----------
        algo_dir : str
            Path to the directory containing the algorithm implementation.
        inputs : dict
            Input metadata for the algorithm (e.g. dataset IDs).
        args : dict, optional
            Algorithm parameters passed as keyword arguments.

        Returns
        -------
        Any
            The algorithm's output object, as returned by its `run()` method.
        """

        runner = self.task.fetch_algorithm(algo_dir, device=self.device)
        return runner.run(inputs, args=args or {})