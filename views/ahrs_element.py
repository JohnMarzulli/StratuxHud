"""
Base class for AHRS view elements.
"""

from data_sources.ahrs_data import AhrsData
from common_utils import tasks, units
from configuration import configuration
from rendering import colors, display, text_renderer


def __get_default_text_background_color__() -> list:
    return colors.BLACK if display.IS_OPENGL else None


class HudElement(object):
    def __init__(
        self,
        font,
        framebuffer_size: list,
        reduced_visuals: bool = False
    ) -> None:
        super().__init__()

        border_margin = 0.01

        self.__font__ = font

        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        self.__width__ = framebuffer_size[0]
        self.__height__ = framebuffer_size[1]

        self.__right_border__ = int((1.0 - border_margin) * framebuffer_size[0])
        self.__left_border__ = int(framebuffer_size[0] * border_margin)

        self.__top_border__ = int(self.__height__ * border_margin)
        self.__bottom_border__ = self.__height__ - self.__top_border__

        self.__center_x__ = framebuffer_size[0] >> 1
        self.__center_y__ = framebuffer_size[1] >> 1

        self.__font_height__ = int(font.get_height())
        self.__font_half_height__ = int(self.__font_height__ >> 1)

        self.__line_width__ = max(1, int((self.__width__ * 0.005) + 0.5))
        self.__thin_line_width__ = self.__line_width__ >> 1
        self.__thick_line_width__ = self.__line_width__ >> 1

        self.__reduced_visuals__ = reduced_visuals

        self.__speed_units__ = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)

        self.__update_units_task__ = tasks.IntermittentTask(
            "update_speed_units",
            1.0,
            self.__update_speed_units__)

    def __get_speed_string__(
        self,
        speed
    ) -> str:
        """
        Gets the string to display for the speed. Uses the units configured by the user.

        Arguments:
            speed {number} -- The raw speed from the sensor.

        Returns:
            string -- A string with the speed and the correct units.
        """

        return units.get_converted_units_string(
            self.__speed_units__,
            speed,
            units.SPEED)

    def __update_speed_units__(
        self
    ) -> None:
        self.__speed_units__ = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)

    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __get_skid_amount__(
        self,
        orientation: AhrsData
    ) -> float:
        """
        Get the normalized amount of skid. Makes sure that that
        values between Stratux and Dynon 180 are comparable.

        Args:
            orientation (AhrsData): The current, combined AHRS data.

        Returns:
            float: The amount of skid.
        """
        if orientation.slip_skid is None or isinstance(orientation.slip_skid, str):
            return 0.0

        if orientation.is_avionics_source:
            return float(orientation.slip_skid * 3.0)

        skid_normalized = -(orientation.slip_skid / 10.0)

        return float(skid_normalized)

    def __render_text__(
        self,
        framebuffer,
        text: str,
        position: list,
        color: list,
        scale: float = 1.0
    ) -> list:
        """
        Renders the given text at the position, color, and scale given.

        Args:
            framebuffer: The surface to render to.
            text (str): The text to render.
            position (list): The upper-left hand corner position to render the text at
            color (list): The foreground color of the text.
            scale (float): Any size adjustment (proportion) to adjust the render by.

        Returns:
            list: The size of the rendered text.
        """

        return text_renderer.render_text(
            framebuffer,
            self.__font__,
            text,
            position,
            color,
            colors.BLACK,
            not self.__reduced_visuals__,
            scale)

    def __render_horizontal_centered_text__(
        self,
        framebuffer,
        text: str,
        position: list,
        color: list,
        bg_color: list = __get_default_text_background_color__(),
        scale: float = 1.0,
        use_alpha: bool = True
    ) -> list:
        """
        Renders the given text so that the given X position is at the center, with
        the given color, and scale given.

        Args:
            framebuffer: The surface to render to.
            text (str): The text to render.
            position (list): The center-X and starting Y position to render the text at
            color (list): The foreground color of the text.
            scale (float): Any size adjustment (proportion) to adjust the render by.

        Returns:
            list: The size of the rendered text.
        """

        key, texture, size = text_renderer.get_or_create_text_texture(
            self.__font__,
            text,
            color,
            bg_color,
            use_alpha,
            scale)

        x_adjustment = size[0] >> 1

        text_renderer.render_cached_texture(
            framebuffer,
            key,
            [position[0] - x_adjustment, position[1]])

        return size

    def __render_centered_text__(
        self,
        framebuffer,
        text: str,
        position: list,
        color: list,
        bg_color: list = __get_default_text_background_color__(),
        scale: float = 1.0,
        rotation: float = 0.0,
        use_alpha: bool = True
    ) -> list:
        """
        Renders the given text so that the given X position is at the center, with
        the given color, and scale given.

        Args:
            framebuffer: The surface to render to.
            text (str): The text to render.
            position (list): The center-X and starting Y position to render the text at
            color (list): The foreground color of the text.
            color (list): Any background color of the text. May be null for Alpha
            scale (float): Any size adjustment (proportion) to adjust the render by.
            scale (float): Any rotation adjustment (proportion) to adjust the text by.

        Returns:
            list: The size of the rendered text.
        """

        use_alpha |= bg_color is None

        key, texture, size = text_renderer.get_or_create_text_texture(
            self.__font__,
            text,
            color,
            bg_color,
            use_alpha,
            scale,
            rotation)

        new_x = position[0] - (size[0] >> 1)
        new_y = position[1] - (size[1] >> 1)

        text_renderer.render_cached_texture(
            framebuffer,
            key,
            [new_x, new_y])

        return size

    def __render_text_right_justified__(
        self,
        framebuffer,
        text: str,
        position: list,
        color: list,
        scale: float = 1.0
    ) -> list:
        """
        Renders the given text at the position, color, and scale given.

        Args:
            framebuffer: The surface to render to.
            text (str): The text to render.
            position (list): The upper-right hand corner position to render the text at
            color (list): The foreground color of the text.
            scale (float): Any size adjustment (proportion) to adjust the render by.

        Returns:
            list: The size of the rendered text.
        """

        key, texture, size = text_renderer.get_or_create_text_texture(
            self.__font__,
            text,
            color,
            __get_default_text_background_color__(),
            True,
            scale)

        text_renderer.render_cached_texture(
            framebuffer,
            key,
            [position[0] - size[0], position[1]])

        return size

    def __render_text_with_stacked_annotations__(
        self,
        framebuffer,
        starting_position: list,
        scale_text_color_list: list
    ):
        """
        Renders text such that the main text is left most,
        and any additional text packages are rendered to its
        immediate right, but stacked on top of each other.
        The position of the stacked text is based on the width
        of the main text.
        The first annotation is veritically positioned at the given y,
        with each additional annotation being moved down by the vertical size
        of the previous annotation.

        This version is LEFT JUSTIFIED

        Args:
            framebuffer: The surface to render the text to.
            starting_position (list): The starting upper-left hand position to render the text at.
            scale_text_color_list (list): A list of text description packages.
        """

        # Take the main info and render it on the left at the given y
        # then take [1], render at the new X and given y
        # then take[2], render at same X as [1], moved down the split vertical

        main_package = scale_text_color_list[0]
        main_size = self.__render_text__(
            framebuffer,
            main_package[1],
            starting_position,
            main_package[2],
            main_package[0])

        current_position = [starting_position[0] + main_size[0],
                            starting_position[1]]

        for (scale, text, color) in scale_text_color_list[1:]:
            info_size = self.__render_text__(
                framebuffer,
                text,
                current_position,
                color,
                scale)

            current_position[1] += info_size[1]

    def __render_text_with_stacked_annotations_right_justified__(
        self,
        framebuffer,
        starting_position: list,
        scale_text_color_list: list
    ):
        """
        Renders text such that the main text is left most,
        and any additional text packages are rendered to its
        immediate right, but stacked on top of each other.
        The position of the stacked text is based on the width
        of the main text.
        The first annotation is veritically positioned at the given y,
        with each additional annotation being moved down by the vertical size
        of the previous annotation.

        This version does it such that the text is right
        justified.

        Args:
            framebuffer: The surface to render the text to.
            starting_position (list): The starting upper-right hand position to render the text at.
            scale_text_color_list (list): A list of text description packages.
        """

        # Take the main info and render it on the left at the given y
        # then take [1], render at the new X and given y
        # then take[2], render at same X as [1], moved down the split vertical

        current_position = [starting_position[0], starting_position[1]]
        longest_x = 0

        for (scale, text, color) in scale_text_color_list[1:]:
            info_size = self.__render_text_right_justified__(
                framebuffer,
                text,
                current_position,
                color,
                scale)

            current_position[1] += info_size[1]

            longest_x = max(info_size[0], longest_x)

        main_package = scale_text_color_list[0]
        self.__render_text_right_justified__(
            framebuffer,
            main_package[1],
            [current_position[0] - longest_x, starting_position[1]],
            main_package[2],
            main_package[0])

    def render(
        self,
        framebuffer,
        orientation
    ):
        self.__update_units_task__.run()


class AhrsElement(HudElement):
    """
    Common definition for view elements that use AHRS.
    """

    GPS_UNAVAILABLE_TEXT = "NO GPS"
    INOPERATIVE_TEXT = "INOP"

    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True
