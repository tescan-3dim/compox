"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json

from compox.database_connection import BaseConnection


class AlgorithmManager:
    """
    This class is responsible for managing the algorithms, modules and assets in
    the database. It provides methods to list or delete algorithms, modules and assets.
    To store the algorithms, modules and assets, use the AlgorithmDeployer class.

    Parameters
    ----------
    database_connection : BaseConnection.BaseConnection
        The database connection to use for the operations.

    algorithms_collection : str
        The name of the collection where the algorithms are stored.

    module_collection: str
        The name of the collection where the modules are stored.

    assets_collection : str
        The name of the collection where the assets are stored.
    """

    def __init__(
        self,
        database_connection: BaseConnection.BaseConnection,
        algorithms_collection: str = "algorithm-store",
        module_collection: str = "module-store",
        assets_collection: str = "asset-store",
    ):
        self.database_connection = database_connection
        self.algorithms_collection = algorithms_collection
        self.module_collection = module_collection
        self.assets_collection = assets_collection

    def list_algorithms(
        self, name: str | None = None, major_version: str | None = None, minor_version: str | None = None
    ) -> list[dict]:
        """
        List all algorithms stored in the database. Optionally can filter by name,
        major version or minor version.

        Parameters
        ----------
        name : str | None, optional
            Can be used to filter the algorithms by name.

        major_version : str | None, optional
            Can be used to filter the algorithms by major version.

        minor_version : str | None, optional
            Can be used to filter the algorithms by minor version.

        Returns
        -------
        list[dict]
            The list of algorithms defined by their jsons

        """
        algorithms = self.database_connection.list_objects(self.algorithms_collection)

        if len(algorithms) == 0:
            return []

        algorithms_jsons = []

        # get the jsons
        for algorithm in algorithms:
            algorithm_json = self.database_connection.get_objects(
                self.algorithms_collection, [algorithm["Key"]]
            )
            algorithms_jsons.append(dict(json.loads(algorithm_json[0])))

        # filter the algorithms
        if name:
            algorithms_jsons = [
                algorithm
                for algorithm in algorithms_jsons
                if name == algorithm["algorithm_name"]
            ]

        if major_version:
            algorithms_jsons = [
                algorithm
                for algorithm in algorithms_jsons
                if major_version == algorithm["algorithm_major_version"]
            ]

        if minor_version:
            algorithms_jsons = [
                algorithm
                for algorithm in algorithms_jsons
                if minor_version == algorithm["algorithm_minor_version"]
            ]

        return algorithms_jsons

    def delete_algorithms(
        self, name: str | None = None, major_version: str | None = None, minor_version: str | None = None
    ) -> None:
        """
        Delete an algorithm and associated modules and assets.

        Parameters
        ----------
        name : str | None
            The name of the algorithm to delete.

        major_version : str | None
            The major version of the algorithm to delete.

        minor_version : str | None
            The minor version of the algorithm to delete.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            if name, major_version or minor_version is not specified
        """

        if not name or not major_version or not minor_version:
            raise ValueError(
                "You must specify the name, major_version and minor_version of the algorithm to delete."
            )

        algorithms = self.list_algorithms(name, major_version, minor_version)

        for algorithm in algorithms:
            assets = algorithm.get("assets", [])
            module = algorithm.get("module_id", None)

            algorithm_id = algorithm["algorithm_id"]
            algorithm_name = algorithm["algorithm_name"]
            algorithm_major_version = algorithm["algorithm_major_version"]
            algorithm_minor_version = algorithm["algorithm_minor_version"]

            algorithm_key = f"{algorithm_id}~{algorithm_name}~{algorithm_major_version}~{algorithm_minor_version}"

            # delete the assets
            for key, value in assets.items():
                self.database_connection.delete_objects(self.assets_collection, [value])

            # delete the module

            if module:
                self.database_connection.delete_objects(
                    self.assets_collection, [module]
                )

            # delete the algorithm
            self.database_connection.delete_objects(
                self.algorithms_collection, [algorithm_key]
            )

        return None
