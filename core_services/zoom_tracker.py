"""
Handles determining how far out we care about traffic.
"""

from core_services import breadcrumbs
import math
from datetime import datetime
from numbers import Number
from typing import Tuple

from common_utils import local_debug, tasks, units
from common_utils.fast_math import interpolatef
from configuration import configuration
from data_sources.ahrs_data import AhrsData

DEFAULT_SCOPE_RANGE = (10, 5)

SCOPE_RANGES = [
    (1, 0),
    (2, 1),
    (5, 3),
    (10, 5),
    (15, 5),
    (20, 10),
    (50, 25)]

# A value of "12" is how far you will fly in
# ten minutes. Making it 12 x 2 will range
# the scope based on how far you will
# fly in 5 minutes.
__DISTANCE_PREDICTION_SCALER__ = 12 * 2


def __get_maximum_scope_range__() -> Tuple[int, int]:
    """
    Get the maximum

    Returns:
        (int, int): Tuple of the maximum distance for the scope, and the distance between each ring.
    """
    return SCOPE_RANGES[-1]


def get_ideal_scope_range(
    groundspeed: float
) -> Tuple[int, int]:
    """
    Given a ground speed, figure out how far the scope should be.
    This is done by figuring out how far you will be in 10 minutes

    Args:
        groundspeed (float): The speed to calculate the ideal scope range from. This is in final units (so MPH, KPH, KNOTS)

    Returns:
        (int, int): The maximum distance the scope will cover and the distance between each ring.

    >>> __get_ideal_scope_range__(0.0)
    (1, 0)
    >>> __get_ideal_scope_range__(0)
    (1, 0)
    >>> __get_ideal_scope_range__(-1 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(-1.0 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(0.5 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(1 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(1.0 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> __get_ideal_scope_range__(1.1 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(1.5 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(1.9 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(2.0 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> __get_ideal_scope_range__(2.1 * __DISTANCE_PREDICTION_SCALER__)
    (5, 3)
    >>> __get_ideal_scope_range__(5 * __DISTANCE_PREDICTION_SCALER__)
    (5, 3)
    >>> __get_ideal_scope_range__(9.9 * __DISTANCE_PREDICTION_SCALER__)
    (10, 5)
    >>> __get_ideal_scope_range__(10 * __DISTANCE_PREDICTION_SCALER__)
    (10, 5)
    >>> __get_ideal_scope_range__(14.9 * __DISTANCE_PREDICTION_SCALER__)
    (15, 5)
    >>> __get_ideal_scope_range__(15 * __DISTANCE_PREDICTION_SCALER__)
    (15, 5)
    >>> __get_ideal_scope_range__(19.9 * __DISTANCE_PREDICTION_SCALER__)
    (20, 10)
    >>> __get_ideal_scope_range__(20 * __DISTANCE_PREDICTION_SCALER__)
    (20, 10)
    >>> __get_ideal_scope_range__(20.1 * __DISTANCE_PREDICTION_SCALER__)
    (50, 25)
    >>> __get_ideal_scope_range__(50 * __DISTANCE_PREDICTION_SCALER__)
    (50, 25)
    >>> __get_ideal_scope_range__(100 * __DISTANCE_PREDICTION_SCALER__)
    (50, 25)
    """

    predicted_travel_distance = math.fabs(groundspeed) / __DISTANCE_PREDICTION_SCALER__

    # The idea is to return the first range in the set
    # that is further than you will fly in 10 minutes.
    for possible_range in SCOPE_RANGES:
        range_distance = possible_range[0]
        if range_distance >= predicted_travel_distance:
            return possible_range

    return __get_maximum_scope_range__()


def get_groundspeed(
    display_units: str,
    orientation: AhrsData
) -> float:
    is_valid_groundspeed = orientation.groundspeed is not None and isinstance(orientation.groundspeed, Number)
    is_valid_airspeed = orientation.airspeed is not None and isinstance(orientation.airspeed, Number)

    airspeed = units.get_converted_units(
        display_units,
        orientation.airspeed * units.feet_to_nm) if is_valid_airspeed else 0.0

    groundspeed = units.get_converted_units(
        units,
        orientation.groundspeed * units.yards_to_nm) if is_valid_groundspeed else 0

    if (local_debug.is_debug() or not is_valid_groundspeed) and is_valid_airspeed:
        return airspeed

    return groundspeed


