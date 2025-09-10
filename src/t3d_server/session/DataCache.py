"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from typing import Any
import sys


class DataCache:
    """
    This class serves as a data cache for the task handler. It is used to store
    data in memory for quick access and modification. The cache is identified by
    a key which is used to store and retrieve the data. The cache has a maximum
    size and memory limit. If the cache exceeds the maximum size, the oldest item
    is removed. If the cache exceeds the maximum memory limit, the cache is cleared.

    """

    def __init__(self, max_size: int = 5, max_memory_mb: int = None):
        """
        Initialize the DataCache.

        Parameters
        ----------
        max_size : int
            The maximum size of the cache.

        max_memory_mb : int
            The maximum memory in MB that the cache can use.
        """
        self.cache = {}
        self.cache_keys = []
        self.removed_keys_len = []
        self.removed_keys_memory = []
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb

    def __len__(self):
        """
        Returns the length of the cache.

        Returns
        -------
        int
            The length of the cache.
        """
        return len(self.cache)

    def __contains__(self, key: str):
        """
        Checks if the key is in the cache.

        Parameters
        ----------
        key : str
            The key to check.

        Returns
        -------
        bool
            True if the key is in the cache, False otherwise.
        """
        return key in self.cache

    def __getitem__(self, key: str):
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
        if key in self.cache:
            # this moves the key to the end of the list as the most recently used
            self.cache_keys.remove(key)
            self.cache_keys.append(key)
            return self.cache[key]
        elif key in self.removed_keys_len:
            raise KeyError(
                f"Key {key} was removed from the cache due to exceeding the maximum cache size. Consider increasing the cache size."
            )
        elif key in self.removed_keys_memory:
            raise KeyError(
                f"Key {key} was removed from the cache due to exceeding the maximum memory limit. Consider increasing the memory limit."
            )
        else:
            raise KeyError(f"Key {key} not found in cache.")

    def _get_memory_usage(self):
        """
        Get the memory usage of the cache.

        Returns
        -------
        int
            The memory usage in MB.
        """
        return (
            sum(sys.getsizeof(value) for value in self.cache.values()) / 1024**2
        )

    def add_item(self, obj: Any, key: str):
        """
        Add an item to the cache.

        Parameters
        ----------
        obj : Any
            The item to add to the cache.
        key : str
            The key of the item.
        """
        if len(self.cache) >= self.max_size:
            # if the cache is full, remove the oldest item from the cache
            key_to_remove = self.cache_keys.pop(0)
            self.remove_item(key_to_remove)
            # keep track of the removed keys
            self.removed_keys_len.append(key_to_remove)

        # if memory limit is set, check if we need to remove items from the cache
        # to stay under the memory limit
        # if the memory limit is exceeded, remove the oldest item from the cache
        # and check again
        # the most recently added item is always kept in the cache even if it exceeds the memory limit

        if self.max_memory_mb is not None:
            while (self._get_memory_usage() >= self.max_memory_mb) and len(
                self.cache
            ) > 1:
                # if the cache exceeds the memory limit, remove the oldest item from the cache
                key_to_remove = self.cache_keys.pop(0)
                self.remove_item(key_to_remove)
                # keep track of the removed keys
                self.removed_keys_memory.append(key_to_remove)

        self.cache[key] = obj
        self.cache_keys.append(key)

    def remove_item(self, key: str):
        """
        Remove an item from the cache.

        Parameters
        ----------
        key : str
            The key of the item to remove.
        """
        if key in self.cache:
            del self.cache[key]
            if key in self.cache_keys:
                self.cache_keys.remove(key)

    def clear(self):
        """
        Clear the cache.
        """
        self.cache = {}
        self.cache_keys = []
