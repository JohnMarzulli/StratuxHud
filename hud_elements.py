import display
import pygame
import math
from lib.task_timer import TaskTimer

from traffic import AdsbTrafficClient
from configuration import Configuration

__sin_radians_by_degrees__ = {}
__cos_radians_by_degrees__ = {}

feet_to_nm = 6076.12
feet_to_sm = 5280.0
feet_to_km = 3280.84
feet_to_m = 3.28084
imperial_nearby = 3000.0
imperial_superclose = feet_to_sm / 4.0

for degrees in range(-360, 361):
    radians = math.radians(degrees)
    __sin_radians_by_degrees__[degrees] = math.sin(radians)
    __cos_radians_by_degrees__[degrees] = math.cos(radians)

TRAFFIC_TEXT_CACHE = {}

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


class ArtificialHorizon(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('ArtificialHorizon')
        self.__pitch_elements__ = {}
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)
        self.__long_line_width__ = self.__framebuffer_size__[0] * 0.2
        self.__short_line_width__ = self.__framebuffer_size__[0] * 0.1
        self.__pixels_per_degree_y__ = pixels_per_degree_y

        for reference_angle in range(-degrees_of_pitch, degrees_of_pitch + 1, 10):
            text = font.render(
                str(reference_angle), True, display.WHITE, display.BLACK)
            size_x, size_y = text.get_size()
            self.__pitch_elements__[reference_angle] = (
                text, (size_x >> 1, size_y >> 1))

    def render(self, framebuffer, orientation):
        """
        Render the pitch hash marks.
        """

        self.task_timer.start()
        for reference_angle in self.__pitch_elements__:
            line_coords, line_center = self.__get_line_coords__(
                int(orientation.pitch), int(orientation.roll), reference_angle)

            # Perform some trivial clipping of the lines
            # This also prevents early text rasterization
            if line_center[1] < 0 or line_center[1] > self.__framebuffer_size__[1]:
                continue

            pygame.draw.lines(framebuffer,
                              display.GREEN, False, line_coords, 2)

            text, half_size = self.__pitch_elements__[reference_angle]
            text = pygame.transform.rotate(text, orientation.roll)
            half_x, half_y = half_size
            center_x, center_y = line_center

            framebuffer.blit(text, (center_x - half_x, center_y - half_y))
        self.task_timer.stop()

    def __get_line_coords__(self, pitch=0, roll=0, hash_mark_angle=0):
        """
        Get the coordinate for the lines for a given pitch and roll.
        """

        if hash_mark_angle == 0:
            length = self.__long_line_width__
        else:
            length = self.__short_line_width__

        ahrs_center_x, ahrs_center_y = self.__center__
        pitch_offset = self.__pixels_per_degree_y__ * \
            (-pitch + hash_mark_angle)

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

        return [[start_x, start_y], [end_x, end_y]], (center_x, center_y)


