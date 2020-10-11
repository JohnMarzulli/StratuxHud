from common_utils.logger import HudLogger


class LoggingObject(object):
    """
    Gives basic logging capabilities to the inheriting objects.
    Intended to be an abstract class.
    """

    def log(
        self,
        text: str
    ):
        """
        Logs the given text if a logger is available.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_info_message(text)
        else:
            print(text)

    def warn(
        self,
        text: str
    ):
        """
        Logs the given text if a logger is available AS A WARNING.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_warning_message(text)
        else:
            print(text)

    def __init__(
        self,
        logger: HudLogger
    ):
        if (logger is not None) and (not isinstance(logger, HudLogger)):
            raise("Recieved a non HudLogger as the logger.")

        self.__logger__ = logger
