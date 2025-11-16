"""
Handles determining how far out we care about traffic.
"""

from core_services import breadcrumbs
from datetime import datetime
from numbers import Number
from typing import Tuple

from common_utils import local_debug, tasks, units
from configuration import configuration
from core_services.zoom_interpolation import SECONDS_FOR_ZOOM, get_actual_zoom
from core_services.scope_range import ScopeRange
from core_services.zoom_manager import ZoomManager, get_ideal_scope_range
from data_sources.ahrs_data import AhrsData
from datetime import timezone

MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE = SECONDS_FOR_ZOOM * 1.1


def get_groundspeed(display_units: str, orientation: AhrsData) -> float:
    is_valid_groundspeed = orientation.groundspeed is not None and isinstance(
        orientation.groundspeed, Number
    )
    is_valid_airspeed = orientation.airspeed is not None and isinstance(
        orientation.airspeed, Number
    )

    airspeed = (
        units.get_converted_units(
            display_units, orientation.airspeed * units.feet_to_nm
        )
        if is_valid_airspeed
        else 0.0
    )

    groundspeed = (
        units.get_converted_units(units, orientation.groundspeed * units.yards_to_nm)
        if is_valid_groundspeed
        else 0
    )

    if (local_debug.is_debug() or not is_valid_groundspeed) and is_valid_airspeed:
        return airspeed

    return groundspeed


class ZoomTracker:
    """
    Tracks what our current zoom is and should be.
    Handles gracefully transitioning the desired
    zoom distance, while providing flapping prevention.
    """

    def __init__(self) -> None:
        super().__init__()

        self.__zoom_manager__ = ZoomManager()

        self.__last_changed__ = datetime.now(timezone.utc)
        self.__last_zoom__: ScopeRange = self.__zoom_manager__.get_current_zoom()
        self.__user_units__ = configuration.CONFIGURATION.get_units()
        self.__update_units_task__ = tasks.IntermittentTask(
            "Zoom:UpdateUnits", 1.0, self.__update_units__
        )

    def manual_zoom_in(self):
        self.__zoom_manager__.manual_zoom_in()
        self.__last_changed__ = datetime.now(timezone.utc)
        self.__last_zoom__ = self.__get_target_zoom__()

    def manual_zoom_out(self):
        self.__zoom_manager__.manual_zoom_out()
        self.__last_changed__ = datetime.now(timezone.utc)
        self.__last_zoom__ = self.__get_target_zoom__()

    def return_to_automatic(self):
        self.__zoom_manager__.return_to_automatic()
        self.__last_zoom__ = self.__get_target_zoom__()

    def get_target_zoom(self) -> ScopeRange:
        """
        Get what our ideal, current zoom is.

        Returns a tuple that is the ideal distance
        AND the distance between rings.

        Returns:
            [Number, int]: The range and step of the scope rings
        """
        seconds_into_zoom = (
            datetime.now(timezone.utc) - self.__last_changed__
        ).total_seconds()

        return get_actual_zoom(
            seconds_into_zoom, self.__last_zoom__, self.__get_target_zoom__()
        )

    def is_in_range(self, raw_distance: float) -> Tuple[bool, float]:
        """
        Is the current distance within the threshold of displaying
        more data about?

        Args:
            raw_distance (float): The distance to the target (raw) from the ADS-B reciever

        Returns:
            bool: TRUE is the target is within the inner scope range.
        """

        display_distance = units.get_converted_units(self.__user_units__, raw_distance)

        scope_range = self.__get_target_zoom__().max_ring_range

        return (display_distance <= scope_range, display_distance)

    def is_in_inner_range(self, raw_distance: float) -> Tuple[bool, float]:
        """
        Is the current distance within the threshold of displaying
        more data about?

        Args:
            raw_distance (float): The distance to the target (raw) from the ADS-B reciever

        Returns:
            bool: TRUE is the target is within the inner scope range.
        """

        display_distance = units.get_converted_units(self.__user_units__, raw_distance)

        scope_range = self.__get_target_zoom__().center_ring_range

        return (display_distance <= scope_range, display_distance)

    def update(self, orientation: AhrsData) -> ScopeRange:
        self.__update_units_task__.run()

        if not self.__zoom_manager__.is_automatic():
            return self.get_target_zoom()

        groundspeed = (
            0.0
            if orientation is None
            else get_groundspeed(self.__user_units__, orientation)
        )

        if breadcrumbs.INSTANCE is not None and not isinstance(
            breadcrumbs.INSTANCE.speed, str
        ):
            breadcrumb_speed = units.get_converted_units(
                self.__user_units__, breadcrumbs.INSTANCE.speed
            )

            groundspeed += breadcrumb_speed
            groundspeed /= 2

        ideal_range = get_ideal_scope_range(groundspeed)

        self.__set_target_zoom__(ideal_range)

        return self.get_target_zoom()

    def __set_target_zoom__(self, new_target_zoom: ScopeRange):
        """
        Sets the desired target zoom distance.

        If a zoom target has been set too recently
        then the request is ignored. (Anti-flapping)

        Args:
            new_target_zoom (Tuple[int, int]): The total distance of the zoom and distance between rings.
        """

        if new_target_zoom is None:
            return

        if (
            new_target_zoom.center_ring_range
            == self.__get_target_zoom__().center_ring_range
        ):
            return

        delta_since_last_change = (
            datetime.now(timezone.utc) - self.__last_changed__
        ).total_seconds()

        if delta_since_last_change < MINIMUM_SECONDS_BETWEEN_ZOOM_CHANGE:
            return

        print(f"Setting new target zoom={new_target_zoom.max_ring_range}")

        self.__last_zoom__ = self.__get_target_zoom__()
        self.__last_changed__ = datetime.now(timezone.utc)

        if new_target_zoom.center_ring_range > self.__last_zoom__.center_ring_range:
            self.__zoom_manager__.automatic_zoom_out()
        elif new_target_zoom.center_ring_range < self.__last_zoom__.center_ring_range:
            self.__zoom_manager__.automatic_zoom_in()

    def __update_units__(self) -> None:
        self.__user_units__ = configuration.CONFIGURATION.get_units()

    def __get_target_zoom__(self) -> ScopeRange:
        return self.__zoom_manager__.get_current_zoom()
