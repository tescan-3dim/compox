"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from t3d_server.database_connection.BaseConnection import BaseConnection
import tempfile
import os


class TempfileConnection(BaseConnection):
    """
    A connection class for a local file system "database". This class inherits from
    the BaseConnection class and implements the methods for interacting with a local
    tempfile file structure mimicking an object storage database. Can be used for
    testing and debugging purposes, or when a real database is not available for
    local deployment of the application.

    Parameters
    ----------
    temp_folder_name : str
        The name of the temporary folder.
    """

    def __init__(self, temp_folder_name: str = "pcb_temp"):
        """
        Initializes the LocalConnection.

        Parameters
        ----------
        temp_folder_name : str
            The name of the temporary folder.
        """
        super().__init__()
        self.temp_folder = tempfile.TemporaryDirectory(prefix=temp_folder_name)

    def list_collections(self) -> list:
        """
        List all subdirectories in the temporary folder.

        Returns
        -------
        list
            The list of subdirectories.
        """
        return os.listdir(self.temp_folder.name)

    def check_collections_exists(self, collection_names: list[str]) -> list[bool]:
        """
        Check if the subdirectories exist in the temporary folder.

        Parameters
        ----------
        collection_names : list[str]
            The subdirectory names.

        Returns
        -------
        list
            The list of booleans indicating if the subdirectories exist.
        """
        return [
            os.path.isdir(os.path.join(self.temp_folder.name, name))
            for name in collection_names
        ]

    def delete_collections(self, collection_names: list[str]) -> None:
        """
        Delete the subdirectories in the temporary folder including all files.

        Parameters
        ----------
        collection_names : list[str]
            The subdirectory names.
        """
        for name in collection_names:
            os.rmdir(os.path.join(self.temp_folder.name, name))

    def create_collections(self, collection_names: list[str]) -> None:
        """
        Create subdirectories in the temporary folder.

        Parameters
        ----------
        collection_names : list[str]
            The subdirectory names.
        """
        for name in collection_names:
            os.mkdir(os.path.join(self.temp_folder.name, name))

    def list_objects(self, collection_name: str) -> list[str]:
        """
        List all files in a subdirectory.

        Parameters
        ----------
        collection_name : str
            The subdirectory name.

        Returns
        -------
        list
            The list of files.
        """
        return os.listdir(os.path.join(self.temp_folder.name, collection_name))

    def check_objects_exist(
        self, collection_name: str, object_names: list[str]
    ) -> list[bool]:
        """
        Check if files exist in a subdirectory.

        Parameters
        ----------
        collection_name : str
            The subdirectory name.
        object_names : list[str]
            The file names.

        Returns
        -------
        list
            The list of booleans indicating if the files exist.
        """
        return [
            os.path.isfile(os.path.join(self.temp_folder.name, collection_name, name))
            for name in object_names
        ]

    def delete_objects(self, collection_name: str, object_names: list[str]) -> None:
        """
        Delete files in a subdirectory.

        Parameters
        ----------
        collection_name : str
            The subdirectory name.
        object_names : list[str]
            The file names.
        """
        for name in object_names:
            os.remove(os.path.join(self.temp_folder.name, collection_name, name))

    def get_objects(self, collection_name: str, object_names: list[str]) -> list[bytes]:
        """
        Get files from a subdirectory.

        Parameters
        ----------
        collection_name : str
            The subdirectory name.
        object_names : list[str]
            The file names.

        Returns
        -------
        list
            The list of file bytes.
        """
        return [
            open(
                os.path.join(self.temp_folder.name, collection_name, name), "rb"
            ).read()
            for name in object_names
        ]

    def put_objects(
        self, collection_name: str, object_names: list[str], objects: list[bytes]
    ) -> None:
        """
        Put files in a subdirectory.

        Parameters
        ----------
        collection_name : str
            The subdirectory name.
        object_names : list[str]
            The file names.
        objects : list[bytes]
            The file bytes.
        """
        for name, obj in zip(object_names, objects):
            with open(
                os.path.join(self.temp_folder.name, collection_name, name), "wb"
            ) as f:
                f.write(obj)

    def put_objects_with_duplicity_check(
        self, collection_name: str, object_names: list[str], objects: list[bytes]
    ) -> list[bool]:
        """
        Put files in a subdirectory with a check for existing files.

        Parameters
        ----------
        collection_name : str
            The subdirectory name.
        object_names : list[str]
            The file names.
        objects : list[bytes]
            The file bytes.

        Returns
        -------
        list
            The list of booleans indicating if the files were put.
        """
        object_exists = self.check_objects_exist(collection_name, object_names)
        for i, (name, obj, exists) in enumerate(
            zip(object_names, objects, object_exists)
        ):
            if not exists:
                with open(
                    os.path.join(self.temp_folder.name, collection_name, name), "wb"
                ) as f:
                    f.write(obj)
        return object_exists