class CompassAndHeading(object):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('CompassAndHeading')
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
            self.__heading_text__[heading] = self.__font__.render(
                str(heading), True, display.GREEN, display.BLACK)

        text_height = font.get_height()
        border_vertical_size = (text_height >> 1) + (text_height >> 2)
        half_width = int(self.__heading_text__[360].get_size()[0] * 2.5)

        center_x = self.__center__[0]

        self.__heading_text_box_lines__ = [
            [center_x - half_width,
             self.compass_text_y - border_vertical_size],
            [center_x + half_width,
             self.compass_text_y - border_vertical_size],
            [center_x + half_width,
             self.compass_text_y + border_vertical_size],
            [center_x - half_width, self.compass_text_y + border_vertical_size]]

        self.__heading_strip__ = {}
        for heading in range(0, 181):
            self.__heading_strip__[heading] = int(
                self.pixels_per_degree_x * heading)

    def render(self, framebuffer, orientation):
        """
        Renders the current heading to the HUD.
        """

        self.task_timer.start()

        compass = int(orientation.compass_heading)
        if compass is None or compass > 360 or compass < 0:
            compass = '---'

        # Render a crude compass
        # Render a heading strip along the top

        center_x = self.__center__[0]

        heading = int(orientation.get_heading())
        for heading_strip in self.__heading_strip__:
            position_x = self.__heading_strip__[heading_strip]
            to_the_left = (heading - heading_strip)
            to_the_right = (heading + heading_strip)

            if to_the_left < 0:
                to_the_left += 360

            if to_the_right > 360:
                to_the_right -= 360

            if (to_the_left % 90) == 0:
                line_x_left = center_x - position_x
                pygame.draw.line(framebuffer, display.GREEN,
                                 [line_x_left, self.line_height], [line_x_left, 0], 2)

                self.__render_heading__(
                    framebuffer, to_the_left, line_x_left, self.heading_text_y)

            if to_the_left == to_the_right:
                continue

            if (to_the_right % 90) == 0:
                line_x_right = center_x + position_x
                pygame.draw.line(framebuffer, display.GREEN,
                                 [line_x_right, self.line_height], [line_x_right, 0], 2)

                self.__render_heading__(
                    framebuffer, to_the_right, line_x_right, self.heading_text_y)

        # Render the text that is showing our AHRS and GPS headings
        cover_old_rendering_spaces = "     "
        heading_text = "{0}{1} | {2}{0}".format(cover_old_rendering_spaces,
                                                compass, int(orientation.gps_heading))

        rendered_text = self.__font__.render(
            heading_text, True, display.GREEN, display.BLACK)
        text_width, text_height = rendered_text.get_size()

        framebuffer.blit(
            rendered_text, (center_x - (text_width >> 1), self.compass_text_y - (text_height >> 1)))

        pygame.draw.lines(framebuffer, display.GREEN, True,
                          self.__heading_text_box_lines__, 2)
        
        self.task_timer.stop()

    def __render_heading__(self, framebuffer, heading, position_x, position_y):
        """
        Renders the text with the results centered on the given
        position.
        """

        rendered_text = self.__heading_text__[heading]
        text_width, text_height = rendered_text.get_size()

        framebuffer.blit(
            rendered_text, (position_x - (text_width >> 1), position_y - (text_height >> 1)))

        return text_width, text_height


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
        self.__top_border__ = int(framebuffer_size[1] * 0.1)
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

    def pad_right(self, text, longest):
        delta = longest - len(text)

        padded_text = text

        for i in range(0, delta, 1):
            padded_text += ' '

        return padded_text

    def pad_left(self, text, longest):
        delta = longest - len(text)

        padded_text = ''

        for i in range(0, delta, 1):
            padded_text += ' '

        return padded_text + text

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
        compass = orientation.get_heading()
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
            [center_x - size, 0 + size],
            [center_x, 0],
            [center_x + size, 0 + size]
        ]

        return above_reticle, size

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
            [center_x - size, self.__height__ - size],
            [center_x, self.__height__],
            [center_x + size, self.__height__ - size]
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

    def __render_heading_bug__(self, framebuffer, identifier, center_x, reticle_lines, reticle_text_y_pos):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """


        pygame.draw.polygon(framebuffer, display.RED, reticle_lines)

        rendered_text = self.__font__.render(
            str(identifier), True, display.YELLOW)
        text_width, text_height = rendered_text.get_size()

        if reticle_text_y_pos < self.__center__[1]:
            text_y = reticle_text_y_pos
        else:
            text_y = reticle_text_y_pos - text_height

        framebuffer.blit(
            rendered_text, (center_x - (text_width >> 1), text_y))

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
        self.__top_border__ = int(self.__height__ * 0.1)
        self.__bottom_border__ = self.__height__ - self.__top_border__

    def __get_padded_traffic_reports__(self, traffic_reports, orientation):
        max_identifier_length = 0
        max_bearing_length = 0
        max_altitude_length = 0
        max_distance_length = 0
        pre_padded_text = []

        report_count = 0
        for traffic in traffic_reports:
            report_count += 1

            if report_count > self.__max_reports__:
                break

            identifier = str(traffic.get_identifer())
            altitude_delta = int(traffic.altitude - orientation.alt)
            distance_text = self.__get_distance_string__(traffic.distance)
            delta_sign = ''
            if altitude_delta > 0:
                delta_sign = '+'
            altitude_text = "{0}{1}'".format(delta_sign, altitude_delta)
            bearing_text = "{0:.0f}".format(traffic.bearing)

            identifier_length = len(identifier)
            bearing_length = len(bearing_text)
            altitude_length = len(altitude_text)
            distance_length = len(distance_text)

            if identifier_length > max_identifier_length:
                max_identifier_length = identifier_length

            if bearing_length > max_bearing_length:
                max_bearing_length = bearing_length

            if altitude_length > max_altitude_length:
                max_altitude_length = altitude_length

            if distance_length > max_distance_length:
                max_distance_length = distance_length

            pre_padded_text.append(
                [identifier, bearing_text, distance_text, altitude_text, traffic.iaco_address])

        out_padded_reports = []

        for report in pre_padded_text:
            identifier = report[0]
            bearing = report[1]
            distance_text = report[2]
            altitude = report[3]
            iaco = report[4]

            # if self.__show_list__:
            traffic_report = "{0} {1:3} {2} {3}".format(self.pad_right(str(identifier), max_identifier_length),
                                                        bearing,
                                                        self.pad_left(
                                                        distance_text, max_distance_length),
                                                        self.pad_left(altitude, max_altitude_length))
            out_padded_reports.append((iaco, traffic_report))

        return out_padded_reports

    def render(self, framebuffer, orientation):
        # Render a heading strip along the top

        self.task_timer.start()
        heading = orientation.get_heading()

        # Get the traffic, and bail out of we have none
        traffic_reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

        if traffic_reports is None:
            self.task_timer.stop()
            return

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__

        padded_traffic_reports = self.__get_padded_traffic_reports__(
            traffic_reports, orientation)

        for identifier, traffic_report in padded_traffic_reports:
            traffic_text_texture = self.__font__.render(
                traffic_report, True, display.WHITE, display.BLACK)

            framebuffer.blit(
                traffic_text_texture, (x_pos, y_pos))

            y_pos += self.__next_line_distance__

            traffic_report = AdsbTrafficClient.TRAFFIC_MANAGER.traffic[str(
                identifier)]

            # Now find where to draw the reticle....
            reticle_x, reticle_y = self.__get_traffic_projection__(
                orientation, traffic_report)

            # Render using the Above us bug
            target_bug_scale = 0.04

            bearing = (heading - traffic_report.bearing)
            if bearing < -180:
                bearing += 360

            if bearing > 180:
                bearing -= 180
            heading_bug_x = int(
                self.__center__[0] - (bearing * self.__pixels_per_degree_x__))

            is_onscreen_x = reticle_x >= 0 and reticle_x < self.__width__
            is_onscreen_y = reticle_y >= self.__top_border__ and reticle_y <= self.__bottom_border__
            is_top = reticle_y <= self.__center__[1] \
                or reticle_y >= self.__bottom_border__

            if is_onscreen_x and is_onscreen_y:
                continue

            # Only draw the ones that would not be on the screen
            if is_top:
                reticle, reticle_text_y_pos = self.get_above_reticle(
                    heading_bug_x, target_bug_scale)
            else:
                reticle, reticle_text_y_pos = self.get_below_reticle(
                    heading_bug_x, target_bug_scale)

            self.__render_heading_bug__(
                framebuffer, traffic_report.get_identifer(), heading_bug_x, reticle, reticle_text_y_pos)
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
        traffic_reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

        if traffic_reports is None:
            self.task_timer.stop()
            return

        for traffic in traffic_reports:
            identifier = traffic.get_identifer()

            # Find where to draw the reticle....
            reticle_x, reticle_y = self.__get_traffic_projection__(
                orientation, traffic)

            # Render using the Above us bug
            min_reticle_size = 0.02
            max_reticle_size = 0.1
            on_screen_reticle_scale = min_reticle_size # 0.05

            if traffic.distance < imperial_superclose:
                on_screen_reticle_scale = max_reticle_size
            if traffic.distance > (2 * feet_to_sm):
                on_screen_reticle_scale = min_reticle_size
            else:
                delta = traffic.distance - imperial_superclose
                scale_distance = (2.0 * feet_to_sm) - imperial_superclose
                ratio = delta / scale_distance

                reticle_range = max_reticle_size - min_reticle_size
                on_screen_reticle_scale = min_reticle_size + (ratio * reticle_range)

            reticle, reticle_size_px = self.get_onscreen_reticle(
                reticle_x, reticle_y, on_screen_reticle_scale)

            if reticle_y < self.__top_border__ or reticle_y > self.__bottom_border__:
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
                          display.RED, True, reticle_lines, 2)
        
        # Move the identifer text away from the reticle
        if center_y < self.__center__[1]:
            text_y = center_y + border_space
        else:
            text_y = center_y - border_space
    

        if identifier in TRAFFIC_TEXT_CACHE:
            texture, texture_size = TRAFFIC_TEXT_CACHE[identifier]
            text_width, text_height = texture_size
        else:
            texture = self.__font__.render(identifier, True, display.YELLOW, display.BLACK)
            text_width, text_height = texture.get_size()
            TRAFFIC_TEXT_CACHE[identifier] = texture, (text_width, text_height)

        self.__render_texture__(framebuffer, (center_x, center_y), texture, (text_width, text_height), roll)

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

