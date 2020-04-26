"""
View to render heading targets.
"""

from numbers import Number

import pygame

from common_utils import units
from common_utils.task_timer import TaskTimer
from configuration import configuration
from data_sources import norden, targets
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from rendering import colors, display
from views import utils
from views.adsb_target_bugs import AdsbTargetBugs
from views.ahrs_element import AhrsElement
from views.hud_elements import (get_heading_bug_x, get_reticle_size,
                                run_adsb_hud_element)


class HeadingAsTrafficObject(object):
    """
    Class that allows for the creation of an arbitrary
    piece of "traffic" that can then be used to create
    a heading bug.
    """

    def __init__(
        self,
        altitude: float,
        distance: float,
        bearing: float
    ):
        self.altitude = altitude
        self.distance = distance
        self.bearing = bearing


class HeadingTargetBugs(AdsbTargetBugs):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        AdsbTargetBugs.__init__(
            self,
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size)

        self.task_timer = TaskTimer('HeadingTargetBugs')
        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def __get_additional_target_text__(
        self,
        time_until_drop: float = 0.0,
        altitude: float = None,
        distance: float = 0.0
    ) -> str:
        """
        Returns a tuple of text to be rendered with the target card.

        Keyword Arguments:
            time_until_drop {float} -- The number of seconds until the flour bomb should be dropped. (default: {0.0})
            altitude_delta {float} -- The number of feet above the target. (default: {0.0})
            distance_meters {float} -- The distance (in meters) to the target. (default: {0.0})

        Returns:
            string[] -- Tuple of strings.
        """

        distance_text = self.__get_distance_string__(distance)
        altitude_text = "{0:.1f}AGL".format(altitude)

        if time_until_drop < 60:
            time_until_drop = "{0:.1f}S".format(time_until_drop)
        else:
            time_until_drop = "---"

        return [altitude_text, distance_text, time_until_drop]

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        # Render a heading strip along the top

        self.task_timer.start()
        heading = orientation.get_onscreen_projection_heading()

        # Get the traffic, and bail out of we have none
        if targets.TARGET_MANAGER is None or targets.TARGET_MANAGER.targets is None:
            return

        for target_position in targets.TARGET_MANAGER.targets:
            ground_speed_ms = units.get_meters_per_second_from_mph(
                orientation.groundspeed)
            distance_miles = norden.get_distance(
                orientation.position,
                target_position)
            distance_meters = units.get_meters_from_statute_miles(
                distance_miles)
            time_to_target = norden.get_time_to_distance(
                distance_meters,
                ground_speed_ms)
            # NOTE:
            # Remember that the altitude off the AHRS is
            # in terms of MSL. That means that we need to
            # subtract out the altitude of the target.
            delta_altitude = orientation.alt - target_position[2]
            time_to_impact = norden.get_time_to_impact(
                units.get_meters_from_feet(delta_altitude))
            time_until_drop = time_to_target - time_to_impact
            # target_altitude_for_drop = units.get_feet_from_meters(
            #     norden.get_altitude(time_to_target))
            bearing_to_target = norden.get_bearing(
                target_position, orientation.position)
            # time_to_impact_from_ideal_current_altitude = norden.get_time_to_impact(
            #    target_altitude_for_drop)

            # Render using the Above us bug
            # target_bug_scale = 0.04
            # target_bug_scale = get_reticle_size(distance_miles)

            heading_bug_x = get_heading_bug_x(
                heading,
                bearing_to_target,
                self.__pixels_per_degree_x__)

            additional_info_text = self.__get_additional_target_text__(
                time_until_drop,
                delta_altitude,
                units.get_yards_from_miles(distance_miles))

            self.__render_info_card__(
                framebuffer,
                "{0:.1f}".format(
                    utils.apply_declination(bearing_to_target)),
                additional_info_text,
                heading_bug_x,
                False)

            as_traffic = HeadingAsTrafficObject(
                target_position[2],
                units.get_yards_from_miles(distance_miles),
                bearing_to_target)

            target_bug_scale = get_reticle_size(as_traffic.distance)

            heading_bug_x = get_heading_bug_x(
                heading,
                utils.apply_declination(as_traffic.bearing),
                self.__pixels_per_degree_x__)

            reticle, reticle_edge_position_y = self.get_below_reticle(
                heading_bug_x,
                target_bug_scale)

            pygame.draw.polygon(
                framebuffer,
                colors.BLUE,
                reticle)

        self.task_timer.stop()


if __name__ == '__main__':
    run_adsb_hud_element(HeadingTargetBugs)
