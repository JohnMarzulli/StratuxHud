import math

import pygame
import utils
import testing

testing.load_imports()

import units
from configuration import Configuration
import hud_elements
from lib.display import *
from lib.task_timer import TaskTimer
import lib.colors as colors
import configuration


class AdsbElement(object):
    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True

    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.__roll_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        half_texture_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = self.__center__[1] - half_texture_height
        self.__font__ = font
        self.__top_border__ = int(framebuffer_size[1] * 0.5)
        self.__bottom_border__ = framebuffer_size[1] - self.__top_border__
        self.__pixels_per_degree_y__ = pixels_per_degree_y
        self.__pixels_per_degree_x__ = self.__framebuffer_size__[0] / 360.0
        self.__height__ = framebuffer_size[1]
        self.__width__ = framebuffer_size[0]
        self.start_fade_threshold = (
            configuration.CONFIGURATION.max_minutes_before_removal * 60) / 2

    def __get_speed_string__(self, speed):
        """
        Gets the string to display for the speed. Uses the units configured by the user.

        Arguments:
            speed {number} -- The raw speed from the sensor.

        Returns:
            string -- A string with the speed and the correct units.
        """

        speed_units = configuration.CONFIGURATION.__get_config_value__(
            Configuration.DISTANCE_UNITS_KEY, units.STATUTE)

        return units.get_converted_units_string(speed_units, speed, units.SPEED)

    def __get_distance_string__(self, distance):
        """
        Gets the distance string for display using the units
        from the configuration.

        Arguments:
            distance {float} -- The distance... straight from the GDL90 which means FEET

        Returns:
            string -- The distance in a handy string for display.
        """

        display_units = configuration.CONFIGURATION.__get_config_value__(
            Configuration.DISTANCE_UNITS_KEY, units.STATUTE)

        return units.get_converted_units_string(display_units, distance)

    def __get_traffic_projection__(self, orientation, traffic):
        """
        Attempts to figure out where the traffic reticle should be rendered.
        Returns value within screen space
        """

        # Assumes traffic.position_valid
        # TODO - Account for aircraft roll...

        altitude_delta = int(traffic.altitude - orientation.alt)
        slope = altitude_delta / traffic.distance
        vertical_degrees_to_target = math.degrees(math.atan(slope))
        vertical_degrees_to_target -= orientation.pitch

        # TODO - Double check ALL of this math...
        compass = orientation.get_onscreen_projection_heading()
        horizontal_degrees_to_target = traffic.bearing - compass

        screen_y = -vertical_degrees_to_target * self.__pixels_per_degree_y__
        screen_x = horizontal_degrees_to_target * self.__pixels_per_degree_y__

        return self.__center__[0] + screen_x, self.__center__[1] + screen_y

    def get_above_reticle(self, center_x, scale):
        """Generates the coordinates for a reticle indicating
        traffic is above use.

        Arguments:
            center_x {int} -- Center X screen position
            center_y {int} -- Center Y screen position
            scale {float} -- The scale of the reticle relative to the screen.
        """

        size = int(self.__framebuffer_size__[1] * scale)

        above_reticle = [
            [center_x - (size >> 2), self.__top_border__ + size],
            [center_x, self.__top_border__],
            [center_x + (size >> 2), self.__top_border__ + size]
        ]

        return above_reticle, self.__top_border__ + size

    def get_below_reticle(self, center_x, scale):
        """Generates the coordinates for a reticle indicating
        traffic is above use.

        Arguments:
            center_x {int} -- Center X screen position
            center_y {int} -- Center Y screen position
            scale {float} -- The scale of the reticle relative to the screen.
        """

        size = int(self.__height__ * scale)
        bug_vertical_offset = self.__font__.get_height() << 1  # int(self.__height__ * 0.25)

        below_reticle = [
            [center_x - (size >> 2), self.__height__ -
             size - bug_vertical_offset],
            [center_x, self.__height__ - bug_vertical_offset],
            [center_x + (size >> 2), self.__height__ -
             size - bug_vertical_offset]
        ]

        # self.__height__ - size - bug_vertical_offset
        return below_reticle, below_reticle[2][1]

    def get_onscreen_reticle(self, center_x, center_y, scale):
        size = int(self.__height__ * scale)

        on_screen_reticle = [
            [center_x, center_y - size],
            [center_x + size, center_y],
            [center_x, center_y + size],
            [center_x - size, center_y]
        ]

        return on_screen_reticle, size

    def __get_additional_target_text__(self, traffic_report, orientation):
        """
        Gets the additional text for a traffic report

        Arguments:
            traffic_report {[type]} -- [description]
            orientation {[type]} -- [description]

        Returns:
            [type] -- [description]
        """

        altitude_delta = int(
            (traffic_report.altitude - orientation.alt) / 100.0)
        distance_text = self.__get_distance_string__(traffic_report.distance)
        delta_sign = ''
        if altitude_delta > 0:
            delta_sign = '+'
        altitude_text = "{0}{1}".format(delta_sign, altitude_delta)
        bearing_text = "{0}".format(
            int(utils.apply_declination(traffic_report.bearing)))

        return [bearing_text, distance_text, altitude_text]

    def __render_info_card__(self,
                             framebuffer,
                             identifier_text,
                             additional_info_text,
                             center_x,
                             time_since_last_report=0.0):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        card_color = self.__get_card_color__(time_since_last_report)

        # Render all of the textures and then
        # find which one is the widest.
        all_text = [identifier_text] + additional_info_text
        all_textures_and_sizes = [hud_elements.HudDataCache.get_cached_text_texture(
            text, self.__font__, BLACK, card_color, False, False) for text in all_text]
        widest_texture = max(all_textures_and_sizes,
                             key=lambda x: x[1][0])[1][0]
        text_height = all_textures_and_sizes[0][1][1]

        info_spacing = 1.2
        texture_height = int(
            (len(all_textures_and_sizes) * info_spacing) * text_height)

        info_position_y = ((self.__height__ >> 1) -
                           (texture_height >> 1) - text_height)

        edge_left = (center_x - (widest_texture >> 1))
        edge_right = (center_x + (widest_texture >> 1))

        if edge_left < 0:
            edge_right += math.fabs(edge_left)
            edge_left = 0

        if edge_right > self.__framebuffer_size__[0]:
            diff = edge_right - self.__framebuffer_size__[0]
            edge_left -= diff
            edge_right = self.__framebuffer_size__[0]

        pixel_border_size = 4
        fill_top_left = [edge_left - pixel_border_size,
                         info_position_y - pixel_border_size]
        fill_top_right = [edge_right + pixel_border_size, fill_top_left[1]]
        fill_bottom_right = [fill_top_right[0], info_position_y + pixel_border_size +
                             int((len(additional_info_text) + 1) * info_spacing * text_height)]
        fill_bottom_left = [fill_top_left[0], fill_bottom_right[1]]

        pygame.draw.polygon(framebuffer, card_color,
                            [fill_top_left, fill_top_right, fill_bottom_right, fill_bottom_left])

        pygame.draw.lines(framebuffer,
                          BLACK, True, [fill_top_left, fill_top_right, fill_bottom_right, fill_bottom_left], 6)

        self.__render_info_text__(
            all_textures_and_sizes, center_x, framebuffer, info_position_y, info_spacing)

    def __get_card_color__(self, time_since_last_report):
        """
        Gets the color the card should be based on how long it has been
        since the traffic has had a report.

        Arguments:
            time_since_last_report {float} -- The number of seconds since the last traffic report.

        Returns:
            float[] -- The RGB tuple/array of the color the target card should be.
        """

        try:
            card_color = YELLOW

            if time_since_last_report > self.start_fade_threshold:
                max_distance = (
                    configuration.CONFIGURATION.max_minutes_before_removal * 60.0) - self.start_fade_threshold
                proportion = (time_since_last_report -
                              self.start_fade_threshold) / max_distance

                card_color = colors.get_color_mix(YELLOW, BLACK, proportion)

            return card_color
        except:
            return YELLOW

    def __render_info_text__(self, additional_info_textures, center_x, framebuffer, info_position_y, info_spacing):
        for info_texture, size in additional_info_textures:
            width_x, width_y = size
            half_width = width_x >> 1
            x_pos = center_x - half_width

            if center_x <= half_width:  # half_width:
                x_pos = 0  # half_width

            if (center_x + half_width) >= self.__width__:
                x_pos = self.__width__ - width_x

            try:
                framebuffer.blit(info_texture, [x_pos, info_position_y])
            except:
                pass

            info_position_y += int(width_y * info_spacing)

    def __render_target_reticle__(self, framebuffer, identifier, center_x, center_y, reticle_lines, roll):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        border_space = int(self.__font__.get_height() * 3.0)

        if center_y < border_space:
            center_y = border_space

        if center_y > (self.__height__ - border_space):
            center_y = int(self.__height__ - border_space)

        pygame.draw.lines(framebuffer,
                          RED, True, reticle_lines, 4)

        # Move the identifer text away from the reticle
        if center_y < self.__center__[1]:
            text_y = center_y + border_space
        else:
            text_y = center_y - border_space

        rendered_text = self.__font__.render(
            str(identifier), True, YELLOW)
        text_width, text_height = rendered_text.get_size()

        text = pygame.transform.rotate(rendered_text, roll)

        framebuffer.blit(
            text, (center_x - (text_width >> 1), text_y - (text_height >> 1)))

    def __render_texture__(self, framebuffer, position, texture, texture_size, roll):
        """
        Renders the text with the results centered on the given
        position.
        """

        position_x, position_y = position
        text_width, text_height = texture_size

        text = pygame.transform.rotate(texture, roll)

        framebuffer.blit(
            text, (position_x - (text_width >> 1), position_y - (text_height >> 1)))

        return text_width, text_height
