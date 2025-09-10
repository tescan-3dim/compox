"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import threading
from datetime import datetime

from t3d_server.server_utils import generate_uuid
from t3d_server.session.DataCache import DataCache


class TaskSession:
    """
    The TaskSession class is used to serve as a common interface for individual
    TaskHandler instances. The session is identified by a session token. The purpose
    of session is to mainly handle in-memory data caches for algorithms.
    This is useful, as in some algorithms, it is necessary to be able to quickly access
    and modify some data without the need to repeatedly store and fetch the data
    from the database. The data is stored under in a dictionary-like structure, where
    the key is the session token and the value is the data cache object. The session token
    is an unique identifier generated for each session. If the client wishes to continue the
    session, the session token is passed in execution response, and when the client
    sends in other requests, they can pass the session in the session_token field.
    A new session is then created with the session token and with the access to the
    data stored in the cache under the particular session token.

    TODO: this currently only works for a single process. If we want to scale this
    to multiple processes, we need to use a shared memory object with access across
    the individual worker nodes.
    """

    # _instance = None
    _lock = threading.Lock()
    data_caches = {}

    def __init__(
        self,
        session_token: str = None,
        max_number_of_data_caches: int = 5,
        max_cache_size: int = 5,
        max_cache_memory_mb: int = None,
        expire_hours: int = 24,
        not_implemented: bool = False,
    ):
        """
        Initialize the TaskSession. The session is identified by a session token.
        If no session token is provided, a new one is generated.

        Parameters
        ----------
        session_token : str
            The identifier of the session. Typically a UUID.
        max_number_of_data_caches : int
            The maximum number of data caches which will be stored in memory.
        max_cache_size : int
            The maximum size of the cache.
        max_cache_memory_mb : int
            The maximum memory in MB that the cache can use.
        expire_hours : int
            The number of hours after which the session expires.
        not_implemented : bool
            Bool which marks the sessions as not supported. This is used currently
            used for marking the session as not supported for celery tasks.
        """

        if session_token:
            self._session_token = session_token
        else:
            self._session_token = generate_uuid()

        with self._lock:
            self._clean_expired_sessions(expire_hours)

            if len(self.data_caches) >= max_number_of_data_caches:
                oldest_session_key = min(
                    self.data_caches,
                    key=lambda k: self.data_caches[k]["time_created"],
                )
                del self.data_caches[oldest_session_key]

        self.max_cache_size = max_cache_size
        self.max_cache_memory_mb = max_cache_memory_mb
        self.not_implemented = not_implemented

    def _clean_expired_sessions(self, expire_hours: int) -> None:
        """
        Remove expired sessions from the cache.

        Parameters
        ----------
        expire_hours : int
            The number of hours after which the session expires.

        Returns
        -------
        None
        """
        current_time = datetime.now()
        expired_sessions = []
        for key, value in self.data_caches.items():
            if (
                current_time - value["time_created"]
            ).total_seconds() > expire_hours * 3600:
                expired_sessions.append(key)

        for key in expired_sessions:
            del self.data_caches[key]

    def __enter__(self):
        """
        The context manager enter method which returns the session.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        The context manager exit method which currently does nothing.
        """
        pass

    def __len__(self):
        """
        Returns the length of the cache.

        Returns
        -------
        int
            The length of the cache.
        """
        return len(self.data_caches)

    def __contains__(self, session_token: str) -> bool:
        """
        Checks if a cache exists for the current session.

        Parameters
        ----------
        session_token : str
            The session token to check.

        Returns
        -------
        bool
            True if the key is in the cache, False otherwise.
        """
        return session_token in self.data_caches.keys()

    def __getitem__(self, key: str) -> any:
        """
        Get the item from the cache.

        Parameters
        ----------
        key : str
            The key to get.

        Returns
        -------
        Any
            The item from the cache.
        """

        # TODO: remove this check when we have support for sessions in celery tasks
        if self.not_implemented:
            raise NotImplementedError(
                "The user attempted to run a task with a session token using a celery task. "
                "Session tokens are not currently allowed for celery tasks. If you "
                "need to run an alorithm requiring sessions, please set up the backend "
                "configuration to use FastAPI background tasks. You can do this by setting "
                "the 'inference.backend' configuration to 'fastapi_background_tasks' "
                "in the server configuration .yaml file."
            )

        try:
            return self.data_caches[self._session_token]["data_cache"][key]
        except KeyError:
            raise KeyError(
                f"Key {key} not found in cache for session {self._session_token}"
            )

    def add_item(self, obj: any, key: str) -> None:
        """
        Store the item in the cache.

        Parameters
        ----------
        obj : any
            The item to store.
        key : str
            The key to store the item with.

        Returns
        -------
        None
        """
        # TODO: remove this check when we have support for sessions in celery tasks
        if self.not_implemented:
            raise NotImplementedError(
                "The user attempted to run a task with a session token using a celery task. "
                "Session tokens are not currently allowed for celery tasks. If you "
                "need to run an alorithm requiring sessions, please set up the backend "
                "configuration to use FastAPI background tasks. You can do this by setting "
                "the 'inference.backend' configuration to 'fastapi_background_tasks' "
                "in the server configuration .yaml file."
            )
        with self._lock:
            if self._session_token not in self.data_caches.keys():
                self.data_caches[self._session_token] = {
                    "data_cache": DataCache(
                        max_size=self.max_cache_size,
                        max_memory_mb=self.max_cache_memory_mb,
                    ),
                    "time_created": datetime.now(),
                }
            self.data_caches[self._session_token]["data_cache"].add_item(
                obj, key
            )

    def remove_item(self, key: str):
        """
        Remove the item from the cache.

        Parameters
        ----------
        key : str
            The key to remove.
        """
        # TODO: remove this check when we have support for sessions in celery tasks
        if self.not_implemented:
            raise NotImplementedError(
                "The user attempted to run a task with a session token using a celery task. "
                "Session tokens are not currently allowed for celery tasks. If you "
                "need to run an alorithm requiring sessions, please set up the backend "
                "configuration to use FastAPI background tasks. You can do this by setting "
                "the 'inference.backend' configuration to 'fastapi_background_tasks' "
                "in the server configuration .yaml file."
            )
        with self._lock:
            self.data_caches[self._session_token]["data_cache"].remove_item(key)

    def clear_cache(self):
        """
        Clear the cache.
        """
        # TODO: remove this check when we have support for sessions in celery tasks
        if self.not_implemented:
            raise NotImplementedError(
                "The user attempted to run a task with a session token using a celery task. "
                "Session tokens are not currently allowed for celery tasks. If you "
                "need to run an alorithm requiring sessions, please set up the backend "
                "configuration to use FastAPI background tasks. You can do this by setting "
                "the 'inference.backend' configuration to 'fastapi_background_tasks' "
                "in the server configuration .yaml file."
            )
        with self._lock:
            self.data_caches[self._session_token]["data_cache"].clear()

    @property
    def session_token(self):
        """
        The identifier of the session. Typically a UUID.

        :getter: Returns the session id.
        :setter: Sets the session id.
        :type: str
        """

        if self.not_implemented:
            return None
        else:
            return self._session_token


if __name__ == "__main__":
    test_session = TaskSession("test_session")

    test_session.add_item("test", "test_key")
    print(test_session["test_key"])
