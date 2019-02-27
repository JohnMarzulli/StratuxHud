"""
Module to handle tasks that occur on a regularly scheduled interval.
"""

import sys
import threading
import time

FUNCTION_A_COUNT = 0
FUNCTION_B_COUNT = 0


class RecurringTask(object):
    """
    Object to control and handle a recurring task.
    """

    __SPAWNED_TASKS__ = []

    @staticmethod
    def kill_all():
        timeout_sec = 5
        for task in RecurringTask.__SPAWNED_TASKS__:  # list of your processes
            print('Killing task {}'.format(task.__task_name__))

            try:
                task.stop()
            except Exception as ex:
                print('While shutting down EX:{}'.format(ex))

    def stop(self):
        self.__is_alive__ = False
        self.__is_running__ = False

    def is_running(self):
        """
        Returns True if the task is running.
        """

        self.__lock__.acquire()
        result = self.__is_alive__ \
            and self.__task_callback__ is not None \
            and self.__is_running__
        self.__lock__.release()

        return result

    def start(self):
        """
        Starts the task if it is not already running.
        """
        if self.__task_callback__ is not None and not self.__is_running__:
            self.__is_running__ = True
            self.__run_task__()

            return True

        return False

    def pause(self):
        """
        Pauses the task if it is running.
        """

        self.__lock__.acquire()
        self.__is_running__ = False
        self.__lock__.release()

    def __run_task__(self):
        """
        Runs the callback.
        """

        self.__last_task__ = threading.Thread(target=self.__run_loop__, name=self.__task_name__)
        self.__last_task__.start()

        RecurringTask.__SPAWNED_TASKS__.append(self)

    def __run_loop__(self):
        while self.__is_alive__:
            if self.__is_running__ and self.__task_callback__ is not None:
                try:
                    self.__lock__.acquire()
                    self.__task_callback__()
                except Exception as e:
                    # + sys.exc_info()[0]
                    error_mesage = "EX({}):{}".format(self.__task_name__, e)

                    if self.__logger__ is not None:
                        self.__logger__.info(error_mesage)
                    else:
                        print(error_mesage)
                finally:
                    self.__lock__.release()

            self.__lock__.acquire()
            try:
                time.sleep(int(self.__task_interval__) if self.__is_alive__ and self.__is_running__ else 0)
            finally:
                self.__lock__.release()

    def __init__(self, task_name, task_interval, task_callback, logger=None, start_immediate=False):
        """
        Creates a new reccurring task.
        The call back is called at the given time schedule.
        """

        self.__task_name__ = task_name
        self.__task_interval__ = task_interval
        self.__task_callback__ = task_callback
        self.__logger__ = logger
        self.__is_alive__ = True
        self.__is_running__ = False
        self.__last_task__ = None
        self.__lock__ = threading.Lock()

        if start_immediate:
            self.start()
        else:
            threading.Timer(int(self.__task_interval__), self.start).start()


class TimerTest(object):
    def __init__(self):
        self.a = 0
        self.b = 0

        RecurringTask("A", 1, self.increment_a)
        RecurringTask("B", 2, self.increment_b)

    def increment_a(self):
        self.a += 1

    def increment_b(self):
        self.b += 1

        if (self.b % 10) == 0:
            raise KeyboardInterrupt


if __name__ == '__main__':

    TEST = TimerTest()

    while True:
        print("A:" + str(TEST.a))
        print("B:" + str(TEST.b))

        time.sleep(1)
