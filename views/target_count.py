from common_utils.task_timer import TaskTimer
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
        self.__font__ = font
        center_y = framebuffer_size[1] >> 2
        text_half_height = int(font.get_height()) >> 1
        self.__text_y_pos__ = center_y - text_half_height
        self.__rhs__ = int(0.9 * framebuffer_size[0])

        self.__left_x__ = 0  # WAS int(framebuffer_size[0] * 0.01)

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

        texture = self.__font__.render(text, True, colors.WHITE, colors.BLACK)

        framebuffer.blit(
            texture, (self.__left_x__, self.__text_y_pos__))


if __name__ == '__main__':
    hud_elements.run_ahrs_hud_element(TargetCount, True)
