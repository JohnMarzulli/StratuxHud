import datetime
from logging import log
import queue
import threading


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


class TaskProfiler(object):
    # {string:TimeDelta}
    __TOTAL_TIMES__ = {}

    # {string:float}
    # Used to track how much time a task that was a child spent
    # So we know what time was ONLY the given task
    __CHILD_TIMES__ = {}

    # {string: int}
    __CALL_COUNTS__ = {}

    # NOTE: Do we need to keep track of the thread here?
    # [string]
    __CALLING_TIMERS__ = []

    @staticmethod
    def reset():
        for task_name in TaskProfiler.__TOTAL_TIMES__.keys():
            TaskProfiler.__CHILD_TIMES__[task_name] = 0.0
            TaskProfiler.__TOTAL_TIMES__[task_name] = 0.0
            TaskProfiler.__CALL_COUNTS__[task_name] = 0

        TaskProfiler.__CALLING_TIMERS__ = []

    @staticmethod
    def get_exclusive_times() -> dict:
        exclusive_times = {}

        for task_name in TaskProfiler.__TOTAL_TIMES__.keys():
            total_time = TaskProfiler.__TOTAL_TIMES__[task_name]
            child_time = TaskProfiler.__CHILD_TIMES__[task_name]
            exclusive_time = total_time - child_time

            exclusive_times[task_name] = exclusive_time

        return exclusive_times

    @staticmethod
    def log(
        logger
    ):
        if logger is None:
            return

        exclusive_times = TaskProfiler.get_exclusive_times()

        expense_order = sorted(
            exclusive_times,
            key=lambda profile: TaskProfiler.__TOTAL_TIMES__[profile],
            reverse=True)

        logger.log_info_message('------ PERF ------')
        logger.log_info_message(
            'Task, Calls, IncTotal, ExTotal, IncMean, ExMean')
        for task_name in expense_order:
            inclusive_ms = TaskProfiler.__TOTAL_TIMES__[task_name]
            exclusive_ms = exclusive_times[task_name]

            call_count = TaskProfiler.__CALL_COUNTS__[task_name]

            inclusive_mean = ''
            exclusive_mean = ''

            if call_count > 0:
                inclusive_mean = "{:.1f}".format(inclusive_ms / call_count)
                exclusive_mean = "{:.1f}".format(exclusive_ms / call_count)

            logger.log_info_message(
                '{0}, {1}, {2:.1f}, {3:.1f}, {4}, {5}'.format(
                    task_name,
                    call_count,
                    inclusive_ms,
                    exclusive_ms,
                    inclusive_mean,
                    exclusive_mean))

    def __init__(
        self,
        task_name: str
    ) -> None:
        super().__init__()

        if task_name not in TaskProfiler.__CHILD_TIMES__:
            TaskProfiler.__CHILD_TIMES__[task_name] = 0.0

        if task_name not in TaskProfiler.__TOTAL_TIMES__:
            TaskProfiler.__TOTAL_TIMES__[task_name] = 0.0

        if task_name not in TaskProfiler.__CALL_COUNTS__:
            TaskProfiler.__CALL_COUNTS__[task_name] = 0

        self.task_name = task_name
        self.__timer__ = datetime.datetime.utcnow()
        self.__is_running__ = False

    def start(
        self
    ):
        if self.__is_running__:
            return

        self.__timer__ = datetime.datetime.utcnow()
        self.__is_running__ = True
        TaskProfiler.__CALLING_TIMERS__.append(self.task_name)

    def stop(
        self
    ):
        if not self.__is_running__:
            return

        self.__is_running__ = False

        total_delta = datetime.datetime.utcnow() - self.__timer__
        total_ms = total_delta.total_seconds() * 1000.0

        TaskProfiler.__CALL_COUNTS__[self.task_name] += 1

        TaskProfiler.__TOTAL_TIMES__[self.task_name] += total_ms
        TaskProfiler.__CALLING_TIMERS__.pop()

        # Keep track of the parent's inclusive times
        if len(TaskProfiler.__CALLING_TIMERS__) < 1:
            return

        parent_task_name = TaskProfiler.__CALLING_TIMERS__[-1]
        TaskProfiler.__CHILD_TIMES__[parent_task_name] += total_ms

    def __enter__(
        self
    ):
        self.start()

    def __exit__(
        self,
        exc_type,
        exc_val,
        traceback
    ):
        self.stop()


if __name__ == '__main__':
    import time
    import logging
    from common_utils.logger import HudLogger

    python_logger = logging.getLogger("task_timer_test")
    python_logger.setLevel(logging.DEBUG)

    test_logger = HudLogger(python_logger)

    for i in range(1, 11, 1):
        with TaskProfiler("Root"):
            time.sleep(1.0)

            with TaskProfiler("Middle"):
                time.sleep(0.5)

                leaf_timer = TaskProfiler("Leaf")
                leaf_timer.start()
                time.sleep(0.5)
                leaf_timer.stop()

        test_logger.log_info_message("-_-_-_-")
        TaskProfiler.log(test_logger)
