from numbers import Number

from common_utils import units
from common_utils.task_timer import TaskProfiler
from configuration import configuration
from core_services import breadcrumbs
from data_sources.ahrs_data import AhrsData
from rendering import colors

from views.ahrs_element import AhrsElement


class Groundspeed(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

        self.__text_y_pos__ = (self.__center_y__ >> 1) - \
            self.__font_half_height__
        self.__speed_units__ = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)

    def __get_indicated_text__(
        self,
        speed,
        type_of_speed: str,
        color: list
    ) -> list:
        """
        Given a speed, generate a list of text description pacakges
        that will result in the speed and annotations
        being rendered

        Args:
            speed (float, str): The speed we are going. Will be float if a number, str if a form of "inop"
            type_of_speed (str): The type of speed annotation. GND or IAS
            color (list): The color to render the speed and annotations.

        Returns:
            list: A list of text description packages.
        """

        text = speed if isinstance(speed, str) else units.get_converted_units_string(
            self.__speed_units__,
            speed,
            unit_type=units.SPEED,
            decimal_places=False)

        split_from_units = text.split(" ")

        # In the case of "---" or other
        # result where the unit is missing
        # add a blank item
        # to the position of the speed-type
        # indicator remains the same veritcally
        if len(split_from_units) == 1:
            split_from_units.append("")

        split_from_units.append(type_of_speed)

        if self.__reduced_visuals__:
            split_from_units = split_from_units[:1]

        is_first = True
        text_with_scale_and_color = []

        for text_piece in split_from_units:
            scale = 1.0 if is_first else 0.5
            package = [scale, text_piece, color]

            text_with_scale_and_color.append(package)

            is_first = False

        return text_with_scale_and_color

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        with TaskProfiler("views.groundspeed.Groundspeed.setup"):
            is_valid_airspeed = orientation.is_avionics_source and isinstance(
                orientation.airspeed,
                Number)
            is_valid_groundspeed = orientation.groundspeed is not None and isinstance(
                orientation.groundspeed,
                Number)

            gs_display_color = colors.WHITE if is_valid_groundspeed and orientation.gps_online else colors.RED
            airspeed_color = colors.WHITE if is_valid_airspeed else colors.RED

            airspeed_text = self.__get_indicated_text__(
                orientation.airspeed * units.feet_to_nm,
                "IAS",
                airspeed_color) if is_valid_airspeed else None

            shown_gs = orientation.groundspeed * \
                units.yards_to_nm if is_valid_groundspeed else orientation.groundspeed

            groundspeed_text = self.__get_indicated_text__(
                shown_gs,
                "GND",
                gs_display_color)

            crumb_text = self.__get_indicated_text__(
                breadcrumbs.INSTANCE.speed,
                "BRC",
                gs_display_color)

            gs_position_adj = self.__font_height__ if is_valid_airspeed is not None else 0

        with TaskProfiler("views.groundspeed.Groundspeed.render"):
            self.__render_text_with_stacked_annotations__(
                framebuffer,
                [self.__left_border__, self.__text_y_pos__ + (2 * gs_position_adj)],
                crumb_text)

            self.__render_text_with_stacked_annotations__(
                framebuffer,
                [self.__left_border__, self.__text_y_pos__ + gs_position_adj],
                groundspeed_text)

            if airspeed_text is not None:
                self.__render_text_with_stacked_annotations__(
                    framebuffer,
                    [self.__left_border__, self.__text_y_pos__],
                    airspeed_text)


if __name__ == '__main__':
    from views.hud_elements import run_hud_element

    run_hud_element(Groundspeed, True)
