from numbers import Number

import pygame
from common_utils import units
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
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
        super().__init__(font, framebuffer_size)

        self.__text_y_pos__ = (self.__center_y__>> 1) - self.__font_half_height__
        self.__speed_units__ = configuration.CONFIGURATION.__get_config_value__(
            configuration.Configuration.DISTANCE_UNITS_KEY,
            units.STATUTE)
    
    def __get_indicated_text__(
        self,
        speed,
        type_of_speed: str,
        color: list
    ) -> list:
        text = speed if isinstance(speed, str) else  units.get_converted_units_string(
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

        is_first = True
        text_with_scale_and_color = []

        for text_piece in split_from_units:
            scale = 1.0 if is_first else 0.5
            package = [scale, text_piece, color]

            text_with_scale_and_color.append(package)

            is_first = False

        return text_with_scale_and_color
    
    def __render_text__(
        self,
        framebuffer,
        text: str,
        position: list,
        color :list,
        scale : float
    ) -> list:
        texture, size = HudDataCache.get_cached_text_texture(
            text,
            self.__font__,
            color,
            colors.BLACK,
            True,
            False)
        
        scaled_size = [int(size[0] * scale), int(size[1] * scale)]
            
        texture = pygame.transform.smoothscale(
            texture,
            scaled_size)
        
        framebuffer.blit(
            texture,
            position)
        
        return scaled_size

    
    def __render_speed_text__(
        self,
        framebuffer,
        starting_position: list,
        scale_text_color_list: list
    ):
        # Take the speed and render it on the left at the given y
        # then take [1], render at the new X and given y
        # then take[2], render at same X as [1], moved down the split vertical

        speed_package = scale_text_color_list[0]
        speed_size = self.__render_text__(
            framebuffer,
            speed_package[1],
            starting_position,
            speed_package[2],
            speed_package[0])
        
        current_position = [starting_position[0] + speed_size[0], starting_position[1]]

        for (scale, text, color) in scale_text_color_list[1:]:
            info_size = self.__render_text__(
                framebuffer,
                text,
                current_position,
                color,
                scale)

            current_position[1] += info_size[1]

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
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

        shown_gs = orientation.groundspeed * units.yards_to_nm if is_valid_groundspeed else orientation.groundspeed

        groundspeed_text = self.__get_indicated_text__(
            shown_gs,
            "GND",
            gs_display_color)

        gs_position_adj = self.__font_height__ if is_valid_airspeed is not None else 0

        self.__render_speed_text__(
            framebuffer,
            [self.__left_border__, self.__text_y_pos__ + gs_position_adj],
            groundspeed_text)
        
        if airspeed_text is not None:
            self.__render_speed_text__(
                framebuffer,
                [self.__left_border__, self.__text_y_pos__],
                airspeed_text)


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element

    run_ahrs_hud_element(Groundspeed, True)
