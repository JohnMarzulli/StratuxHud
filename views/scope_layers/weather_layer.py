"""
NEXRAD weather reflectivity on the scope.
"""

import math
from typing import List

from common_utils.authoritative_time import get_system_time
from common_utils.task_timer import TaskProfiler
from common_utils.tasks import IntermittentTask
from core_services.zoom_manager import get_maximum_possible_zoom
from data_sources.nexrad import NexradClient, ReflectivityBlock
from rendering import colors, drawing
from views.reflectivity_bitmap import ReflectivityBitmap
from views.scope_layers.scope_canvas import ScopeCanvas
from views.scope_layers.scope_frame import ScopeFrame
from views.scope_layers.scope_layer import ScopeLayer

# How often to look for new blocks in range.
SECONDS_BETWEEN_BLOCK_FETCHES = 15


class WeatherLayer(ScopeLayer):
    """
    Draws the reflectivity as a bitmap clipped to the scope's disc.

    Blocks are fetched for the furthest possible zoom, so zooming
    never has to wait for data. The bitmap is only rebuilt when the
    blocks (or their reports) change.
    """

    def __init__(self, canvas: ScopeCanvas) -> None:
        super().__init__(canvas)

        self.__time_of_last_block_fetch__ = get_system_time()
        self.__nexrad_cache__: List[ReflectivityBlock] | None = None
        self.__reflectivity_blocks__: List[ReflectivityBlock] | None = None
        self.__reflectivity_signature__ = None
        self.__reflectivity_bitmap__: ReflectivityBitmap | None = None
        self.__nearby_blocks_count__ = 0
        self.__total_blocks_count__ = 0

        self.__log_bin_stats_task__ = IntermittentTask(
            "Render Failed Weather Counts", 15.0, self.__log_bin_counts__, None
        )

    def render(self, frame: ScopeFrame) -> None:
        try:
            self.__render_reflectivity__(frame)
        except Exception:
            # Weather is a nice-to-have; never let it take the scope down.
            pass

    def __render_reflectivity__(self, frame: ScopeFrame):
        self.__log_bin_stats_task__.run()

        nexrad_blocks = []

        if frame.has_position():
            current_heading = frame.orientation.get_precise_gps_heading()
            is_heading_valid = current_heading is not None and not isinstance(
                current_heading, str
            )

            if is_heading_valid:
                maximum_range_statute = frame.display_to_statute(
                    get_maximum_possible_zoom().max_ring_range
                )
                nexrad_blocks = self.__get_nexrad_blocks__(
                    frame.orientation.position, maximum_range_statute
                )

                bitmap = self.__get_reflectivity_bitmap__(nexrad_blocks)

                if bitmap is not None:
                    self.__draw_reflectivity_bitmap__(frame, current_heading, bitmap)

        self.__render_debug_visuals__(frame, nexrad_blocks)

    def __render_debug_visuals__(
        self, frame: ScopeFrame, nexrad_blocks: List[ReflectivityBlock]
    ):
        canvas = self.canvas

        if not canvas.clutter_visuals:
            return

        text_y_pos = canvas.bottom_border - (canvas.font_height << 1)

        self.__nearby_blocks_count__ = len(nexrad_blocks)
        canvas.draw_text(
            frame.framebuffer,
            f"Nearby: {self.__nearby_blocks_count__}",
            [canvas.left_border, text_y_pos + (canvas.font_height >> 1)],
            list(colors.YELLOW),
            0.5,
        )

        self.__total_blocks_count__ = len(NexradClient.REFLECTIVITY.keys())
        canvas.draw_text(
            frame.framebuffer,
            f"Total: {self.__total_blocks_count__}",
            [canvas.left_border, text_y_pos + canvas.font_height],
            list(colors.YELLOW),
            0.5,
        )

    def __get_nexrad_blocks__(
        self, position, max_distance_statute: float
    ) -> List[ReflectivityBlock]:
        now = get_system_time()
        seconds_since = (now - self.__time_of_last_block_fetch__).seconds

        if self.__nexrad_cache__ is not None and seconds_since < SECONDS_BETWEEN_BLOCK_FETCHES:
            return self.__nexrad_cache__

        self.__nexrad_cache__ = NexradClient.get_nexrad_in_range(
            position, max_distance_statute
        )
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
        signature = [(block.block_id, block.report_time) for block in nexrad_blocks]

        if signature == self.__reflectivity_signature__:
            return self.__reflectivity_bitmap__

        self.__reflectivity_signature__ = signature
        self.__reflectivity_bitmap__ = None

        if len(nexrad_blocks) > 0:
            with TaskProfiler("views.scope_layers.WeatherLayer.draw_reflectivity_bitmap"):
                self.__reflectivity_bitmap__ = ReflectivityBitmap(nexrad_blocks)

        return self.__reflectivity_bitmap__

    def __draw_reflectivity_bitmap__(
        self,
        frame: ScopeFrame,
        current_heading: float,
        bitmap: "ReflectivityBitmap",
    ):
        max_pixel_distance = self.canvas.max_pixel_radius
        # The bitmap is measured in statute miles; the rings in display units.
        pixels_per_statute_mile = max_pixel_distance / frame.display_to_statute(
            frame.scope_range.max_ring_range
        )

        # The bitmap is in lat/lon, so a bin gets narrower the further
        # from the equator we are.
        bin_width_miles = (
            bitmap.lon_step
            * ReflectivityBitmap.MILES_PER_DEGREE
            * math.cos(math.radians(frame.orientation.position[0]))
        )
        bin_height_miles = bitmap.lat_step * ReflectivityBitmap.MILES_PER_DEGREE

        drawing.renderer.textured_disc(
            frame.framebuffer,
            bitmap.surface,
            list(bitmap.get_bitmap_position(frame.orientation.position)),
            [
                bin_width_miles * pixels_per_statute_mile,
                bin_height_miles * pixels_per_statute_mile,
            ],
            current_heading,
            self.canvas.center,
            max_pixel_distance,
        )

    def __log_bin_counts__(self):
        if self.__reflectivity_bitmap__ is not None:
            print(f"Missing bins:{self.__reflectivity_bitmap__.missing_bins}")
            print(f"Failed bins:{self.__reflectivity_bitmap__.failed_bins}")
            print(f"Passed bins:{self.__reflectivity_bitmap__.successful_bins}")

        print(f"Nearby blocks:{self.__nearby_blocks_count__}")
        print(f"Total blocks:{self.__total_blocks_count__}")
