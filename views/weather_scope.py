"""
View element for a weather "radar" that looks from the top downwards.
"""

import datetime
import math
from typing import List

import pygame

from common_utils.task_timer import TaskProfiler
from common_utils.tasks import IntermittentTask
from configuration import configuration
from core_services.scope_range import ScopeRange
from core_services.zoom_manager import ZoomManager
from data_sources.ahrs_data import AhrsData
from data_sources.airports import load_example_airports, load_example_flight_rules
from data_sources.nexrad import NexradClient, ReflectivityBlock
from rendering import colors, drawing
from views.reflectivity_bitmap import ReflectivityBitmap
from views.abstract_elements.top_down_scope import TopDownScope


class WeatherTopViewScope(TopDownScope):
    """
    A view element for the HUD that draws a radar style scope
    showing where traffic is relative to our current position.
    """

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

        self.__time_of_last_block_fetch__ = datetime.datetime.now(
            datetime.timezone.utc)
        self.__nexrad_cache__: List[ReflectivityBlock] | None = None
        self.__reflectivity_blocks__: List[ReflectivityBlock] | None = None
        self.__reflectivity_signature__ = None
        self.__reflectivity_bitmap__: ReflectivityBitmap | None = None
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

        self.__maximum_radar_range__: int = self.__zoom_manager__.get_maximum_possible_zoom().max_ring_range

    def __render_reflectivity__(
        self,
        framebuffer: pygame.Surface,
        orientation: AhrsData,
    ):
        self.__log_bin_stats_task__.run()

        scope_range = self.__zoom_manager__.get_current_zoom()

        nexrad_blocks = []
        is_valid_orientation = (
            orientation.position is not None
            and orientation.position[0] is not None
            and orientation.position[1] is not None
        )

        if is_valid_orientation:
            current_heading = orientation.get_precise_gps_heading()
            is_heading_valid = current_heading is not None and not isinstance(
                current_heading, str
            )

            if is_heading_valid:
                nexrad_blocks = self.__get_nexrad_blocks__(
                    orientation.position, self.__maximum_radar_range__
                )

                bitmap = self.__get_reflectivity_bitmap__(nexrad_blocks)

                if bitmap is not None:
                    self.__draw_reflectivity_bitmap__(
                        framebuffer, orientation, current_heading, scope_range, bitmap
                    )

        self.__render_debug_visuals__(framebuffer, nexrad_blocks)

    def __render_debug_visuals__(
        self,
        framebuffer: pygame.Surface,
        nexrad_blocks: List[ReflectivityBlock],
    ):
        text_y_pos = self.__bottom_border__ - (self.__font_height__ << 1)
        nearby_position = [
            self.__left_border__,
            text_y_pos + (self.__font_height__ >> 1),
        ]
        total_position = [self.__left_border__,
                          text_y_pos + self.__font_height__]

        if self.__cluter_visuals__:
            self.__nearby_blocks_count__ = len(nexrad_blocks)

            self.__render_text__(
                framebuffer,
                f"Nearby: {self.__nearby_blocks_count__}",
                nearby_position,
                list(colors.YELLOW),
                0.5,
            )

            self.__total_blocks_count__ = len(NexradClient.REFLECTIVITY.keys())

            self.__render_text__(
                framebuffer,
                f"Total: {self.__total_blocks_count__}",
                total_position,
                list(colors.YELLOW),
                0.5,
            )

    def __get_nexrad_blocks__(
        self, position, max_distance: float
    ) -> List[ReflectivityBlock]:
        now = datetime.datetime.now(datetime.timezone.utc)
        seconds_since = (now - self.__time_of_last_block_fetch__).seconds

        if self.__nexrad_cache__ != None and seconds_since < 15:
            return self.__nexrad_cache__

        self.__nexrad_cache__ = NexradClient.get_nexrad_in_range(
            position, max_distance)
        self.__time_of_last_block_fetch__ = now

        return self.__nexrad_cache__

    def __get_reflectivity_bitmap__(
        self, nexrad_blocks: List[ReflectivityBlock]
    ) -> "ReflectivityBitmap | None":
        """
        Returns the bitmap of the given blocks, only drawing it again
        when the blocks, or their reports, have changed.
        """
        if nexrad_blocks is self.__reflectivity_blocks__:
            return self.__reflectivity_bitmap__

        self.__reflectivity_blocks__ = nexrad_blocks
        signature = [(block.block_id, block.report_time)
                     for block in nexrad_blocks]

        if signature == self.__reflectivity_signature__:
            return self.__reflectivity_bitmap__

        self.__reflectivity_signature__ = signature
        self.__reflectivity_bitmap__ = None
        self.__successful_bin_counts__ = 0
        self.__failed_bin_counts__ = 0
        self.__missing_bin_counts__ = 0

        if len(nexrad_blocks) > 0:
            with TaskProfiler(
                "views.weather_top_view_scope.WeatherTopViewScope.draw_reflectivity_bitmap"
            ):
                self.__reflectivity_bitmap__ = ReflectivityBitmap(
                    nexrad_blocks)

            self.__successful_bin_counts__ = self.__reflectivity_bitmap__.successful_bins
            self.__failed_bin_counts__ = self.__reflectivity_bitmap__.failed_bins
            self.__missing_bin_counts__ = self.__reflectivity_bitmap__.missing_bins

        return self.__reflectivity_bitmap__

    def __draw_reflectivity_bitmap__(
        self,
        framebuffer,
        orientation: AhrsData,
        current_heading: float,
        scope_range: ScopeRange,
        bitmap: "ReflectivityBitmap",
    ):
        max_pixel_distance = self.__scope_center__[1] - self.__top_border__
        pixels_per_mile = max_pixel_distance / scope_range.max_ring_range

        # The bitmap is in lat/lon, so a bin gets narrower the further
        # from the equator we are.
        bin_width_miles = (
            bitmap.lon_step
            * ReflectivityBitmap.MILES_PER_DEGREE
            * math.cos(math.radians(orientation.position[0]))
        )
        bin_height_miles = bitmap.lat_step * ReflectivityBitmap.MILES_PER_DEGREE

        drawing.renderer.textured_disc(
            framebuffer,
            bitmap.surface,
            list(bitmap.get_bitmap_position(orientation.position)),
            [bin_width_miles * pixels_per_mile,
                bin_height_miles * pixels_per_mile],
            current_heading,
            self.__scope_center__,
            max_pixel_distance,
        )

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
            self.__draw_distance_rings__(
                framebuffer, scope_range, colors.WHITE)
            self.__draw_all_compass_headings__(
                framebuffer, orientation, scope_range)

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
        "../test_data/large_response.json"
    ]

    for test_data_file in test_data_files:
        full_file_path = configuration.get_absolute_file_path(test_data_file)

        with open(full_file_path) as json_test_data_file:
            json_config_text = json_test_data_file.read()
            test_data_json = json.loads(json_config_text)
            nexrad_client.inject(test_data_json)

    load_example_flight_rules()
    load_example_airports()

    run_hud_elements(
        [WeatherTopViewScope, CompassAndHeadingTopElement, Groundspeed])


# Orgeon FAA sample data should look like this:
#
#       111111111111111111
#    11122223333333333322211
#  111223333355555555533332211
# 11223333445555676555543333221
