"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""


class BaseConnection:
    """
    A generic database connection class. This class is meant to be inherited by
    specific database connection classes. It defines the methods for interacting
    with the object storage database. It assumes that the database is structured
    as a set of collections, where each collection contains a set of
    objects. The objects can be any type of data, such as files, images, or
    other objects. The objects are acessed by their names, and the collections
    are accessed by their names. For example, in an S3 database, the collections
    would be the buckets, and the objects would be the files in the buckets.
    """

    def __init__(self):
        pass

    def list_collections(self) -> list:
        """
        Lists all object collections.

        Returns
        -------
        list
            The list of object collections.
        """
        raise NotImplementedError

    def check_collections_exists(self, collection_names: list[str]) -> list[bool]:
        """
        Checks if collections exist.

        Parameters
        ----------
        collection_names : list[str]
            The collection names.

        Returns
        -------
        list[bool]
            The list of booleans indicating if the collections exist.
        """
        raise NotImplementedError

    def delete_collections(self, collection_names: list[str]) -> None:
        """
        Deletes collections.

        Parameters
        ----------
        collection_names : list[str]
            The collection names.
        """
        raise NotImplementedError

    def create_collections(self, collection_names: list[str]) -> None:
        """
        Creates collections.

        Parameters
        ----------
        collection_names : list[str]
            The collection names.
        """
        raise NotImplementedError

    def list_objects(self, collection_name: str) -> list[str]:
        """
        Lists all objects in a collection.

        Parameters
        ----------
        collection_name : str
            The collection name.

        Returns
        -------
        list
            The list of objects in the collection.
        """
        raise NotImplementedError

    def check_objects_exist(
        self, collection_name: str, object_names: list[str]
    ) -> list[bool]:
        """
        Checks if objects exist in a collection.

        Parameters
        ----------
        collection_name : str
            The collection name.
        object_names : list[str]
            The object names.

        Returns
        -------
        list[bool]
            The list of booleans indicating if the objects exist.
        """
        raise NotImplementedError

    def get_objects(self, collection_name: str, object_names: list[str]) -> list[bytes]:
        """
        Gets objects from a collection.

        Parameters
        ----------
        collection_name : str
            The collection name.
        object_names : str
            The object names.

        Returns
        -------
        list
            The list of bytes objects.
        """
        raise NotImplementedError

    def put_objects(
        self, collection_name: str, object_names: list[str], object: list[bytes]
    ) -> None:
        """
        Puts objects into a collection.

        Parameters
        ----------
        collection_name : str
            The collection name.
        object_names : list[str]
            The object names.
        object : list[bytes]
            The byte objects.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def put_objects_with_duplicity_check(
        self, collection_name: str, object_names: list[str], object: list[bytes]
    ) -> list[str]:
        """
        Puts objects into a collection with duplicity check. Returns the list of
        object names, where the objects of which duplicates were found, substituted
        with the object names of the duplicates.

        Parameters
        ----------
        collection_name : str
            The collection name.
        object_names : list[str]
            The object names.
        object : list[bytes]
            The byte objects.

        Returns
        -------
        list[str]
            The list of object names.
        """
        raise NotImplementedError

    def delete_objects(self, collection_name: str, object_names: list[str]) -> None:
        """
        Deletes objects from a collection.

        Parameters
        ----------
        collection_name : str
            The collection name.
        object_names : list[str]
            The object names.

        Returns
        -------
        None
        """
        raise NotImplementedError
