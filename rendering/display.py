"""
Initializes the display, and holds common color values.
"""

import os

import pygame
import pygame.constants
from common_utils import local_debug

__OPEN_GL_AVAILABLE__ = False
try:
    from OpenGL import GL, GLU

    __OPEN_GL_AVAILABLE__ = True
except:
    pass

from rendering import colors


def __is_x_windows__() -> bool:
    display = os.getenv('DISPLAY')

    return (display is not None) and len(display) > 0


def is_opengl_target() -> bool:
    return __OPEN_GL_AVAILABLE__ and (not local_debug.IS_PI or __is_x_windows__())


IS_OPENGL = is_opengl_target()


class Display:
    """
    Instance of the current display that is being used for
    rendering. Chooses the correct renderer, and
    handles platform detection.
    """

    __DEFAULT_SCREEN_SIZE__ = 800, 480  # 1600, 960

    def __is_fullscreen_target__(
        self
    ) -> bool:
        return local_debug.IS_PI and not __is_x_windows__()

    def __get_target_screen_mode__(
        self
    ) -> int:
        screen_mode = pygame.HWACCEL | pygame.constants.DOUBLEBUF | pygame.constants.RLEACCEL

        if self.__is_fullscreen_target__():
            screen_mode |= pygame.FULLSCREEN

        if is_opengl_target():
            screen_mode |= pygame.constants.OPENGL | pygame.constants.OPENGLBLIT

        return screen_mode

    def __get_target_screen_size__(
        self
    ) -> list:
        if pygame is not None and pygame.display is not None and pygame.display.get_init() != 0:
            return pygame.display.Info().current_w, pygame.display.Info().current_h

        return Display.__DEFAULT_SCREEN_SIZE__

    def __init__(
        self
    ) -> None:
        """
        Initializes PyGame to run on the current screen.
        """

        self.is_open_gl = is_opengl_target()
        self.size = self.__get_target_screen_size__()
        display_mode = self.__get_target_screen_mode__()

        # List of drivers:
        # https://wiki.libsdl.org/FAQUsingSDL
        if not __is_x_windows__():
            drivers = ['fbcon', 'directfb', 'svgalib', 'directx', 'windib', 'Quartz']
            found = False
            for driver in drivers:
                if not os.getenv('SDL_VIDEODRIVER'):
                    os.putenv('SDL_VIDEODRIVER', driver)

                try:
                    pygame.display.init()
                except pygame.error as ex:
                    print('Driver: {0} failed. EX={1}'.format(driver, ex))
                    continue

                found = True
                break

            if not found:
                raise Exception('No suitable video driver found!')

        pygame.display.set_mode(self.size, display_mode)

        if self.is_open_gl:
            GL.glEnable(GL.GL_POLYGON_SMOOTH)
            GL.glEnable(GL.GL_POINT_SMOOTH)
            GL.glEnable(GL.GL_LINE_SMOOTH)
            # Note that the vertical needs to be in reversed
            # order for some reason, but X is OK.
            # If you are "consistent" with the parameters
            # IE (0, sx, 0, sy) then the Y is flipped such
            # that 0 is at the bottom of the screen.
            GLU.gluOrtho2D(0, self.size[0], self.size[1], 0)
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)

    def clear(
        self
    ):
        if self.is_open_gl:
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        else:
            self.get_framebuffer().fill(colors.BLACK)

    def get_framebuffer(
        self
    ):
        return None if self.is_open_gl else pygame.display.get_surface()

    def flip(
        self
    ):
        if self.is_open_gl:
            GL.glFlush()

        pygame.display.flip()
