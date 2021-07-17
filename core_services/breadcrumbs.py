"""
Handles determining how far out we care about traffic.
"""

import queue

import math
from datetime import datetime
from numbers import Number
from typing import List, Tuple

from common_utils import local_debug, units, geo_math
from common_utils.fast_math import interpolatef
from configuration import configuration
from data_sources.ahrs_data import AhrsData

BREADCRUMB_LIFESPAN_SECONDS = 2 * 60


class BreadcrumbReport:
    def __init__(
        self,
        position: list
    ) -> None:
        super().__init__()

        self.position = position
        self.timestamp = datetime.utcnow()


class Breadcrumbs:
    def __init__(
        self
    ) -> None:
        super().__init__()

        self.__breadcrumbs__ = queue.Queue()
        self.speed = 0.0

    def __report__(
        self,
        position: list
    ):
        if position is None or position[0] is None or position[1] is None:
            return

        self.__breadcrumbs__.put(BreadcrumbReport(position))

    def __has_contents__(
        self
    ) -> bool:
        return self.__breadcrumbs__ != None and self.__breadcrumbs__.qsize() > 0

    def __get_oldest_crumb_age__(
        self
    ) -> int:
        return 0 if not self.__has_contents__() else (datetime.utcnow() - self.__breadcrumbs__[0].__timestamp__).total_seconds()

    def __get_speed_estimate__(
        self
    ) -> float:
        """
        Generates a guess at our REAL groundspeed based on where we have been.
        The idea is to take into account work in the pattern and keep our
        traffic zoom distance appropriate.

        In the pattern or low level work, you may be circling something causing
        you really to have a zero ground speed BUT your instantaneous speed is 100MPH

        Returns:
            float: [description]
        """

        # Find an average (mean) GPS position
        # Then find the median timestamp.
        #
        # Use the MEAN position with the last position....
        # the MEDIAN timestamp with the last timestamp.
        # Finally find the distance and average everything out.

        sum_lat = 0.0
        sum_long = 0.0

        if self.__breadcrumbs__ is None or self.__breadcrumbs__.qsize() == 0:
            return 0.0

        for report in self.__breadcrumbs__:
            sum_lat += report.position[0]
            sum_long += report.position[1]

        length = self.__breadcrumbs__.qsize()

        avg_pos = [sum_lat / length, sum_long / length]
        middle_index = int(length / 2)
        mid_pos = self.__breadcrumbs__[middle_index].position
        mid_timestamp = self.__breadcrumbs__[middle_index].timestamp.total_seconds()
        last_report = self.__breadcrumbs__[self.__breadcrumbs__.qsize() - 1]

        disance = geo_math.get_distance(avg_pos, last_report.position)
        avg = disance / ((mid_timestamp - last_report.timestamp).total_seconds() / 2)

        return avg / 60

    def update(
        self,
        orientation: AhrsData
    ):
        self.__report__(orientation.position)

        while self.__get_oldest_crumb_age__() > BREADCRUMB_LIFESPAN_SECONDS:
            self.__breadcrumbs__.get()

        self.speed = self.__get_speed_estimate__()


INSTANCE = Breadcrumbs()
