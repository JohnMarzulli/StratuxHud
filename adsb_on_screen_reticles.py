import pygame

from adsb_element import *
from hud_elements import *
from lib.display import *
from lib.task_timer import TaskTimer


class AdsbOnScreenReticles(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration)

        self.task_timer = TaskTimer('AdsbOnScreenReticles')

        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__max_reports__ = int(
            (self.__height__ - self.__listing_text_start_y__) / self.__next_line_distance__)
        self.__top_border__ = int(self.__height__ * 0.1)
        self.__bottom_border__ = self.__height__ - self.__top_border__

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.RELIABLE_TRAFFIC_REPORTS

        if traffic_reports is None:
            self.task_timer.stop()
            return

        for traffic in traffic_reports:
            # Do not render reticles for things to far away
            if traffic.distance > imperial_occlude:
                continue

            if traffic.is_on_ground():
                continue

            identifier = traffic.get_identifer()

            # Find where to draw the reticle....
            reticle_x, reticle_y = self.__get_traffic_projection__(
                orientation, traffic)

            # Render using the Above us bug
            on_screen_reticle_scale = get_reticle_size(traffic.distance)
            reticle, reticle_size_px = self.get_onscreen_reticle(
                reticle_x, reticle_y, on_screen_reticle_scale)

            if reticle_y < self.__top_border__ or reticle_y > self.__bottom_border__ or \
                    reticle_x < 0 or reticle_x > self.__width__:
                continue
            else:
                reticle_x, reticle_y = self.__rotate_reticle__(
                    [[reticle_x, reticle_y]], orientation.roll)[0]

                self.__render_target_reticle__(
                    framebuffer, identifier, reticle_x, reticle_y, reticle, orientation.roll, reticle_size_px)
        self.task_timer.stop()

    def __render_target_reticle__(self, framebuffer, identifier, center_x, center_y, reticle_lines, roll, reticle_size_px):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        border_space = int(reticle_size_px * 1.2)

        if center_y < border_space:
            center_y = border_space

        if center_y > (self.__height__ - border_space):
            center_y = int(self.__height__ - border_space)

        pygame.draw.lines(framebuffer,
                          BLACK, True, reticle_lines, 20)
        pygame.draw.lines(framebuffer,
                          RED, True, reticle_lines, 10)

        # TEST - Do not render the tail number
        # Move the identifer text away from the reticle
        # if center_y < self.__center__[1]:
        #     center_y = center_y + border_space
        # else:
        #     center_y = center_y - border_space

        # texture, texture_size = HudDataCache.get_cached_text_texture(
        #     identifier, self.__font__)

        # self.__render_texture__(
        #     framebuffer, (center_x, center_y), texture, texture_size, roll)

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

        for x_y in reticle:
            px, py = x_y

            qx = ox + cos_roll * (px - ox) - sin_roll * (py - oy)
            qy = oy + sin_roll * (px - ox) + cos_roll * (py - oy)

            translated_points.append([qx, qy])

        return translated_points


if __name__ == '__main__':
    import hud_elements
    hud_elements.run_adsb_hud_element(AdsbOnScreenReticles)
