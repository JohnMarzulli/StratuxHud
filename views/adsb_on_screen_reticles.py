import pygame

from adsb_element import *
from hud_elements import *

testing.load_imports()

import units

from lib.display import *
from lib.task_timer import TaskTimer


class AdsbOnScreenReticles(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)

        self.task_timer = TaskTimer('AdsbOnScreenReticles')

        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__top_border__ = int(self.__height__ * 0.1)
        self.__bottom_border__ = self.__height__ - self.__top_border__

    def __render_on_screen_reticle__(self,  framebuffer, orientation, traffic):
        """
        Draws a single reticle on the screen.

        Arguments:
            framebuffer {Surface} -- Render target
            orientation {Orientation} -- The orientation of the plane.
            traffic {Traffic} -- The traffic to draw the reticle for.
        """

        identifier = traffic.get_identifer()

        # Find where to draw the reticle....
        reticle_x, reticle_y = self.__get_traffic_projection__(
            orientation, traffic)

        # Render using the Above us bug
        on_screen_reticle_scale = get_reticle_size(traffic.distance)
        reticle, reticle_size_px = self.get_onscreen_reticle(
            reticle_x, reticle_y, on_screen_reticle_scale)

        reticle_x, reticle_y = self.__rotate_reticle__([[reticle_x, reticle_y]],
                                                       orientation.roll)[0]

        self.__render_target_reticle__(framebuffer,
                                       identifier,
                                       (reticle_x, reticle_y),
                                       reticle,
                                       orientation.roll,
                                       reticle_size_px)

    def render(self, framebuffer, orientation):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        self.task_timer.start()
        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.get_reliable_traffic()

        traffic_reports = filter(lambda x: not x.is_on_ground(),
                                 traffic_reports)
        traffic_reports = traffic_reports[:max_target_bugs]

        [self.__render_on_screen_reticle__(framebuffer, orientation, traffic)
         for traffic in traffic_reports]

        self.task_timer.stop()

    def __render_target_reticle__(self, framebuffer, identifier, pos, reticle_lines, roll, reticle_size_px):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        center_x, center_y = pos
        border_space = int(reticle_size_px * 1.2)

        center_y = border_space if center_y < border_space else center_y
        center_y = int(self.__height__ - border_space) \
            if center_y > (self.__height__ - border_space) else center_y

        pygame.draw.lines(framebuffer,
                          BLACK, True, reticle_lines, 20)
        pygame.draw.lines(framebuffer,
                          RED, True, reticle_lines, 10)

    def __rotate_reticle__(self, reticle, roll):
        """
        Takes a series of line segments and rotates them (roll) about
        the screen's center

        Arguments:
            reticle {list of tuples} -- The line segments
            roll {float} -- The amount to rotate about the center by.

        Returns:
            list of lists -- The new list of line segments
        """

        # Takes the roll in degrees
        # Example input..
        # [
        #     [center_x, center_y - size],
        #     [center_x + size, center_y],
        #     [center_x, center_y + size],
        #     [center_x - size, center_y]
        # ]

        translated_points = []

        int_roll = int(-roll)
        cos_roll = COS_RADIANS_BY_DEGREES[int_roll]
        sin_roll = SIN_RADIANS_BY_DEGREES[int_roll]
        ox, oy = self.__center__

        translated_points = [[(ox + cos_roll * (x_y[0] - ox) - sin_roll * (x_y[1] - oy)),
                              (oy + sin_roll * (x_y[0] - ox) + cos_roll * (x_y[1] - oy))]
                             for x_y in reticle]

        return translated_points


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbOnScreenReticles)
