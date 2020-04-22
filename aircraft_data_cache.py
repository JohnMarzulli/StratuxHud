import datetime
import threading


class AircraftDataCache(object):
    """
    Stores JSON data (in dictionary form) and handles invalidation based on
    the package age (last update).
    Does not handle aging out of specific data entries.
    """

    def __init__(
        self,
        max_age_seconds
    ):
        """
        Creates a new cache for a dictionary.

        Arguments:
            max_age_seconds {float} -- The number of seconds that the data is considered old and invalid if an update has not happened.
        """

        self.__max_age_seconds__ = max_age_seconds
        self.__lock_object__ = threading.Lock()
        self.__last_updated__ = None
        self.__json_package__ = {}

    def __get_data_age__(
        self
    ):
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

            if data_age > self.__max_age_seconds__:
                self.__json_package__ = {}
        finally:
            self.__lock_object__.release()

    def update(
        self,
        new_package
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
    ):
        try:
            self.__lock_object__.acquire()

            data_age = self.__get_data_age__()
            return data_age < self.__max_age_seconds__
        finally:
            self.__lock_object__.release()

    def get_item_count(
        self
    ):
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

    def get(
        self
    ):
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
