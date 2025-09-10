"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from t3d_server.config.server_settings import Settings
from t3d_server.database_connection.S3Connection import S3Connection


_DATABASE_BACKEND_TYPE = "s3"


def build_database_connection(settings: Settings):
    """
    Build a database connection based on the settings provided.

    Parameters
    ----------
    settings : Settings
        The settings object containing the database configuration.

    Returns
    -------
    S3Connection
        The database connection instance.
    """

    if _DATABASE_BACKEND_TYPE == "s3":
        
        database_connection = S3Connection(
            settings.storage.backend_settings.s3_endpoint_url,
            settings.storage.access_key_id,
            settings.storage.secret_access_key,
            settings.storage.backend_settings.aws_region,
            data_store_expire_days=settings.storage.data_store_expire_days,
            collection_prefix=settings.storage.collection_prefix,
        )
        return database_connection
    else:
        raise ValueError("Database backend not supported")
