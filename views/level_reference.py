import pygame
from common_utils.task_timer import TaskTimer
from rendering import colors

from views.ahrs_element import AhrsElement


class LevelReference(AhrsElement):
    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size
    ):
        self.task_timer = TaskTimer('LevelReference')
        self.level_reference_lines = []

        width = framebuffer_size[0]
        center = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        edge_proportion = int(width * 0.05)

        artificial_horizon_level = [[int(width * 0.4),  center[1]],
                                    [int(width * 0.6),  center[1]]]
        left_hash = [[0, center[1]], [edge_proportion, center[1]]]
        right_hash = [[width - edge_proportion, center[1]], [width, center[1]]]

        self.level_reference_lines.append(artificial_horizon_level)
        self.level_reference_lines.append(left_hash)
        self.level_reference_lines.append(right_hash)

    def render(
        self,
        framebuffer,
        orientation
    ):
        """
        Renders a "straight and level" line to the HUD.
        """

        self.task_timer.start()
        [pygame.draw.lines(
            framebuffer,
            colors.WHITE,
            False,
            line,
            6) for line in self.level_reference_lines]
        self.task_timer.stop()


if __name__ == '__main__':
    from views.hud_elements import run_ahrs_hud_element
    run_ahrs_hud_element(LevelReference)
