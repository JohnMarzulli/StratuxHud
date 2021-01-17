from numbers import Number

from common_utils import units
from common_utils.task_timer import TaskTimer
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from rendering import colors

from views.ahrs_element import AhrsElement


class Groundspeed(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.__font__ = font
        self.__font_height__ = font.get_height()
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(self.__font_height__) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = 0  # WAS int(framebuffer_size[0] * 0.01)

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        speed_units = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)

        airspeed_text = None
        is_valid_airspeed = orientation.is_avionics_source and isinstance(
            orientation.airspeed,
            Number)
        is_valid_groundspeed = orientation.groundspeed is not None and isinstance(
            orientation.groundspeed,
            Number)

        airspeed_text = units.get_converted_units_string(
            speed_units,
            orientation.airspeed * units.feet_to_nm,
            unit_type=units.SPEED,
            decimal_places=False) if is_valid_airspeed else None

        groundspeed_text = units.get_converted_units_string(
            speed_units,
            (orientation.groundspeed * units.yards_to_nm),
            unit_type=units.SPEED,
            decimal_places=False) if is_valid_groundspeed else orientation.groundspeed

        groundspeed_text += " GND"

        if airspeed_text is not None:
            airspeed_text += " IAS"
            ias_len = len(airspeed_text)
            gnd_len = len(groundspeed_text)
            max_len = gnd_len if ias_len < gnd_len else ias_len
            airspeed_text = airspeed_text.rjust(max_len)
            groundspeed_text = groundspeed_text.rjust(max_len)

        gs_display_color = colors.WHITE if is_valid_groundspeed and orientation.gps_online else colors.RED
        airspeed_color = colors.WHITE if is_valid_airspeed else colors.RED

        ias_texture = self.__font__.render(
            airspeed_text,
            True,
            airspeed_color,
            colors.BLACK) if airspeed_text is not None else None

        gs_texture = self.__font__.render(
            groundspeed_text,
            True,
            gs_display_color,
            colors.BLACK)

        gs_position_adj = self.__font_height__ if ias_texture is not None else 0

        framebuffer.blit(
            gs_texture,
            (self.__left_x__, self.__text_y_pos__ + gs_position_adj))

        if ias_texture is not None:
            framebuffer.blit(
                ias_texture,
                (self.__left_x__, self.__text_y_pos__))


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element

    run_ahrs_hud_element(Groundspeed, True)
