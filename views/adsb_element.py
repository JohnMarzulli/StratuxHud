import math

from common_utils import units
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.traffic import Traffic
from rendering import colors, drawing, text_renderer

from views.ahrs_element import AhrsElement, HudElement
from views.hud_elements import apply_declination


class AdsbElement(HudElement):
    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__roll_elements__ = {}
        self.__text_y_pos__ = self.__center_y__ - self.__font_half_height__
        self.__pixels_per_degree_y__ = pixels_per_degree_y
        self.__pixels_per_degree_x__ = self.__framebuffer_size__[0] / 360.0
        self.start_fade_threshold = (configuration.CONFIGURATION.max_minutes_before_removal * 60) / 2
        self.__lower_reticle_bottom_y__ = self.__bottom_border__ - self.__font_height__ - self.__font_half_height__ - (self.__thick_line_width__ << 2)

    def __get_distance_string__(
        self,
        distance: float,
        decimal_places: bool = True
    ) -> str:
        """
        Gets the distance string for display using the units
        from the configuration.

        Arguments:
            distance {float} -- The distance... straight from the GDL90 which means FEET

        Returns:
            string -- The distance in a handy string for display.
        """

        display_units = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)

        return units.get_converted_units_string(
            display_units,
            math.fabs(distance),
            decimal_places=decimal_places)

    def __get_traffic_projection__(
        self,
        orientation: AhrsData,
        traffic: Traffic
    ):
        """
        Attempts to figure out where the traffic reticle should be rendered.
        Returns value within screen space
        """

        # Assumes traffic.position_valid
        # TODO - Account for aircraft roll...

        altitude_delta = int(traffic.altitude - orientation.alt)
        slope = altitude_delta / traffic.distance if traffic.distance > 0 else 0.0
        vertical_degrees_to_target = math.degrees(math.atan(slope))
        vertical_degrees_to_target -= orientation.pitch

        # TODO - Double check ALL of this math...
        compass = orientation.get_onscreen_projection_heading()

        if isinstance(compass, str):
            return None, None

        horizontal_degrees_to_target = apply_declination(
            traffic.bearing) - compass

        screen_y = -vertical_degrees_to_target * self.__pixels_per_degree_y__
        screen_x = horizontal_degrees_to_target * self.__pixels_per_degree_y__

        return self.__center__[0] + screen_x, self.__center__[1] + screen_y

    def get_above_reticle(
        self,
        center_x: int,
        scale: float
    ):
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

    def get_below_reticle(
        self,
        center_x: int,
        scale: float
    ):
        """
        Generates the coordinates for a reticle indicating
        traffic is below us.

        Arguments:
            center_x {int} -- Center X screen position
            center_y {int} -- Center Y screen position
            scale {float} -- The scale of the reticle relative to the screen.
        """

        size = int(self.__height__ * scale)
        quarter_size = size >> 2
        left = center_x - quarter_size
        right = center_x + quarter_size
        top = self.__lower_reticle_bottom_y__ - size

        below_reticle = [
            [left, top],
            [center_x, self.__lower_reticle_bottom_y__],
            [right, top]]

        # self.__height__ - size - bug_vertical_offset
        return below_reticle, below_reticle[2][1]

    def __get_additional_target_text__(
        self,
        traffic_report: Traffic,
        orientation: AhrsData
    ):
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
            int(apply_declination(traffic_report.bearing)))

        return [bearing_text, distance_text, altitude_text]

    def __render_info_card__(
        self,
        framebuffer,
        identifier_text: str,
        additional_info_text: str,
        center_x: int,
        time_since_last_report: float = 0.0
    ):
        """
        Renders a targetting reticle on the screen.
        Assumes the X/Y projection has already been performed.
        """

        card_color = self.__get_card_color__(time_since_last_report)

        # Render all of the textures and then
        # find which one is the widest.
        all_text = [identifier_text] + additional_info_text
        all_textures_and_sizes = [text_renderer.get_or_create_text_texture(
            self.__font__,
            text,
            colors.BLACK,
            card_color) for text in all_text]

        texture_widths = [texture[2][0] for texture in all_textures_and_sizes]

        widest_texture = max(texture_widths)
        text_height = all_textures_and_sizes[0][2][1]

        info_spacing = 1.2
        texture_height = int(
            (len(all_textures_and_sizes) * info_spacing) * text_height)

        info_position_y = ((self.__height__ >> 1) - (texture_height >> 1) - text_height)

        edge_left = (center_x - (widest_texture >> 1))
        edge_right = (center_x + (widest_texture >> 1))

        if edge_left < 0:
            edge_right += math.fabs(edge_left)
            edge_left = 0

        if edge_right > self.__framebuffer_size__[0]:
            diff = edge_right - self.__framebuffer_size__[0]
            edge_left -= diff
            edge_right = self.__framebuffer_size__[0]

        fill_top_left = [edge_left - self.__line_width__, info_position_y - self.__line_width__]
        fill_top_right = [edge_right + self.__line_width__, fill_top_left[1]]
        fill_bottom_right = [
            fill_top_right[0],
            info_position_y + self.__line_width__ + int((len(additional_info_text) + 1) * info_spacing * text_height)]
        fill_bottom_left = [fill_top_left[0], fill_bottom_right[1]]

        drawing.renderer.polygon(
            framebuffer,
            card_color,
            [fill_top_left, fill_top_right, fill_bottom_right, fill_bottom_left],
            False)

        drawing.renderer.segments(
            framebuffer,
            colors.BLACK,
            True,
            [fill_top_left, fill_top_right, fill_bottom_right, fill_bottom_left],
            int(self.__line_width__ * 1.5))

        self.__render_info_text__(
            all_textures_and_sizes,
            center_x,
            framebuffer,
            info_position_y,
            info_spacing)

    def __get_card_color__(
        self,
        time_since_last_report: float
    ):
        """
        Gets the color the card should be based on how long it has been
        since the traffic has had a report.

        Arguments:
            time_since_last_report {float} -- The number of seconds since the last traffic report.

        Returns:
            float[] -- The RGB tuple/array of the color the target card should be.
        """

        try:
            card_color = colors.YELLOW

            if time_since_last_report > self.start_fade_threshold:
                max_distance = (configuration.CONFIGURATION.max_minutes_before_removal * 60.0) - self.start_fade_threshold
                proportion = (time_since_last_report - self.start_fade_threshold) / max_distance

                card_color = colors.get_color_mix(
                    colors.YELLOW,
                    colors.BLACK,
                    proportion)

            return card_color
        except:
            return colors.YELLOW

    def __render_info_text__(
        self,
        additional_info_textures,
        center_x: int,
        framebuffer,
        info_position_y: int,
        info_spacing
    ):
        for key, info_texture, size in additional_info_textures:
            width_x, width_y = size
            half_width = width_x >> 1
            x_pos = center_x - half_width

            if center_x <= half_width:  # half_width:
                x_pos = 0  # half_width

            if (center_x + half_width) >= self.__width__:
                x_pos = self.__width__ - width_x

            try:
                text_renderer.render_cached_texture(
                    framebuffer,
                    key,
                    [x_pos, info_position_y])
            except:
                pass

            info_position_y += int(width_y * info_spacing)

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        super(AhrsElement, self).render(framebuffer, orientation)
