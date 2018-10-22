"""
View to render heading targets.
"""


import pygame

from adsb_element import AdsbElement
from hud_elements import HudDataCache, get_reticle_size, get_heading_bug_x
import hud_elements
import utils
import testing
testing.load_imports()

from lib.task_timer import TaskTimer
import norden
import units
import targets


class HeadingTargetBugs(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)

        self.task_timer = TaskTimer('HeadingTargetBugs')
        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def __get_additional_target_text__(self, time_until_drop=0.0, altitude_delta=0.0, distance_meters=0.0):
        """
        Returns a tuple of text to be rendered with the target card.
        
        Keyword Arguments:
            time_until_drop {float} -- The number of seconds until the flour bomb should be dropped. (default: {0.0})
            altitude_delta {float} -- The number of feet above the target. (default: {0.0})
            distance_meters {float} -- The distance (in meters) to the target. (default: {0.0})
        
        Returns:
            string[] -- Tuple of strings.
        """

        if altitude_delta < 0:
            altitude_delta = 0.0

        if time_until_drop < 0.0:
            altitude_delta = 0

        distance_text = self.__get_distance_string__(distance_meters)
        altitude_text = "{0:.1f}AGL".format(altitude_delta)
        time_until_drop = "{0:.1f}S".format(time_until_drop)

        return [altitude_text, distance_text, time_until_drop]

    def render(self, framebuffer, orientation):
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
            distance_meters = units.get_meters_from_feet(
                units.get_feet_from_miles(distance_miles))
            time_to_target = norden.get_time_to_distance(
                distance_meters, ground_speed_ms)
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
                heading, bearing_to_target, self.__pixels_per_degree_x__)

            additional_info_text = self.__get_additional_target_text__(
                time_until_drop, delta_altitude, units.get_feet_from_miles(distance_miles))

            self.__render_info_card__(framebuffer,
                                      "{0:.1f}".format(utils.apply_declination(bearing_to_target)),
                                      additional_info_text,
                                      heading_bug_x,
                                      False)
        self.task_timer.stop()


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(HeadingTargetBugs)