class ZoomTracker:
    """
    Tracks what our current zoom is and should be.
    Handles gracefully transitioning the desired
    zoom distance, while providing flapping prevention.
    """

    SECONDS_FOR_ZOOM = 3
    MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE = SECONDS_FOR_ZOOM * 5

    def __init__(
        self,
        starting_zoom: Tuple[int, int]
    ) -> None:
        super().__init__()

        self.__last_changed__ = datetime.utcnow()
        self.__last_zoom__ = starting_zoom
        self.__target_zoom__ = starting_zoom
        self.__user_units__ = configuration.CONFIGURATION.get_units()
        self.__update_units_task__ = tasks.IntermittentTask(
            "Zoom:UpdateUnits",
            1.0,
            self.__update_units__)

    def __update_units__(
        self
    ) -> None:
        self.__user_units__ = configuration.CONFIGURATION.get_units()

    def set_target_zoom(
        self,
        new_target_zoom: Tuple[int, int]
    ):
        """
        Sets the desired target zoom distance.

        If a zoom target has been set too recently
        then the request is ignored. (Anti-flapping)

        Args:
            new_target_zoom (Tuple[int, int]): The total distance of the zoom and distance between rings.
        """

        if new_target_zoom is None:
            return

        if new_target_zoom[0] == self.__target_zoom__[0]:
            return

        delta_since_last_change = (datetime.utcnow() - self.__last_changed__).total_seconds()

        if delta_since_last_change < ZoomTracker.MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE:
            return

        print("Old target zoom={}".format(self.__target_zoom__))
        print("Setting new target zoom={}".format(new_target_zoom))

        self.__last_zoom__ = self.__target_zoom__
        self.__last_changed__ = datetime.utcnow()
        self.__target_zoom__ = new_target_zoom

    def get_target_threshold_distance(
        self
    ) -> int:
        """
        Get the distance of the first inner-ring...
        or the distance that we determine really means
        immediately close targets
        """
        return self.__target_zoom__[0]

    def get_target_zoom(
        self
    ) -> Tuple[Number, int]:
        """
        Get what our ideal, current zoom is.

        Returns a tuple that is the ideal distance
        AND the distance between rings.

        Returns:
            [Number, int]: The range and step of the scope rings
        """
        delta_since_last_change = (datetime.utcnow() - self.__last_changed__).total_seconds()

        proportion_into_zoom = delta_since_last_change / ZoomTracker.SECONDS_FOR_ZOOM

        if proportion_into_zoom >= 1.0:
            return self.__target_zoom__

        computed_range = interpolatef(
            self.__last_zoom__[0],
            self.__target_zoom__[0],
            proportion_into_zoom)

        # Determine the stepping to use based on
        # stepping of the rings. We want to always
        # use the largest stepping.
        #
        # We choose this way so the whole process has visual consistency
        # and does not startle the aviator.
        previous_zoom_stepping = self.__last_zoom__[1]
        new_zoom_stepping = self.__target_zoom__[1]

        target_zoom_step = max(new_zoom_stepping, previous_zoom_stepping)

        return [computed_range, target_zoom_step]

    def is_in_inner_range(
        self,
        raw_distance: float
    ) -> Tuple[bool, float]:
        """
        Is the current distance within the threshold of displaying
        more data about?

        Args:
            raw_distance (float): The distance to the target (raw) from the ADS-B reciever

        Returns:
            bool: TRUE is the target is within the inner scope range.
        """

        display_distance = units.get_converted_units(
            self.__user_units__,
            raw_distance)

        scope_range = self.get_target_threshold_distance()

        return (display_distance <= scope_range, display_distance)

    def update(
        self,
        orientation: AhrsData
    ) -> Tuple[Number, float]:
        self.__update_units_task__.run()

        groundspeed = 0.0 if orientation is None else get_groundspeed(self.__user_units__, orientation)

        if breadcrumbs.INSTANCE is not None and not isinstance(breadcrumbs.INSTANCE.speed, str):
            groundspeed = units.get_converted_units(
                self.__user_units__,
                breadcrumbs.INSTANCE.speed)

        ideal_range = get_ideal_scope_range(groundspeed)

        self.set_target_zoom(ideal_range)

        return self.get_target_zoom()


INSTANCE = ZoomTracker(DEFAULT_SCOPE_RANGE)
