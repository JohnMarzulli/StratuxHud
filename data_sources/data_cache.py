import threading
from datetime import datetime

from common_utils.task_timer import TaskProfiler
from configuration import configuration
from rendering import colors

from data_sources import traffic


class HudDataCache(object):
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
            list -- A list of the reliable traffic.
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
            return True

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

    @staticmethod
    def purge_old_textures():
        """
        Works through the traffic reports and removes any traffic that is
        old, or the cache has timed out on.
        """

        # The second hardest problem in comp-sci...
        with TaskProfiler("HudDataCache::purge_old_textures"):

            HudDataCache.__LOCK__.acquire()
            try:
                now = datetime.utcnow()
                textures_to_purge = [HudDataCache.__get_purge_key__(
                    now,
                    texture_key) for texture_key in HudDataCache.__CACHE_ENTRY_LAST_USED__]
                textures_to_purge = list(filter(lambda x: x is not None,
                                                textures_to_purge))

                # pylint:disable=expression-not-assigned
                [HudDataCache.__purge_texture__(
                    texture_to_purge) for texture_to_purge in textures_to_purge]
            finally:
                HudDataCache.__LOCK__.release()

    @staticmethod
    def get_cached_text_texture(
        text: str,
        font,
        text_color: list = colors.BLACK,
        background_color: list = colors.YELLOW,
        use_alpha: bool = False,
        force_regen: bool = False
    ):
        """
        Retrieves a cached texture.
        If the texture with the given text does not already exists, creates it.
        Uses only the text has the key. If the colors change, the cache is not invalidated or changed.

        Arguments:
            text {string} -- The text to generate a texture for.
            font {pygame.font} -- The font to use for the texture.

        Keyword Arguments:
            text_color {tuple} -- The RGB color for the text. (default: {BLACK})
            background_color {tuple} -- The RGB color for the BACKGROUND. (default: {YELLOW})
            use_alpha {bool} -- Should alpha be used? (default: {False})

        Returns:
            [tuple] -- The texture and the size of the texture
        """

        with TaskProfiler("HudDataCache::get_cached_text_texture"):
            result = None
            text_key = "{0}:{1}:{2}:{3}:{4}".format(
                font,
                text,
                text_color,
                background_color,
                use_alpha)
            HudDataCache.__LOCK__.acquire()
            try:
                if text_key not in HudDataCache.TEXT_TEXTURE_CACHE or force_regen:
                    texture = font.render(
                        text,
                        True,
                        text_color,
                        background_color)
                    size = texture.get_size()

                    if use_alpha:
                        texture = texture.convert_alpha()

                    HudDataCache.TEXT_TEXTURE_CACHE[text_key] = texture, size

                HudDataCache.__CACHE_ENTRY_LAST_USED__[
                    text_key] = datetime.utcnow()
                result = HudDataCache.TEXT_TEXTURE_CACHE[text_key]
            finally:
                HudDataCache.__LOCK__.release()

        return result
