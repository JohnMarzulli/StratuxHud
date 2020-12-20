import datetime
import queue
import threading
import time


class RollingStats(object):
    """
    Class to keep a rolling means.
    """

    def __init__(
        self,
        name: str
    ):
        """
        Creates a new mean tracker.

        Arguments:
            name {string} -- The name of the task being tracked.
        """

        self.task_name = name
        self.__max_running_average__ = 120
        self.__running_average__ = queue.Queue(self.__max_running_average__)
        self.__running_sum__ = 0.0
        self.__running_average_count__ = 0
        self.last = None
        self.average = 0.0

    def reset(
        self
    ):
        """
        Resets the rolling mean and maximums.
        """

        self.average = 0.0
        self.__running_average__ = queue.Queue(self.__max_running_average__)
        self.__running_sum__ = 0.0
        self.__running_average_count__ = 0.0

    def push(
        self,
        value: float
    ):
        """
        Adds a new value to be tracked in the mean.

        Arguments:
            value {float} -- The new value to be averaged.
        """

        self.last = value
        self.__running_average__.put(self.last)
        self.__running_sum__ += self.last
        self.__running_average_count__ += 1

        if self.__running_average__.full():
            self.__running_sum__ -= self.__running_average__.get()
            self.__running_average_count__ -= 1

        self.average = float(self.__running_sum__ /
                             self.__running_average_count__)

    def to_string(
        self
    ) -> str:
        """
        Returns a string representation of the rolling mean data.

        Returns:
            string -- A string representing the data.
        """

        try:
            if self.last is None:
                return "{0}: NO DATA".format(self.task_name)

            slowest = max(
                self.__running_average__.queue) if not self.__running_average__.empty() else None

            if slowest is not None:
                slowest_text = "{0:.1f}".format(slowest)
            else:
                slowest_text = '---'

            slowest_length = len(slowest_text)

            last_text = "{0:.1f}".format(self.last).rjust(slowest_length)

            if self.average is not None:
                average_text = "{0:.1f}".format(
                    self.average).rjust(slowest_length)
            else:
                average_text = '---'

            return "{0}, {1}, {2}, {3}".format(
                self.task_name,
                last_text,
                average_text,
                slowest_text)
        except:
            return '---'


class TimerRegistry(object):
    __TIMERS__ = {}

    @staticmethod
    def add_task_timer(
        new_timer
    ):
        if new_timer is None:
            return

        TimerRegistry.__TIMERS__[new_timer.task_name] = new_timer

    @staticmethod
    def get_timers():
        return TimerRegistry.__TIMERS__.values()


class TaskTimer(object):
    """
    Class to track how long a task takes.
    """

    __TIMER_STACK__ = {}

    def __init__(
        self,
        task_name: str
    ):
        self.__stats__ = RollingStats(task_name)
        self.__start_time__ = None
        self.is_running = False
        self.task_name = task_name

        TimerRegistry.add_task_timer(self)

    def __push_timer_on_stack__(
        self
    ):
        """
        This is so we can eventually keep track of the call graph,
        and inclusive vs exclusive execution time.
        """
        tid = threading.get_ident()

        if tid not in TaskTimer.__TIMER_STACK__:
            TaskTimer.__TIMER_STACK__[tid] = []

        TaskTimer.__TIMER_STACK__[tid].append(self.task_name)

    def __pop_timer_from_stack__(
        self
    ):
        tid = threading.get_ident()

        if tid not in TaskTimer.__TIMER_STACK__:
            return

        TaskTimer.__TIMER_STACK__[tid].pop()

    def reset(
        self
    ):
        self.stop()
        self.__stats__.reset()

    def start(
        self
    ):
        self.stop()

        self.__start_time__ = datetime.datetime.utcnow()
        self.is_running = True

        self.__push_timer_on_stack__()

    def stop(
        self
    ):
        if not self.is_running:
            return

        self.is_running = False

        value = (datetime.datetime.utcnow() -
                 self.__start_time__).total_seconds() * 1000.0
        self.__stats__.push(value)

        self.__pop_timer_from_stack__()

    def to_string(
        self
    ) -> str:
        return self.__stats__.to_string()


if __name__ == '__main__':
    timer = TaskTimer("test")

    for i in range(1, 11, 1):
        timer.start()
        time.sleep(i / 10.0)
        timer.stop()
        print(timer.to_string())
