"""
Base class for AHRS view elements.
"""

import pygame
from data_sources.data_cache import HudDataCache
from rendering import colors


class HudElement(object):
    def __init__(
        self,
        font,
        framebuffer_size
    ) -> None:
        super().__init__()

        border_margin = 0.01

        self.__font__ = font

        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        self.__width__ = framebuffer_size[0]
        self.__height__ = framebuffer_size[1]

        self.__right_border__ = int((1.0 - border_margin)
                                    * framebuffer_size[0])
        self.__left_border__ = int(framebuffer_size[0] * border_margin)

        self.__top_border__ = int(self.__height__ * border_margin)
        self.__bottom_border__ = self.__height__ - self.__top_border__

        self.__center_x__ = framebuffer_size[0] >> 1
        self.__center_y__ = framebuffer_size[1] >> 1

        self.__font_height__ = int(font.get_height())
        self.__font_half_height__ = int(self.__font_height__ >> 1)

        self.__line_width__ = int((self.__height__ / 120) + 0.5)

    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

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
        texture, size = HudDataCache.get_cached_text_texture(
            text,
            self.__font__,
            color,
            colors.BLACK,
            True,
            False)

        scaled_size = [int(size[0] * scale), int(size[1] * scale)]

        texture = pygame.transform.smoothscale(
            texture,
            scaled_size)

        framebuffer.blit(
            texture,
            position)

        return scaled_size

    def __render_horizontal_centered_text__(
        self,
        framebuffer,
        text: str,
        position: list,
        color: list,
        scale: float = 1.0
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
        texture, size = HudDataCache.get_cached_text_texture(
            text,
            self.__font__,
            color,
            colors.BLACK,
            True,
            False)

        scaled_size = [int(size[0] * scale), int(size[1] * scale)]

        x_adjustment = scaled_size[0] >> 1

        texture = pygame.transform.smoothscale(
            texture,
            scaled_size)

        framebuffer.blit(
            texture,
            [position[0] - x_adjustment, position[1]])

        return scaled_size

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
        texture, size = HudDataCache.get_cached_text_texture(
            text,
            self.__font__,
            color,
            colors.BLACK,
            True,
            False)

        scaled_size = [int(size[0] * scale), int(size[1] * scale)]

        texture = pygame.transform.smoothscale(
            texture,
            scaled_size)

        framebuffer.blit(
            texture,
            [position[0] - scaled_size[0], position[1]])

        return scaled_size

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

            longest_x = info_size[0] if info_size[0] > longest_x else longest_x

        main_package = scale_text_color_list[0]
        self.__render_text_right_justified__(
            framebuffer,
            main_package[1],
            [current_position[0] - longest_x, starting_position[1]],
            main_package[2],
            main_package[0])


class AhrsElement(HudElement):
    GPS_UNAVAILABLE_TEXT = "NO GPS"
    INOPERATIVE_TEXT = "INOP"

    def __init__(
        self,
        font,
        framebuffer_size
    ) -> None:
        super().__init__(font, framebuffer_size)

    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True
