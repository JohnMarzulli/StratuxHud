"""
View that shows the list of nearby traffic
"""

from typing import List

import pygame

from data_sources.ahrs_data import AhrsData
from rendering import colors
from views.text_line import TextLine
from views.adsb_element import AdsbElement


class PaginatedTextElement(AdsbElement):
    """
    Provides a basis for text views that have a
    page up and page down functionality.

    Implements a page/scroll view.
    """

    def uses_ahrs(self) -> bool:
        return False

    def handle_events(self, unhandled_events) -> list:
        """
        Handle up/down events so scrolling can be implemented.

        Args:
            unhandled_events (_type_): Any events that have not yet been handeled.

        Returns:
            list: A list of events that were not handled by this code.
        """

        remaining_unhandled_events = []

        for event in unhandled_events:
            if event.type != pygame.KEYUP:
                continue

            if event.key in [pygame.K_UP, pygame.K_KP8]:
                self.__page__ -= 1
            elif event.key in [pygame.K_DOWN, pygame.K_KP2]:
                self.__page__ += 1
            else:
                remaining_unhandled_events.append(event)

        return remaining_unhandled_events

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False,
    ):
        super().__init__(
            degrees_of_pitch,
            pixels_per_degree_y,
            font,
            framebuffer_size,
            reduced_visuals,
        )

        self.__page__ = 0
        self.__listing_text_start_y__ = int(self.__font__.get_height())
        self.__listing_text_start_x__ = int(self.__framebuffer_size__[0] * 0.01)
        self.__next_line_distance__ = int(font.get_height())
        self.__font_scale__ = 0.6

        self.__max_screen_lines__ = (
            int(
                (self.__height__ - self.__listing_text_start_y__)
                / (self.__next_line_distance__ * self.__font_scale__)
            )
            - 4
        )

    def __get_text_pages__(self, orientation: AhrsData) -> List[List[TextLine]]:
        return []

    def render(self, framebuffer, orientation: AhrsData):
        lines_by_page = self.__get_text_pages__(orientation)
        page_count = len(lines_by_page)

        self.__page__ = min(page_count - 1, self.__page__)
        self.__page__ = max(self.__page__, 0)

        # Render a list of traffic that we have positions
        # for, along with the tail number

        y_pos = self.__listing_text_start_y__
        x_pos = self.__listing_text_start_x__
        line_increment = int(self.__next_line_distance__ * (self.__font_scale__ * 1.2))

        if page_count > 0:
            text_page = lines_by_page[self.__page__]

            for report_line in text_page:
                self.__render_text__(
                    framebuffer,
                    report_line.text,
                    [x_pos, y_pos],
                    report_line.color,
                    self.__font_scale__,
                )

                y_pos += line_increment

        self.__render_text__(
            framebuffer,
            f"Pg: {self.__page__ + 1} / {page_count}",
            [
                self.__left_border__,
                (self.__bottom_border__ - (self.__font_height__ << 1))
                + self.__font_height__,
            ],
            colors.YELLOW,
            0.5,
        )

    def __get_max_line_length__(self) -> int:
        report_start_x = self.__listing_text_start_x__ + (
            self.__font_height__ * self.__font_scale__ * 4
        )

        return int(
            (
                (((self.__center_x__ * 2) - report_start_x) / self.__font_scale__)
                / (self.__font_height__ / 2)
            )
            * 0.9
        )


if __name__ == "__main__":
    from views.hud_elements import run_hud_element

    run_hud_element(PaginatedTextElement)
