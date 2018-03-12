import datetime
import time
import Queue


class TaskTimer(object):
    def __init__(self, task_name):
        self.__max_running_average__ = 120
        self.__running_average__ = Queue.Queue(self.__max_running_average__)
        self.__running_sum__ = 0.0
        self.__running_average_count__ = 0
        self.__start_time__ = None
        self.slowest = None
        self.last = None
        self.fastest = None
        self.average = 0.0
        self.is_running = False
        self.task_name = task_name
    
    def reset(self):
        self.stop()
        self.fastest = None
        self.slowest = None
        self.average = 0.0
        self.__running_average__ = Queue.Queue(self.__max_running_average__)
        self.__running_sum__ = 0.0
        self.__running_average_count__ = 0.0


    def start(self):
        self.stop()

        self.__start_time__ = datetime.datetime.now()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            return
        
        self.is_running = False

        self.last = (datetime.datetime.now() -
                     self.__start_time__).total_seconds() * 1000.0
        self.__running_average__.put(self.last)
        self.__running_sum__ += self.last
        self.__running_average_count__ += 1

        if self.__running_average__.full():
            self.__running_sum__ -= self.__running_average__.get()
            self.__running_average_count__ -= 1

        self.average = float(self.__running_sum__ /
                             self.__running_average_count__)

        if self.slowest is None or self.slowest < self.last:
            self.slowest = self.last

        if self.fastest is None or self.fastest > self.last:
            self.fastest = self.last

    def to_string(self):
        return "{0}: {1:3.1f}, m={2:3.1f}, s={3:3.1f}".format(self.task_name,
                                                                self.last,
                                                                self.average,
                                                                self.slowest)

if __name__ == '__main__':
    timer = TaskTimer("test")

    for i in range(1, 11, 1):
        timer.start()
        time.sleep(i / 10.0)
        timer.stop()
        print timer.to_string()
