"""
Simple wrapper around a logger.
"""

import datetime
import logging
from logging import Logger
from typing import Optional

from common_utils import text_tools
from common_utils.authoritative_time import DISPLAY_TIME, AuthoritativeTime

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class DisplayTimeFormatter(logging.Formatter):
    """
    Log formatter whose timestamps (%(asctime)s) come from the authoritative
    display time (GPS corrected) instead of the raw system clock.

    The record's own creation time is corrected, so the timestamp reflects
    when the message was logged, not when it was written out.

    Timestamps are always UTC and end in "Z".
    """

    def __init__(
        self,
        fmt: str = DEFAULT_LOG_FORMAT,
        datefmt: Optional[str] = None,
        clock: Optional[AuthoritativeTime] = None,
    ):
        super().__init__(fmt, datefmt)
        self.__clock__ = clock

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        # Resolve the clock at format time so tests can patch DISPLAY_TIME.
        clock = self.__clock__ or DISPLAY_TIME
        system_time = datetime.datetime.fromtimestamp(
            record.created, datetime.timezone.utc
        )
        display_time = clock.to_display_time(system_time)
        datefmt = datefmt or self.datefmt

        if datefmt:
            return display_time.strftime(datefmt)

        return display_time.strftime("%Y-%m-%d %H:%M:%S.") + (
            "%03dZ" % (display_time.microsecond // 1000)
        )


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
