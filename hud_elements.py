import display
import pygame
import math
import datetime
from lib.task_timer import TaskTimer

import aircraft
from traffic import AdsbTrafficClient, Traffic
from configuration import Configuration, DEFAULT_CONFIG_FILE

__sin_radians_by_degrees__ = {}
__cos_radians_by_degrees__ = {}

feet_to_nm = 6076.12
feet_to_sm = 5280.0
feet_to_km = 3280.84
feet_to_m = 3.28084
imperial_nearby = 3000.0
imperial_occlude = feet_to_sm * 5
imperial_faraway = feet_to_sm * 2
imperial_superclose = feet_to_sm / 4.0

for degrees in range(-360, 361):
    radians = math.radians(degrees)
    __sin_radians_by_degrees__[degrees] = math.sin(radians)
    __cos_radians_by_degrees__[degrees] = math.cos(radians)


def get_reticle_size(distance, min_reticle_size=0.05, max_reticle_size=0.20):
    on_screen_reticle_scale = min_reticle_size  # 0.05

    if distance <= imperial_superclose:
        on_screen_reticle_scale = max_reticle_size
    elif distance >= imperial_faraway:
        on_screen_reticle_scale = min_reticle_size
    else:
        delta = distance - imperial_superclose
        scale_distance = imperial_faraway - imperial_superclose
        ratio = delta / scale_distance
        reticle_range = max_reticle_size - min_reticle_size

        on_screen_reticle_scale = min_reticle_size + \
            (reticle_range * (1.0 - ratio))

    return on_screen_reticle_scale


class HudDataCache(object):
    TRAFFIC_TEXT_CACHE = {}
    RELIABLE_TRAFFIC_REPORTS = []

    @staticmethod
    def update_traffic_reports():
        HudDataCache.RELIABLE_TRAFFIC_REPORTS = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

    @staticmethod
    def get_identifier_texture(identifier, font):
        if identifier not in HudDataCache.TRAFFIC_TEXT_CACHE:
            texture = font.render(
                identifier, True, display.YELLOW, display.BLACK)  # .convert()
            text_width, text_height = texture.get_size()
            HudDataCache.TRAFFIC_TEXT_CACHE[identifier] = texture, (
                text_width, text_height)

        return HudDataCache.TRAFFIC_TEXT_CACHE[identifier]


