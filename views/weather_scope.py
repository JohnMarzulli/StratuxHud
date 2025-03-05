"""
View element for a weather "radar" that looks from the top downwards.
"""

import datetime
from typing import Tuple

import pygame

from common_utils import geo_math
from common_utils.task_timer import TaskProfiler
from common_utils.tasks import IntermittentTask
from configuration import configuration
from core_services.scope_range import ScopeRange
from core_services.zoom_manager import ZoomManager
from data_sources.ahrs_data import AhrsData
from data_sources.airports import AirportClient
from data_sources.nexrad import NexradClient, ReflectivityBlock
from rendering import colors, drawing
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

            if event.key in [pygame.K_UP, pygame.K_KP8]:
                self.__zoom_manager__.manual_zoom_out()
            elif event.key in [pygame.K_DOWN, pygame.K_KP2]:
                self.__zoom_manager__.manual_zoom_in()
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
        self.__zoom_manager__: ZoomManager = ZoomManager()
        self.__zoom_manager__.manual_zoom_out()
        self.__zoom_manager__.manual_zoom_out()
        self.__zoom_manager__.manual_zoom_out()
        self.__failed_bin_counts__ = 0
        self.__missing_bin_counts__ = 0
        self.__successful_bin_counts__ = 0
        self.__nearby_blocks_count__ = 0
        self.__total_blocks_count__ = 0

        self.__log_bin_stats_task__ = IntermittentTask(
            "Render Failed Weather Counts", 15.0, self.__log_bin_counts__, None
        )

    def __render_reflectivity__(
        self,
        framebuffer: pygame.Surface,
        orientation: AhrsData,
    ):
        self.__log_bin_stats_task__.run()
        self.__successful_bin_counts__ = 0
        self.__failed_bin_counts__ = 0
        self.__missing_bin_counts__ = 0

        scope_range = self.__zoom_manager__.get_current_zoom()

        text_y_pos = self.__bottom_border__ - (self.__font_height__ << 1)
        nearby_position = [
            self.__left_border__,
            text_y_pos + (self.__font_height__ >> 1),
        ]
        total_position = [self.__left_border__, text_y_pos + self.__font_height__]

        nexrad_blocks = []

        if not (
            orientation.position is None
            or orientation.position[0] is None
            or orientation.position[1] is None
        ):
            current_heading = orientation.get_onscreen_gps_heading()

            if not (current_heading is None or isinstance(current_heading, str)):
                nexrad_blocks = self.__get_nexrad_blocks__(
                    orientation.position, scope_range.max_ring_range
                )

        [
            self.__render_block__(
                framebuffer, orientation, current_heading, scope_range, block
            )
            for block in nexrad_blocks
        ]

        self.__nearby_blocks_count__ = len(nexrad_blocks)

        self.__render_text__(
            framebuffer,
            f"Nearby: {self.__nearby_blocks_count__}",
            nearby_position,
            colors.YELLOW,
            0.5,
        )

        self.__total_blocks_count__ = len(NexradClient.REFLECTIVITY.keys())

        self.__render_text__(
            framebuffer,
            f"Total: {self.__total_blocks_count__}",
            total_position,
            colors.YELLOW,
            0.5,
        )

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
        orientation: AhrsData,
        current_heading,
        scope_range: ScopeRange,
        block,
    ):
        lat_step = (block.north_western[0] - block.south_western[0]) / 4.0
        lon_step = (block.north_eastern[1] - block.north_western[1]) / 32.0

        [
            self.__render_bins__(
                framebuffer,
                orientation,
                current_heading,
                scope_range,
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
        scope_range: ScopeRange,
        lat_index,
        lon_index,
        lat_step,
        lon_step,
        block: ReflectivityBlock,
    ):
        try:
            if len(block.reflectivity) <= lat_index:
                self.__missing_bin_counts__ += 1
                return

            if len(block.reflectivity[lat_index]) <= lon_index:
                self.__missing_bin_counts__ += 1
                return

            reflectivity = block.reflectivity[lat_index][lon_index]

            if reflectivity == 0:
                self.__successful_bin_counts__ += 1
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

            center_lat = (n_lat + s_lat) / 2.0
            center_lon = (w_lon + e_lon) / 2.0

            distance = geo_math.get_distance(
                orientation.position, [center_lat, center_lon]
            )

            if distance > scope_range.max_ring_range:
                return

            nw_pixel = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, nw
            )
            ne_pixel = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, ne
            )
            se_pixel = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, se
            )
            sw_pixel = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, sw
            )

            drawing.renderer.polygon(
                framebuffer,
                color,
                [nw_pixel, ne_pixel, se_pixel, sw_pixel],
                False,
            )
        except Exception as ex:
            self.__failed_bin_counts__ += 1

            return

        self.__successful_bin_counts__ += 1

    def render(self, framebuffer: pygame.Surface, orientation: AhrsData):
        """
        Renders all of the on-screen reticles  for nearby traffic.

        Arguments:
            framebuffer {pygame.Surface} -- The render target.
            orientation {Orientation} -- The orientation of the plane the HUD is in.
        """

        scope_range = self.__zoom_manager__.get_current_zoom()

        with TaskProfiler(
            "views.weather_top_view_scope.WeatherTopViewScope.render_reflectivity"
        ):
            self.__render_reflectivity__(framebuffer, orientation)

        with TaskProfiler(
            "views.weather_top_view_scope.WeatherTopViewScope.render_ring"
        ):
            self.__render_ownship__(framebuffer)
            self.__draw_distance_rings__(framebuffer, scope_range)
            self.__draw_all_compass_headings__(framebuffer, orientation, scope_range)

        with TaskProfiler(
            "views.weather_top_view_scope.WeatherTopViewScope.render_airports"
        ):
            self.__draw_airports__(framebuffer, orientation, scope_range)

    def __log_bin_counts__(self):
        print(f"Missing bins:{self.__missing_bin_counts__}")
        print(f"Failed bins:{self.__failed_bin_counts__}")
        print(f"Passed bins:{self.__successful_bin_counts__}")
        print(f"Nearby blocks:{self.__nearby_blocks_count__}")
        print(f"Total blocks:{self.__total_blocks_count__}")


if __name__ == "__main__":
    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements
    import json

    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    test_data_files = [
        "../test_data/challenging_reflectivity.json",
        "../test_data/seatac_nye_2024_reflectivity.json",
    ]

    for test_data_file in test_data_files:
        full_file_path = configuration.get_absolute_file_path(test_data_file)

        with open(full_file_path) as json_test_data_file:
            json_config_text = json_test_data_file.read()
            test_data_json = json.loads(json_config_text)
            nexrad_client.inject(test_data_json)

    AirportClient.inject_flight_rules(
        {
            "KPLU": "VFR",
            "K4S2": "MVFR",
            "KS39": "VFR",
            "KBVS": "VFR",
            "KSZT": "VFR",
            "K0S9": "VFR",
            "K6S2": "IFR",
            "KS33": "VFR",
            "K63S": "MVFR",
            "KRNT": "IFR",
            "KSEA": "VFR",
            "KBFI": "MVFR",
            "1WA6": "LIFR",
        }
    )

    run_hud_elements([WeatherTopViewScope, CompassAndHeadingTopElement, Groundspeed])
