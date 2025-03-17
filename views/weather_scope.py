"""
View element for a weather "radar" that looks from the top downwards.
"""

import datetime
from typing import List

import pygame

from common_utils import geo_math
from common_utils.task_timer import TaskProfiler
from common_utils.tasks import IntermittentTask
from configuration import configuration
from core_services.scope_range import ScopeRange
from core_services.zoom_manager import ZoomManager
from data_sources.ahrs_data import AhrsData
from data_sources.airports import load_example_airports, load_example_flight_rules
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
        self.__nexrad_cache__: List[ReflectivityBlock] = None
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

        if self.__cluter_visuals__:
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

    def __get_nexrad_blocks__(
        self, position, max_distance: float
    ) -> List[ReflectivityBlock]:
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
        block: ReflectivityBlock,
    ):
        [
            self.__render_bin_row__(
                framebuffer, orientation, current_heading, scope_range, block, lat_index
            )
            for lat_index in WeatherTopViewScope.BIN_ROWS
        ]

    def __render_bin_row__(
        self,
        framebuffer,
        orientation: AhrsData,
        current_heading,
        scope_range: ScopeRange,
        block: ReflectivityBlock,
        lat_index,
    ):
        if len(block.reflectivity) <= lat_index:
            self.__missing_bin_counts__ += len(WeatherTopViewScope.BIN_COLUMNS)
            return

        n_edge_lat = block.north_western[0] - (lat_index * block.lat_step)
        s_edge_lat = n_edge_lat - block.lat_step

        lon_start_index: int = 0
        rle = block.reflectivity[lat_index]

        for run in rle:
            try:
                run_length: int = run["runLength"]
                reflectivity: int = run["reflectivity"]

                self.__render_bin_lon_range__(
                    framebuffer,
                    orientation,
                    current_heading,
                    scope_range,
                    lon_start_index,
                    lon_start_index + (run_length - 1),
                    n_edge_lat,
                    s_edge_lat,
                    block,
                    reflectivity,
                )
                lon_start_index += run_length
            except:
                pass

    def __render_bin_lon_range__(
        self,
        framebuffer,
        orientation,
        current_heading,
        scope_range: ScopeRange,
        lon_start_index,
        lon_end_index,
        n_edge_lat,
        s_edge_lat,
        block: ReflectivityBlock,
        reflectivity,
    ):
        if lon_end_index < lon_start_index:
            print(f"Invalid lon range: {lon_start_index} to {lon_end_index}")

        try:
            if reflectivity == 0:
                self.__successful_bin_counts__ += lon_end_index - lon_start_index
                return

            color = NexradClient.reflectivity_to_rgb(reflectivity)

            w_edge_lon = block.north_western[1] + (lon_start_index * block.lon_step)
            e_edge_lon = (
                block.north_western[1]
                + (lon_end_index * block.lon_step)
                + block.lon_step
            )

            nw = [n_edge_lat, w_edge_lon]
            ne = [n_edge_lat, e_edge_lon]
            se = [s_edge_lat, e_edge_lon]
            sw = [s_edge_lat, w_edge_lon]

            center_lat = (n_edge_lat + s_edge_lat) / 2.0
            center_lon = (w_edge_lon + e_edge_lon) / 2.0
            distance = geo_math.get_distance(
                orientation.position, [center_lat, center_lon]
            )

            if distance > scope_range.max_ring_range:
                return

            nw_corner = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, nw
            )
            ne_corner = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, ne
            )
            se_corner = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, se
            )
            sw_corner = self.__get_screen_coordinates__(
                orientation, current_heading, scope_range, sw
            )

            drawing.renderer.polygon(
                framebuffer,
                color,
                [nw_corner, ne_corner, se_corner, sw_corner],
                False,
            )
        except Exception as ex:
            self.__failed_bin_counts__ += 1

            return

        self.__successful_bin_counts__ += lon_end_index - lon_start_index

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
            try:
                self.__render_reflectivity__(framebuffer, orientation)
            except:
                pass

        with TaskProfiler(
            "views.weather_top_view_scope.WeatherTopViewScope.render_ring"
        ):
            self.__render_ownship__(framebuffer)
            self.__draw_distance_rings__(framebuffer, scope_range, colors.WHITE)
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
    import json

    from views.compass_and_heading_top_element import CompassAndHeadingTopElement
    from views.groundspeed import Groundspeed
    from views.hud_elements import run_hud_elements

    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    test_data_files = [
        "../test_data/faa_sample_reflectivity.json",
        "../test_data/reflectivity_response.json",
        "../test_data/2025-03-14_incomplete_bins.json",
    ]

    for test_data_file in test_data_files:
        full_file_path = configuration.get_absolute_file_path(test_data_file)

        with open(full_file_path) as json_test_data_file:
            json_config_text = json_test_data_file.read()
            test_data_json = json.loads(json_config_text)
            nexrad_client.inject(test_data_json)

    load_example_flight_rules()
    load_example_airports()

    run_hud_elements([WeatherTopViewScope, CompassAndHeadingTopElement, Groundspeed])


# Orgeon FAA sample data should look like this:
#
#       111111111111111111
#    11122223333333333322211
#  111223333355555555533332211
# 11223333445555676555543333221