class AhrsNotAvailable(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('AhrsNotAvailable')
        self.__not_available_lines__ = []

        width, height = framebuffer_size

        self.__not_available_lines__.append([[0, 0], [width, height]])
        self.__not_available_lines__.append([[0, height], [width, 0]])
        self.__na_color__ = display.RED
        self.__na_line_width__ = 20

    def render(self, framebuffer, orientation):
        """
        Render an "X" over the screen to indicate the AHRS is not
        available.
        """

        self.task_timer.start()
        pygame.draw.line(framebuffer, self.__na_color__, self.__not_available_lines__[
                         0][0], self.__not_available_lines__[0][1], self.__na_line_width__)
        pygame.draw.line(framebuffer, self.__na_color__, self.__not_available_lines__[
                         1][0], self.__not_available_lines__[1][1], self.__na_line_width__)
        self.task_timer.stop()


class LevelReference(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('LevelReference')
        self.level_reference_lines = []

        width = framebuffer_size[0]
        center = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        edge_reference_proportion = int(width * 0.05)

        artificial_horizon_level = [[int(width * 0.4),  center[1]],
                                    [int(width * 0.6),  center[1]]]
        left_hash = [[0, center[1]], [edge_reference_proportion, center[1]]]
        right_hash = [[width - edge_reference_proportion,
                       center[1]], [width, center[1]]]

        self.level_reference_lines.append(artificial_horizon_level)
        self.level_reference_lines.append(left_hash)
        self.level_reference_lines.append(right_hash)

    def render(self, framebuffer, orientation):
        """
        Renders a "straight and level" line to the HUD.
        """

        self.task_timer.start()
        for line in self.level_reference_lines:
            pygame.draw.lines(framebuffer,
                              display.GRAY, False, line, 2)
        self.task_timer.stop()


def get_heading_bug_x(heading, bearing, degrees_per_pixel):
    delta = (bearing - heading + 180)
    if delta < 0:
        delta += 360

    if delta > 360:
        delta -= 360

    return int(delta * degrees_per_pixel)


def get_onscreen_traffic_projection__(heading, pitch, roll, bearing, distance, altitude_delta, pixels_per_degree):
    """
    Attempts to figure out where the traffic reticle should be rendered.
    Returns value RELATIVE to the screen center.
    """

    # Assumes traffic.position_valid
    # TODO - Account for aircraft roll...
    slope = altitude_delta / distance
    vertical_degrees_to_target = math.degrees(math.atan(slope))
    vertical_degrees_to_target -= pitch

    # TODO - Double check ALL of this math...
    horizontal_degrees_to_target = bearing - heading

    screen_y = -vertical_degrees_to_target * pixels_per_degree
    screen_x = horizontal_degrees_to_target * pixels_per_degree

    return screen_x, screen_y


class ArtificialHorizon(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('ArtificialHorizon')
        self.__pitch_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.1
        self.__pixels_per_degree_y__ = pixels_per_degree_y
        self.__height__ = framebuffer_size[1]

        for reference_angle in range(-degrees_of_pitch, degrees_of_pitch + 1, 10):
            text = font.render(
                str(reference_angle), True, display.WHITE, display.BLACK).convert()
            size_x, size_y = text.get_size()
            self.__pitch_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

    def render(self, framebuffer, orientation):
        self.task_timer.start()

        for reference_angle in self.__pitch_elements__:
            line_coords, line_center = self.__get_line_coords__(
                orientation.pitch, orientation.roll, reference_angle)

            # Perform some trivial clipping of the lines
            # This also prevents early text rasterization
            if line_center[1] < 0 or line_center[1] > self.__height__:
                continue

            pygame.draw.lines(framebuffer,
                              display.GREEN, False, line_coords, 2)

            text, half_size = self.__pitch_elements__[reference_angle]
            text = pygame.transform.rotate(text, orientation.roll)
            half_x, half_y = half_size
            center_x, center_y = line_center

            framebuffer.blit(text, (center_x - half_x, center_y - half_y))
        self.task_timer.stop()

    def __get_line_coords__(self, pitch, roll, reference_angle):
        """
        Get the coordinate for the lines for a given pitch and roll.
        """

        if reference_angle == 0:
            length = self.__long_line_width__
        else:
            length = self.__short_line_width__

        pitch = int(pitch)
        roll = int(roll)

        ahrs_center_x, ahrs_center_y = self.__center__
        pitch_offset = self.__pixels_per_degree_y__ * \
            (-pitch + reference_angle)

        roll_delta = 90 - roll

        center_x = int(
            (ahrs_center_x - (pitch_offset * __cos_radians_by_degrees__[roll_delta])) + 0.5)
        center_y = int(
            (ahrs_center_y - (pitch_offset * __sin_radians_by_degrees__[roll_delta])) + 0.5)

        x_len = int((length * __cos_radians_by_degrees__[roll]) + 0.5)
        y_len = int((length * __sin_radians_by_degrees__[roll]) + 0.5)

        half_x_len = x_len >> 1
        half_y_len = y_len >> 1

        start_x = center_x - half_x_len
        end_x = center_x + half_x_len
        start_y = center_y + half_y_len
        end_y = center_y - half_y_len

        return [[int(start_x), int(start_y)], [int(end_x), int(end_y)]], (int(center_x), int(center_y))


class CompassAndHeadingTopElement(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('CompassAndHeadingTopElement')
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.1
        self.__pixels_per_degree_y__ = pixels_per_degree_y

        self.heading_text_y = int(font.get_height() * 2)
        self.compass_text_y = int(font.get_height() * 3)

        self.pixels_per_degree_x = framebuffer_size[0] / 360.0
        cardinal_direction_line_proportion = 0.05
        self.line_height = int(
            framebuffer_size[1] * cardinal_direction_line_proportion)
        self.__font__ = font

        self.__heading_text__ = {}
        for heading in range(-1, 361):
            texture = self.__font__.render(
                str(heading), True, display.BLACK, display.YELLOW).convert()
            width, height = texture.get_size()
            self.__heading_text__[heading] = texture, (width >> 1, height >> 1)

        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        half_width = int(self.__heading_text__[360][1][0] * 3.5)

        self.__center_x__ = self.__center__[0]

        self.__heading_text_box_lines__ = [
            [self.__center_x__ - half_width,
             self.compass_text_y - border_vertical_size],
            [self.__center_x__ + half_width,
             self.compass_text_y - border_vertical_size],
            [self.__center_x__ + half_width,
             self.compass_text_y + border_vertical_size],
            [self.__center_x__ - half_width, self.compass_text_y + border_vertical_size]]

        self.__heading_strip_offset__ = {}
        for heading in range(0, 181):
            self.__heading_strip_offset__[heading] = int(
                self.pixels_per_degree_x * heading)

        self.__heading_strip__ = {}

        for heading in range(0, 361):
            self.__heading_strip__[
                heading] = self.__generate_heading_strip__(heading)

        self.__render_heading_mark_timer__ = TaskTimer("HeadingRender")

    def __generate_heading_strip__(self, heading):
        things_to_render = []
        for heading_strip in self.__heading_strip_offset__:
            to_the_left = (heading - heading_strip)
            to_the_right = (heading + heading_strip)

            if to_the_left < 0:
                to_the_left += 360

            if to_the_right > 360:
                to_the_right -= 360

            if (to_the_left == 0) or ((to_the_left % 90) == 0):
                line_x_left = self.__center_x__ - \
                    self.__heading_strip_offset__[heading_strip]
                things_to_render.append([line_x_left, to_the_left])

            if to_the_left == to_the_right:
                continue

            if (to_the_right % 90) == 0:
                line_x_right = self.__center_x__ + \
                    self.__heading_strip_offset__[heading_strip]
                things_to_render.append([line_x_right, to_the_right])

        return things_to_render

    def __render_heading_mark__(self, framebuffer, x_pos, heading):
        pygame.draw.line(framebuffer, display.GREEN,
                         [x_pos, self.line_height], [x_pos, 0], 2)

        self.__render_heading_text__(
            framebuffer, heading, x_pos, self.heading_text_y)

    def render(self, framebuffer, orientation):
        """
        Renders the current heading to the HUD.
        """

        self.task_timer.start()

        # Render a crude compass
        # Render a heading strip along the top

        heading = orientation.get_onscreen_projection_heading()

        for heading_mark_to_render in self.__heading_strip__[heading]:
            self.__render_heading_mark__(
                framebuffer, heading_mark_to_render[0], heading_mark_to_render[1])

        # Render the text that is showing our AHRS and GPS headings
        cover_old_rendering_spaces = "  "
        heading_text = "{0}{1} | {2}{0}".format(cover_old_rendering_spaces,
                                                str(orientation.get_onscreen_projection_display_heading()).rjust(
                                                    3),
                                                str(int(orientation.gps_heading)).rjust(3))

        rendered_text = self.__font__.render(
            heading_text, True, display.GREEN, display.BLACK)
        text_width, text_height = rendered_text.get_size()

        framebuffer.blit(
            rendered_text, (self.__center_x__ - (text_width >> 1), self.compass_text_y - (text_height >> 1)))

        pygame.draw.lines(framebuffer, display.GREEN, True,
                          self.__heading_text_box_lines__, 2)
        self.task_timer.stop()

    def __render_heading_text__(self, framebuffer, heading, position_x, position_y):
        """
        Renders the text with the results centered on the given
        position.
        """
        rendered_text, half_size = self.__heading_text__[heading]

        framebuffer.blit(
            rendered_text, (position_x - half_size[0], position_y - half_size[1]))


class CompassAndHeadingBottomElement(CompassAndHeadingTopElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        CompassAndHeadingTopElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size)
        self.task_timer = TaskTimer('CompassAndHeadingBottomElement')
        self.__line_top__ = framebuffer_size[1] - self.line_height
        self.__line_bottom__ = framebuffer_size[1]
        self.heading_text_y = self.__line_top__ - (font.get_height() * 1.2)

        self.compass_text_y = self.__line_bottom__ - \
            int(font.get_height() * 3.5)
        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        half_width = int(self.__heading_text__[360][1][0] * 3.5)
        self.__heading_text_box_lines__ = [
            [self.__center_x__ - half_width,
             self.compass_text_y - border_vertical_size],
            [self.__center_x__ + half_width,
             self.compass_text_y - border_vertical_size],
            [self.__center_x__ + half_width,
             self.compass_text_y + border_vertical_size],
            [self.__center_x__ - half_width, self.compass_text_y + border_vertical_size]]

    def __render_heading_mark__(self, framebuffer, x_pos, heading):
        pygame.draw.line(framebuffer, display.GREEN,
                         [x_pos, self.__line_top__], [x_pos, self.__line_bottom__], 2)

        self.__render_heading_text__(
            framebuffer, heading, x_pos, self.heading_text_y)

    def render(self, framebuffer, orientation):
        """
        Renders the current heading to the HUD.
        """

        self.task_timer.start()

        # Render a crude compass
        # Render a heading strip along the top

        heading = orientation.get_onscreen_projection_heading()

        if heading < 0:
            heading += 360

        if heading > 360:
            heading -= 360

        for heading_mark_to_render in self.__heading_strip__[heading]:
            self.__render_heading_mark__(
                framebuffer, heading_mark_to_render[0], heading_mark_to_render[1])

        # Render the text that is showing our AHRS and GPS headings
        heading_text = "{0} | {1}".format(
            orientation.get_onscreen_projection_display_heading(), int(orientation.gps_heading))

        rendered_text = self.__font__.render(
            heading_text, True, display.BLACK, display.GREEN)
        text_width, text_height = rendered_text.get_size()

        pygame.draw.polygon(framebuffer, display.GREEN,
                            self.__heading_text_box_lines__)
        # pygame.draw.lines(framebuffer, display.GREEN, True,
        #                  self.__heading_text_box_lines__, 2)
        framebuffer.blit(
            rendered_text, (self.__center_x__ - (text_width >> 1), self.compass_text_y - (text_height >> 1)))
        self.task_timer.stop()


class Altitude(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('Altitude')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        altitude_text = str(int(orientation.alt)) + "' MSL"
        alt_texture = self.__font__.render(
            altitude_text, True, display.WHITE, display.BLACK)
        text_width, text_height = alt_texture.get_size()

        framebuffer.blit(
            alt_texture, (self.__rhs__ - text_width, self.__text_y_pos__))
        self.task_timer.stop()


class SkidAndGs(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('SkidAndGs')
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = (text_half_height << 2) + \
            center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        g_load_text = "{0:.1f}Gs".format(orientation.g_load)
        texture = self.__font__.render(
            g_load_text, True, display.WHITE, display.BLACK)
        text_width, text_height = texture.get_size()

        framebuffer.blit(
            texture, (self.__rhs__ - text_width, self.__text_y_pos__))
        self.task_timer.stop()


class RollIndicator(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('RollIndicator')
        self.__roll_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        half_texture_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = self.__center__[1] - half_texture_height

        for reference_angle in range(-180, 181):
            text = font.render(
                "{0:3}".format(int(math.fabs(reference_angle))), True, display.WHITE, display.BLACK)
            size_x, size_y = text.get_size()
            self.__roll_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

    def render(self, framebuffer, orientation):
        self.task_timer.start()
        roll = int(orientation.roll)

        roll_texture, texture_size = self.__roll_elements__[roll]
        roll_texture = pygame.transform.rotate(roll_texture, roll)
        text_half_width, text_half_height = texture_size
        framebuffer.blit(
            roll_texture, (self.__center__[0] - text_half_width, self.__text_y_pos__))
        self.task_timer.stop()


class AdsbElement(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration):
        self.__roll_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        half_texture_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = self.__center__[1] - half_texture_height
        self.__font__ = font
        self.__configuration__ = configuration
        self.__top_border__ = int(framebuffer_size[1] * 0.5)
        self.__bottom_border__ = framebuffer_size[1] - self.__top_border__
        self.__pixels_per_degree_y__ = pixels_per_degree_y
        self.__pixels_per_degree_x__ = self.__framebuffer_size__[0] / 360.0
        self.__height__ = framebuffer_size[1]
        self.__width__ = framebuffer_size[0]

    def __get_distance_string__(self, distance):
        sm = "statute"
        nm = "knots"
        metric = "metric"

        units = self.__configuration__.__get_config_value__(
            Configuration.DISTANCE_UNITS_KEY, sm)

        if units is not metric:
            if distance < imperial_nearby:
                return "{0:.0f}".format(distance) + "'"

            if units is nm:
                return "{0:.1f}NM".format(distance / feet_to_nm)

            return "{0:.1f}SM".format(distance / feet_to_sm)
        else:
            conversion = distance / feet_to_km

            if conversion > 0.5:
                return "{0:.1f}km".format(conversion)

            return "{0:.1f}m".format(distance / feet_to_m)

        return "{0:.0f}'".format(distance)

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

        below_reticle = [
            [center_x - (size >> 2), self.__height__ - size],
            [center_x, self.__height__],
            [center_x + (size >> 2), self.__height__ - size]
        ]

        return below_reticle, self.__height__ - size

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
        bearing_text = "{0}".format(int(traffic_report.bearing))

        return [bearing_text, distance_text, altitude_text]

    def __render_heading_bug__(self, framebuffer,
                               identifier_text,
                               additional_info_text,
                               center_x, target_bug_scale, is_top):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        # Only draw the ones that would not be on the screen
        if is_top:
            reticle, reticle_edge_positon_y = self.get_above_reticle(
                center_x, target_bug_scale)
        else:
            reticle, reticle_edge_positon_y = self.get_below_reticle(
                center_x, target_bug_scale)

        pygame.draw.polygon(framebuffer, display.RED, reticle)

        texture, texture_size = HudDataCache.get_identifier_texture(
            identifier_text, self.__font__)
        text_width, text_height = texture_size

        additional_info_textures = [texture]
        for additional_text in additional_info_text:
            additional_info_textures.append(self.__font__.render(
                additional_text, True, display.YELLOW, display.BLACK))

        info_spacing = 1.2

        if is_top:
            info_position_y = reticle_edge_positon_y + \
                (text_height >> 1) + int(text_height * (1.0 - info_spacing))
        else:
            info_position_y = reticle_edge_positon_y - \
                int((len(additional_info_textures) * info_spacing) * text_height)

        self.__render_info_text__(
            additional_info_textures, center_x, framebuffer, info_position_y, info_spacing)

    def __render_info_text__(self, additional_info_textures, center_x, framebuffer, info_position_y, info_spacing):
        for info_texture in additional_info_textures:
            width_x, width_y = info_texture.get_size()
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
                          display.RED, True, reticle_lines, 4)

        # Move the identifer text away from the reticle
        if center_y < self.__center__[1]:
            text_y = center_y + border_space
        else:
            text_y = center_y - border_space

        rendered_text = self.__font__.render(
            str(identifier), True, display.YELLOW)
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


class AdsbListing(AdsbElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration):
        AdsbElement.__init__(
            self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size, configuration)

        self.task_timer = TaskTimer('AdsbListing')
        self.__listing_text_start_y__ = int(self.__font__.get_height() * 4)
        self.__listing_text_start_x__ = int(
            self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height() * 1.5)
        self.__max_reports__ = int(
            (self.__height__ - self.__listing_text_start_y__) / self.__next_line_distance__)
        self.__top_border__ = int(self.__height__ * 0.2)
        self.__bottom_border__ = self.__height__ - int(self.__height__ * 0.1)

    def render(self, framebuffer, orientation):
        # Render a heading strip along the top

        self.task_timer.start()
        heading = orientation.get_onscreen_projection_heading()

        # Get the traffic, and bail out of we have none
        traffic_reports = HudDataCache.RELIABLE_TRAFFIC_REPORTS

        if traffic_reports is None:
            self.task_timer.stop()
            return

        # Draw the heading bugs in reverse order so the traffic closest to
        # us will be the most visible
        traffic_bug_reports = sorted(
            HudDataCache.RELIABLE_TRAFFIC_REPORTS, key=lambda traffic: traffic.distance, reverse=True)

        for traffic_report in traffic_bug_reports:
            if traffic_report.distance > imperial_occlude:
                continue

            # Now find where to draw the reticle....
            reticle_x, reticle_y = self.__get_traffic_projection__(
                orientation, traffic_report)

            # Render using the Above us bug
            # target_bug_scale = 0.04
            target_bug_scale = get_reticle_size(traffic_report.distance)

            is_onscreen_x = reticle_x >= 0 and reticle_x < self.__width__
            is_onscreen_y = reticle_y >= self.__top_border__ and reticle_y <= self.__bottom_border__
            is_top = reticle_y <= self.__center__[1]

            if is_onscreen_x and is_onscreen_y:
                continue

            heading_bug_x = get_heading_bug_x(
                heading, traffic_report.bearing, self.__pixels_per_degree_x__)

            additional_info_text = self.__get_additional_target_text__(
                traffic_report, orientation)

            self.__render_heading_bug__(framebuffer,
                                        str(traffic_report.get_identifer()),
                                        additional_info_text,
                                        heading_bug_x,
                                        target_bug_scale,
                                        is_top)
        self.task_timer.stop()


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
                reticle = self.__rotate_reticle__(reticle, orientation.roll)
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
                          display.RED, True, reticle_lines, 4)

        # Move the identifer text away from the reticle
        if center_y < self.__center__[1]:
            center_y = center_y + border_space
        else:
            center_y = center_y - border_space

        texture, texture_size = HudDataCache.get_identifier_texture(
            identifier, self.__font__)

        self.__render_texture__(
            framebuffer, (center_x, center_y), texture, texture_size, roll)

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

        int_roll = int(roll)
        cos_roll = __cos_radians_by_degrees__[int_roll]
        sin_roll = __sin_radians_by_degrees__[int_roll]
        ox, oy = self.__center__

        for x_y in reticle:
            px, py = x_y

            qx = ox + cos_roll * (px - ox) - sin_roll * (py - oy)
            qy = oy + sin_roll * (px - ox) + cos_roll * (py - oy)

            translated_points.append([qx, qy])

        return translated_points


if __name__ == '__main__':
    for distance in range(0, int(2.5 * feet_to_sm), int(feet_to_sm / 10.0)):
        print "{0}' -> {1}".format(distance, get_reticle_size(distance))

    heading = 327
    pitch = 0
    roll = 0
    distance = 1000
    altitude_delta = 1000
    pixels_per_degree = 10
    for bearing in range(0, 360, 10):
        print "Bearing {0} -> {1}px".format(bearing, get_heading_bug_x(heading, bearing, 2.2222222))
        x, y = get_onscreen_traffic_projection__(
            heading, pitch, roll, bearing, distance, altitude_delta, pixels_per_degree)
        print "    {0}, {1}".format(x + 400, y + 240)
