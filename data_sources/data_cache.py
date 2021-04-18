"""
Class and module to handle caching, and invalidation, of textures
and other data.
"""

import threading
from datetime import datetime

from common_utils.local_debug import IS_PI
from common_utils.task_timer import TaskProfiler
from configuration import configuration

from data_sources import traffic

__ANTI_ALIAS_TEXT__ = not IS_PI


class HudDataCache(object):
    """
    handle caching, and invalidation, of textures and other data.
    """

    TEXT_TEXTURE_CACHE = {}
    __CACHE_ENTRY_LAST_USED__ = {}
    __CACHE_INVALIDATION_TIME__ = 60 * 5

    RELIABLE_TRAFFIC = []
    IS_TRAFFIC_AVAILABLE = False

    __LOCK__ = threading.Lock()

    __TRAFFIC_CLIENT__ = traffic.AdsbTrafficClient(
        configuration.CONFIGURATION.get_traffic_manager_address())

    @staticmethod
    def update_traffic_reports():
        """
        Updates the intermediary traffic store with the currently known reliable data.
        """
        with TaskProfiler("HudDataCache::update_traffic_reports"):
            HudDataCache.__LOCK__.acquire()

            try:
                HudDataCache.RELIABLE_TRAFFIC = traffic.AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()
                HudDataCache.IS_TRAFFIC_AVAILABLE = traffic.AdsbTrafficClient.TRAFFIC_MANAGER.is_traffic_available()
            finally:
                HudDataCache.__LOCK__.release()

    @staticmethod
    def get_reliable_traffic() -> list:
        """
        Returns a thread safe copy of the currently known reliable traffic.

        Returns:
            list: A list of the reliable traffic stored in Traffic objects.
        """

        with TaskProfiler("HudDataCache::get_reliable_traffic"):
            traffic_clone = None
            HudDataCache.__LOCK__.acquire()
            try:
                traffic_clone = HudDataCache.RELIABLE_TRAFFIC[:]
            finally:
                HudDataCache.__LOCK__.release()

        return traffic_clone

    @staticmethod
    def __purge_texture__(
        texture_to_purge
    ):
        """
        Attempts to remove a texture from the cache.

        Arguments:
            texture_to_purge {string} -- The identifier of the texture to remove from the system.
        """

        try:
            del HudDataCache.TEXT_TEXTURE_CACHE[texture_to_purge]
            del HudDataCache.__CACHE_ENTRY_LAST_USED__[texture_to_purge]
        finally:
            pass

    @staticmethod
    def __get_purge_key__(
        now: datetime,
        texture_key: str
    ):
        """
        Returns the key of the traffic to purge if it should be, otherwise returns None.

        Arguments:
            now {datetime} -- The current time.
            texture_key {string} -- The identifier of the texture we are interesting in.

        Returns:
            string -- The identifier to purge, or None
        """

        lsu = HudDataCache.__CACHE_ENTRY_LAST_USED__[texture_key]
        time_since_last_use = (now - lsu).total_seconds()

        return texture_key if time_since_last_use > HudDataCache.__CACHE_INVALIDATION_TIME__ else None
