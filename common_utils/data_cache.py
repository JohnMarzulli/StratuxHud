import datetime
import threading

import requests


class DataCache(object):
    """
    Stores JSON data (in dictionary form) and handles invalidation based on
    the package age (last update).
    Does not handle aging out of specific data entries.
    """

    def __init__(
        self,
        cache_name: str,
        max_age_seconds: float
    ):
        """
        Creates a new cache for a dictionary.

        Arguments:
            cache_name {str} -- The name of the date/cache being held. Used to help in debugging.
            max_age_seconds {float} -- The number of seconds that the data is considered old and invalid if an update has not happened.
        """

        self.__max_age_seconds__ = max_age_seconds
        self.__lock_object__ = threading.Lock()
        self.__cache_name__ = cache_name
        self.__last_updated__ = None
        self.__json_package__ = {}

    def __get_data_age__(
        self
    ) -> float:
        """
        Returns the age of the data in seconds.
        INTENDED TO BE CALLED FROM INSIDE A LOCK.
        DOES NOT PERFORM ITS OWN LOCK.

        Returns:
            float -- The age of the data in seconds.
        """
        if self.__json_package__ is not None and self.__last_updated__ is not None:
            return (datetime.datetime.utcnow() - self.__last_updated__).total_seconds()

        return self.__max_age_seconds__ * 1000.0

    def garbage_collect(
        self
    ):
        """
        Go through the old data and make sure that it is removed if it is too old.
        This prevents a scenario where contact is lost with a service, and then
        an incomplete package keeps old data dangerously present.
        """
        self.__lock_object__.acquire()

        try:
            data_age = self.__get_data_age__()

            if (data_age > self.__max_age_seconds__) and (self.__json_package__ is not None) and len(self.__json_package__) > 0:
                self.__json_package__ = {}
        finally:
            self.__lock_object__.release()

    def update(
        self,
        new_package: dict
    ):
        """
        Performs a data update. Marks the timestamp of the data having been updated.
        Thread safe.

        Arguments:
            new_package {dict} -- The updated dictionary. It is merged into the existing data.
        """

        if new_package is None or len(new_package) < 1:
            return

        self.__lock_object__.acquire()

        try:
            self.__last_updated__ = datetime.datetime.utcnow()
            self.__json_package__.update(new_package)
        finally:
            self.__lock_object__.release()

    def is_available(
        self
    ) -> bool:
        try:
            self.__lock_object__.acquire()

            data_age = self.__get_data_age__()
            is_recent = data_age < self.__max_age_seconds__

            return is_recent
        except Exception as ex:
            print("is_available ex={}".format(ex))
        finally:
            self.__lock_object__.release()

        return False

    def get_item_count(
        self
    ) -> int:
        """
        Get how many items (key count) are in the package, regardless of age.

        Returns:
            int -- The number of keys in the package.
        """
        try:
            self.__lock_object__.acquire()

            return len(self.__json_package__)
        finally:
            self.__lock_object__.release()

        return 0

    def get(
        self
    ) -> dict:
        """
        Get the package if it has been updated recently enough.
        If the package has not been updated recently, then an empty
        dictionary is returned.

        Thread safe.

        Returns:
            dict -- The data if it is up-to-date, or an empty set.
        """
        self.__lock_object__.acquire()

        try:
            if self.__last_updated__ is None:
                return {}

            time_since = datetime.datetime.utcnow() - self.__last_updated__
            if time_since.total_seconds() < self.__max_age_seconds__:
                return self.__json_package__.copy()
        finally:
            self.__lock_object__.release()

        return {}


class RestfulDataCache(object):
    """
    Class to handle fetching data from a REST endpoint (GET only)
    and caching the results.

    Arguments:
        object {[type]} -- [description]
    """

    def __init__(
        self,
        cache_name: str,
        session: requests.Session,
        service_url: str,
        maximum_age_seconds: float,
        get_timeout: float = 1.0
    ):
        """
        Create the new cached REST fetcher

        Arguments:
            session {requests.Session} -- The session for calling the GET/endpoint
            cache_name {str} -- The name of the cache/data being held.
            service_url {str} -- The url to call GET for.
            maximum_age_seconds {float} -- The oldest the data can be in the cache.

        Keyword Arguments:
            get_timeout {float} -- The timeout for the GET call. (default: {1.0})
        """

        super().__init__()

        self.__data_cache__ = DataCache(cache_name, maximum_age_seconds)
        self.__service_url__ = service_url
        self.__session__ = session
        self.__timeout__ = get_timeout

    def update(
        self
    ) -> dict:
        """
        Attempt to call the GET and update the cached value.

        Returns:
            dict -- The value (if any, held in the cache.)
        """
        try:
            report = self.__session__.get(
                self.__service_url__,
                timeout=self.__timeout__).json()

            if report is not None:
                self.__data_cache__.update(report)
        finally:
            return self.get()

    def get(
        self
    ) -> dict:
        """
        Get the value currently in the cache.

        Returns:
            dict -- The current value, if any. None if the cache is empty or has been invalidated and purged.
        """
        return self.__data_cache__.get()

    def garbage_collect(
        self
    ):
        """
        Make sure the underlying data is garbage collected.
        """
        self.__data_cache__.garbage_collect()

    def get_item_count(
        self
    ) -> int:
        """
        Get how many items (key count) are in the package, regardless of age.

        Returns:
            int -- The number of keys in the package.
        """
        return self.__data_cache__.get_item_count()

    def is_available(
        self
    ) -> bool:
        """
        Is the data source available?

        Returns:
            bool -- True if the data source is available
        """
        return self.__data_cache__.is_available()
