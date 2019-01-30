"""
Package for simulating values for debugging and testing.
"""


import datetime
import math


class SimulatedValue(object):
    """
    Fluctuates a value.
    """

    def direction(self):
        """
        Gets the direction of movement.
        """
        if self.__direction__ > 0.0:
            return 1.0

        return -1.0

    def simulate(self):
        """
        Changes the value.
        """
        current_time = datetime.datetime.utcnow()
        self.__dt__ = (current_time - self.__last_sim__).total_seconds()
        self.__last_sim__ = current_time
        self.value += self.direction() * self.__rate__ * self.__dt__

        upper_limit = math.fabs(self.__limit__)
        lower_limit = 0 - upper_limit

        if self.direction() > 0.0 and self.value > upper_limit:
            self.__direction__ = -1.0
            self.value = upper_limit
        elif self.direction() < 0.0 and self.value < lower_limit:
            self.__direction__ = 1.0
            self.value = lower_limit

        return self.__offset__ + self.value

    def __init__(self, rate, limit, initial_direction, initial_value=0.0, offset=0.0):
        self.__rate__ = rate
        self.__limit__ = limit
        self.__direction__ = initial_direction
        self.__offset__ = offset
        self.value = initial_value
        self.__dt__ = 1.0 / 60.0
        self.__last_sim__ = datetime.datetime.utcnow()
