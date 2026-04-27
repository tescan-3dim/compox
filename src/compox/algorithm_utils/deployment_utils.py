"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from loguru import logger
from compox.algorithm_utils.AlgorithmDeployer import AlgorithmDeployer
from compox.algorithm_utils.AlgorithmManager import AlgorithmManager
from compox.database_connection import BaseConnection


def deploy_algorithm_from_folder(
    root_path: str,
    database_connection: BaseConnection.BaseConnection,
    delete_existing: bool = False,
) -> None:
    """
    Store algorithm into database.

    Parameters
    ----------
    root_path : str
        Algorithm
    database_connection : BaseConnection.BaseConnection
        The database connection object.
    delete_existing : bool, optional
        If True, delete existing algorithm with the same name and major version,
        by default False.

    Returns
    -------
    None
    """
    print("root_path")
    algorithm_deployer = AlgorithmDeployer(root_path)

    if delete_existing:
        algorithm_manager = AlgorithmManager(
            database_connection=database_connection
        )
        try:
            algorithm_manager.delete_algorithm(
                name=algorithm_deployer.algorithm_name,
                major_version=algorithm_deployer.algorithm_major_version,
            )
        except Exception as _:
            logger.error(
                f"Could not delete algorithm {algorithm_deployer.algorithm_name} "
                f"{algorithm_deployer.algorithm_major_version}."
            )

    algorithm_deployer.store_algorithm(database_connection=database_connection)


def remove_algorithm_from_folder(root_path, database_connection):
    """
    Helper function that looks at an algorithm folder and removes the algorithm
    from the database if it exists.
    """
    algorithm_deployer = AlgorithmDeployer(root_path)
    algorithm_manager = AlgorithmManager(
        database_connection=database_connection
    )

    try:
        algorithm_manager.delete_algorithm(
            name=algorithm_deployer.algorithm_name,
            major_version=algorithm_deployer.algorithm_major_version,
        )
        logger.info(
            f"Deleted algorithm {algorithm_deployer.algorithm_name} "
            f"{algorithm_deployer.algorithm_major_version}."
        )
    except Exception as _:
        logger.error(
            f"Could not delete algorithm {algorithm_deployer.algorithm_name} "
            f"{algorithm_deployer.algorithm_major_version}."
        )
