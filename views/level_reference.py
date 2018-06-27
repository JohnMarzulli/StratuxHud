import pygame

import testing
testing.load_imports()

from lib.display import *
from lib.task_timer import TaskTimer
from ahrs_element import AhrsElement


class LevelReference(AhrsElement):
    def __init__(self, degrees_of_pitch, pixels_per_degree_y, font, framebuffer_size):
        self.task_timer = TaskTimer('LevelReference')
        self.level_reference_lines = []

        width = framebuffer_size[0]
        center = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        edge_reference_proportion = int(width * 0.05)

        artificial_horizon_level = [[int(width * 0.4),  center[1]],
                                    [int(width * 0.6),  center[1]]]
        left_hash = [[0, center[1]], [edge_reference_proportion, center[1]]]
        right_hash = [[width - edge_reference_proportion,
                       center[1]], [width, center[1]]]

        self.level_reference_lines.append(artificial_horizon_level)
        self.level_reference_lines.append(left_hash)
        self.level_reference_lines.append(right_hash)

    def render(self, framebuffer, orientation):
        """
        Renders a "straight and level" line to the HUD.
        """

        self.task_timer.start()
        for line in self.level_reference_lines:
            pygame.draw.lines(framebuffer,
                              WHITE, False, line, 6)
        self.task_timer.stop()

if __name__ == '__main__':
    import hud_elements
    hud_elements.run_ahrs_hud_element(LevelReference)
