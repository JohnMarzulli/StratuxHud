"""
Simple wrapper around a logger.
"""

from logging import Logger

from common_utils import text_tools


class HudLogger(object):
    """
    Wrapper around a normal logger so stuff gets printed too.
    """

    def get_logger(
        self
    ) -> Logger:
        return self.__logger__

    def log_info_message(
        self,
        message_to_log: str,
        print_to_screen: bool = True
    ):
        """ Log and print at Info level """
        if print_to_screen:
            print("LOG:" + text_tools.escape(message_to_log))
        self.__logger__.info(text_tools.escape(message_to_log))

        return message_to_log

    def log_warning_message(
        self,
        message_to_log: str
    ):
        """ Log and print at Warning level """
        print("WARN:" + message_to_log)
        self.__logger__.warning(text_tools.escape(message_to_log))

        return message_to_log

    def __init__(
        self,
        logger: Logger
    ):
        self.__logger__ = logger
