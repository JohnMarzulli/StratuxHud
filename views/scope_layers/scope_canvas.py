from common_utils import fast_math


import math


class ScopeCanvas:
    """
    The fixed drawing surface of one scope.
    """

    def __init__(self, host, scope_center: list, max_pixel_radius: int) -> None:
        """
        Args:
            host: The HudElement that owns the scope. Used for its font
                (text drawing) and its line widths.
            scope_center (list): Screen position of our own aircraft.
            max_pixel_radius (int): Pixels from the center to the outer ring.
        """
        self.__host__ = host

        self.center = scope_center
        self.max_pixel_radius = max_pixel_radius

        self.width = host.__width__
        self.height = host.__height__
        self.left_border = host.__left_border__
        self.right_border = host.__right_border__
        self.bottom_border = host.__bottom_border__

        self.font_height = host.__font_height__
        self.font_half_height = host.__font_half_height__

        self.line_width = host.__line_width__
        self.thin_line_width = host.__thin_line_width__
        self.reduced_visuals = host.__reduced_visuals__
        self.clutter_visuals = host.__cluter_visuals__
        self.draw_identifiers = True

        size = self.height * 0.04
        half_size = int((size / 2.0) + 0.5)
        quarter_size = int((size / 4.0) + 0.5)
        self.no_direction_target_size = quarter_size

        # Points of the traffic arrow, centered on 0,0 and pointing up.
        self.__target_indicator__ = [
            [-quarter_size, half_size],
            [0, -half_size],
            [quarter_size, half_size],
        ]

    def get_traffic_indicator(
        self, indicator_position: list, our_heading: float, traffic_heading: float
    ) -> list:
        """
        The points of an arrow at the given screen position, pointing
        along the traffic's heading relative to ours.
        """
        rotation = 360.0 - our_heading
        rotation = rotation + traffic_heading
        rotation_degrees = int(fast_math.wrap_degrees(rotation))

        radians = math.radians(rotation_degrees)
        rotation_sin = math.sin(radians)
        rotation_cos = math.cos(radians)

        return [
            [
                (point[0] * rotation_cos - point[1] * rotation_sin)
                + indicator_position[0],
                (point[0] * rotation_sin + point[1] * rotation_cos)
                + indicator_position[1],
            ]
            for point in self.__target_indicator__
        ]

    def draw_centered_text(
        self, framebuffer, text: str, position, color, background_color, scale: float
    ):
        return self.__host__.__render_centered_text__(
            framebuffer, text, position, color, background_color, scale, 0, True
        )

    def draw_text(self, framebuffer, text: str, position, color, scale: float = 1.0):
        return self.__host__.__render_text__(framebuffer, text, position, color, scale)

    def draw_right_justified_text(
        self, framebuffer, text: str, position, color, scale: float = 1.0
    ):
        return self.__host__.__render_text_right_justified__(
            framebuffer, text, position, color, scale
        )
