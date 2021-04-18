"""
Class and module to handle caching of any data.
"""

import threading
from datetime import datetime

from common_utils.task_timer import TaskProfiler


class GenericDataCache:
    """
    Singleton store for GENERIC data.

    Includes the ability to purge data based on time.
    """

    __CACHE_INVALIDATION_TIME__ = 60 * 5

    def __init__(
        self
    ) -> None:
        self.__data_last_used__ = {}
        self.__data_cache__ = {}
        self.__lock__ = threading.Lock()

    def __purge_data__(
        self,
        texture_to_purge
    ):
        """
        Attempts to remove a texture from the cache.

        Arguments:
            texture_to_purge {string} -- The identifier of the texture to remove from the system.
        """

        try:
            del self.__data_cache__[texture_to_purge]
            del self.__data_last_used__[texture_to_purge]
        finally:
            pass

    def __get_purge_key__(
        self,
        now: datetime,
        data_key: str
    ):
        """
        Returns the key of the traffic to purge if it should be, otherwise returns None.

        Arguments:
            now {datetime} -- The current time.
            data_key {string} -- The identifier of the texture we are interesting in.

        Returns:
            string -- The identifier to purge, or None
        """

        lsu = self.__data_last_used__[data_key]
        time_since_last_use = (now - lsu).total_seconds()

        return data_key if time_since_last_use > GenericDataCache.__CACHE_INVALIDATION_TIME__ else None

    def purge_old_data(
        self
    ):
        """
        Works through the traffic reports and removes any traffic that is
        old, or the cache has timed out on.
        """

        # The second hardest problem in comp-sci...
        with TaskProfiler("GenericDataCache::purge_old_data"):

            try:
                self.__lock__.acquire()
                now = datetime.utcnow()
                textures_to_purge = [self.__get_purge_key__(
                    now,
                    data_key) for data_key in self.__data_last_used__]
                textures_to_purge = list(filter(lambda x: x is not None,
                                                textures_to_purge))

                # pylint:disable=expression-not-assigned
                [self.__purge_data__(
                    texture_to_purge) for texture_to_purge in textures_to_purge]
            finally:
                self.__lock__.release()

    def set_data(
        self,
        data_key: str,
        value: any
    ):
        """
        Works through the traffic reports and removes any traffic that is
        old, or the cache has timed out on.
        """

        # The second hardest problem in comp-sci...
        with TaskProfiler("GenericDataCache::set_data"):
            try:
                self.__lock__.acquire()
                self.__data_cache__[data_key] = value

                self.__data_last_used__[data_key] = datetime.utcnow()
            finally:
                self.__lock__.release()

    def get_data(
        self,
        data_key: str
    ) -> any:
        with TaskProfiler("GenericDataCache::get_data"):
            try:
                self.__lock__.acquire()
                if data_key in self.__data_cache__:
                    self.__data_last_used__[data_key] = datetime.utcnow()

                    return self.__data_cache__[data_key]
            finally:
                self.__lock__.release()

            return None

    def get_or_create_data(
        self,
        data_key: str,
        data_creation_callback=None
    ) -> any:
        """
        Attempts to get the data (if available)

        Args:
            data_key (str): The key to the data.
            data_creation_callback: A callback to create the data if needed.

        Returns:
            any: The value found, None if not found.
        """

        with TaskProfiler("GenericDataCache::get_data"):
            try:
                self.__lock__.acquire()

                if data_key not in self.__data_cache__:
                    if data_creation_callback is None:
                        return None
                    self.__data_cache__[data_key] = data_creation_callback()

                self.__data_last_used__[data_key] = datetime.utcnow()
                return self.__data_cache__[data_key]
            finally:
                self.__lock__.release()
