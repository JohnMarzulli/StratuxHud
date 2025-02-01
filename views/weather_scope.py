"""
View element for a weather "radar" that looks from the top downwards.
"""

import datetime
from typing import Tuple

import pygame

from common_utils.task_timer import TaskProfiler
from configuration import configuration
from core_services import zoom_tracker
from data_sources.ahrs_data import AhrsData
from data_sources.nexrad import NexradClient
from rendering import drawing
from views.top_down_scope import TopDownScope


class WeatherTopViewScope(TopDownScope):
    """
    A view element for the HUD that draws a radar style scope
    showing where traffic is relative to our current position.
    """

    BIN_ROWS = [0, 1, 2, 3]
    BIN_COLUMNS = list(range(32))

    def handle_events(self, unhandled_events) -> list:

        remaining_unhandled_events = []

        for event in unhandled_events:
            if event.type != pygame.KEYUP:
                continue

            if event.key in [pygame.K_UP]:
                self.__zoom_out__()
            elif event.key in [pygame.K_DOWN]:
                self.__zoom_in__()
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

        self.__time_of_last_block_fetch__ = datetime.datetime.now(datetime.timezone.utc)
        self.__nexrad_cache__ = None
        self.__zoom_levels__ = [(10, 5), (15, 5), (20, 10), (50, 25), [100, 25]]
        self.__zoom_index__ = len(self.__zoom_levels__) - 2

    def __zoom_in__(self):
        self.__zoom_index__ -= 1
        self.__zoom_index__ = max(self.__zoom_index__, 0)

    def __zoom_out__(self):
        self.__zoom_index__ += 1
        self.__zoom_index__ = min(self.__zoom_index__, len(self.__zoom_levels__) - 1)

    def __render_reflectivity__(
        self,
        framebuffer: pygame.Surface,
        scope_range: Tuple[int, int],
        orientation: AhrsData,
    ):
        max_distance = scope_range[0]

        if (
            orientation.position is None
            or orientation.position[0] is None
            or orientation.position[1] is None
        ):
            return

        current_heading = orientation.get_onscreen_gps_heading()

        if current_heading is None or isinstance(current_heading, str):
            return

        nexrad_blocks = self.__get_nexrad_blocks__(orientation.position, max_distance)

        [
            self.__render_block__(
                framebuffer, orientation, current_heading, max_distance, block
            )
            for block in nexrad_blocks
        ]

    def __get_nexrad_blocks__(self, position, max_distance: float) -> list:
        now = datetime.datetime.now(datetime.timezone.utc)
        seconds_since = (now - self.__time_of_last_block_fetch__).seconds

        if self.__nexrad_cache__ != None and seconds_since < 15:
            return self.__nexrad_cache__

        self.__nexrad_cache__ = NexradClient.get_nexrad_in_range(position, max_distance)
        self.__time_of_last_block_fetch__ = now

        return self.__nexrad_cache__

    def __render_block__(
        self,
        framebuffer,
        orientation,
        current_heading,
        max_distance,
        block,
    ):
        lat_step = (block.north_western[0] - block.south_western[0]) / 4.0
        lon_step = (block.north_eastern[1] - block.north_western[1]) / 32.0

        [
            self.__render_bins__(
                framebuffer,
                orientation,
                current_heading,
                max_distance,
                lat_index,
                lon_index,
                lat_step,
                lon_step,
                block,
            )
            for lat_index in WeatherTopViewScope.BIN_ROWS
            for lon_index in WeatherTopViewScope.BIN_COLUMNS
        ]

    def __render_bins__(
        self,
        framebuffer,
        orientation,
        current_heading,
        max_distance,
        lat_index,
        lon_index,
        lat_step,
        lon_step,
        block,
    ):
        reflectivity = block.reflectivity[lat_index][lon_index]

        if reflectivity == 0:
            return

        color = NexradClient.reflectivity_to_rgb(reflectivity)

        n_lat = block.north_western[0] - (lat_index * lat_step)
        s_lat = n_lat - lat_step
        w_lon = block.north_western[1] + (lon_index * lon_step)
        e_lon = w_lon + lon_step

        nw = [n_lat, w_lon]
        ne = [n_lat, e_lon]
        se = [s_lat, e_lon]
        sw = [s_lat, w_lon]

        nw_pixel = self.__get_screen_coordinates__(
            orientation, current_heading, max_distance, nw
        )
        ne_pixel = self.__get_screen_coordinates__(
            orientation, current_heading, max_distance, ne
        )
        se_pixel = self.__get_screen_coordinates__(
            orientation, current_heading, max_distance, se
        )
        sw_pixel = self.__get_screen_coordinates__(
            orientation, current_heading, max_distance, sw
        )

        drawing.renderer.polygon(
            framebuffer,
            color,
            [nw_pixel, ne_pixel, se_pixel, sw_pixel],
            False,
        )

    def render(self, framebuffer: pygame.Surface, orientation: AhrsData):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {pygame.Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        scope_range = self.__zoom_levels__[self.__zoom_index__]

        with TaskProfiler(
            "views.weather_top_view_scope.WeatherTopViewScope.render_reflectivity"
        ):
            self.__render_reflectivity__(framebuffer, scope_range, orientation)

        with TaskProfiler("views.weather_top_view_scope.WeatherTopViewScope.render"):
            self.__render_ownship__(framebuffer)

            self.__draw_distance_rings__(framebuffer, scope_range)

            self.__draw_all_compass_headings__(framebuffer, orientation, scope_range[0])


if __name__ == "__main__":
    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements

    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    run_hud_elements([WeatherTopViewScope, CompassAndHeadingTopElement, Groundspeed])
