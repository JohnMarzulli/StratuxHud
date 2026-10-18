from common_utils import geo_math
from data_sources.nexrad import NexradClient, ReflectivityBlock
from rendering import colors


import pygame


import math
from typing import List, Tuple


class ReflectivityBitmap:
    """
    The reflectivity of a set of blocks, drawn north-up onto a bitmap
    where each pixel is exactly one bin.

    Drawing the bitmap only takes a fill per run, and is only needed when
    the reports change. The scope then scales, rotates, and positions
    the bitmap for each frame, which keeps every bin a solid block.
    """

    BIN_ROWS = [0, 1, 2, 3]
    BIN_COLUMNS = list(range(32))

    MILES_PER_DEGREE = math.radians(1.0) * geo_math.EARTH_RADIUS_STATUTE_MILES

    def __init__(self, blocks: List[ReflectivityBlock]):
        self.lat_step: float = min(block.lat_step for block in blocks)
        self.lon_step: float = min(block.lon_step for block in blocks)
        self.north: float = max(block.north_western[0] for block in blocks)
        self.west: float = min(block.north_western[1] for block in blocks)
        south: float = min(block.south_eastern[0] for block in blocks)
        east: float = max(block.south_eastern[1] for block in blocks)

        self.successful_bins: int = 0
        self.failed_bins: int = 0
        self.missing_bins: int = 0

        # Leave an empty border so that the edge bins are not
        # stretched outwards when the bitmap is drawn.
        size: tuple[int, int] = (
            int(round((east - self.west) / self.lon_step)) + 2,
            int(round((self.north - south) / self.lat_step)) + 2,
        )

        self.surface: pygame.Surface = pygame.Surface(size)
        self.surface.fill(colors.BLACK)
        self.surface.set_colorkey(colors.BLACK)

        [self.__draw_block__(block) for block in blocks]

    def get_bitmap_position(self, position) -> Tuple[float, float]:
        """
        Returns the (x, y) position in the bitmap, in fractional pixels,
        of the given lat/lon.
        """
        return (
            ((position[1] - self.west) / self.lon_step) + 1,
            ((self.north - position[0]) / self.lat_step) + 1,
        )

    def __draw_block__(self, block: ReflectivityBlock) -> None:
        left, top = self.get_bitmap_position(block.north_western)
        left = int(round(left))
        top = int(round(top))
        bin_width = max(1, int(round(block.lon_step / self.lon_step)))
        bin_height = max(1, int(round(block.lat_step / self.lat_step)))

        for lat_index in ReflectivityBitmap.BIN_ROWS:
            if len(block.reflectivity) <= lat_index:
                self.missing_bins += len(ReflectivityBitmap.BIN_COLUMNS)
                continue

            lon_index: int = 0
            row_top = top + (lat_index * bin_height)

            for run in block.reflectivity[lat_index]:
                try:
                    run_length: int = run["runLength"]
                    reflectivity: int = run["reflectivity"]

                    if reflectivity > 0:
                        self.surface.fill(
                            NexradClient.reflectivity_to_rgb(reflectivity),
                            (
                                left + (lon_index * bin_width),
                                row_top,
                                run_length * bin_width,
                                bin_height,
                            ),
                        )

                    self.successful_bins += run_length
                    lon_index += run_length
                except:
                    self.failed_bins += 1
