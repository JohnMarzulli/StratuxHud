"""
Simple wrapper around a logger.
"""

import utilities


class Logger(object):
    """
    Wrapper around a normal logger so stuff gets printed too.
    """

    def log_info_message(self, message_to_log, print_to_screen=True):
        """ Log and print at Info level """
        if print_to_screen:
            print("LOG:" + utilities.escape(message_to_log))
        self.__logger__.info(utilities.escape(message_to_log))

        return message_to_log

    def log_warning_message(self, message_to_log):
        """ Log and print at Warning level """
        print("WARN:" + message_to_log)
        self.__logger__.warning(utilities.escape(message_to_log))

        return message_to_log

    def __init__(self, logger):
        self.__logger__ = logger
