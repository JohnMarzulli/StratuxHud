from data_sources import targets
from data_sources.ahrs_data import AhrsData
from rendering import colors

from views import hud_elements
from views.ahrs_element import AhrsElement


class TargetCount(AhrsElement):
    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        super().__init__(font, framebuffer_size)

        self.__text_y_pos__ = self.__center_y__ - self.__font_half_height__

    def render(
        self,
        framebuffer,
        orientation: AhrsData
    ):
        # Get the traffic, and bail out of we have none

        text = "NO TARGETS"

        try:
            count = len(targets.TARGET_MANAGER.targets)

            if count > 0:
                text = "{0} TARGETS".format(count)
        except Exception as e:
            text = "ERROR" + str(e)

        texture = self.__font__.render(
            text,
            True,
            colors.WHITE, colors.BLACK)

        framebuffer.blit(
            texture,
            (self.__left_border__, self.__text_y_pos__))


if __name__ == '__main__':
    hud_elements.run_ahrs_hud_element(TargetCount, True)
