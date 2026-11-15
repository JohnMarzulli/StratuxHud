import datetime
import threading
from threading import Lock
from time import monotonic
from typing import Callable


class RateLimitedTask:
    """
    Allow an action at most once per interval, without blocking callers.
    """

    def __init__(self, interval: datetime.timedelta):
        """
        Initializes the rate limiter with the given interval.

        Arguments:
            interval {datetime.timedelta} -- The minimum time between allowed actions.
        """
        self.__interval__: float = interval.total_seconds()
        self.__last_allowed__: float | None = None
        self.__lock__: Lock = threading.Lock()

    def run(self, callback: Callable[[], object]) -> bool:
        """Run the callback if its interval has elapsed; return whether it ran."""
        with self.__lock__:
            now = monotonic()

            if self.__last_allowed__ is not None and now - self.__last_allowed__ < self.__interval__:
                return False

            self.__last_allowed__ = now

        callback()
        return True
