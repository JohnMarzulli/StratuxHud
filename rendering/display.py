"""
Initializes the display, and holds common color values.
"""

import os
import sys

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

FORCE_SOFTWARE_FLAG = "software"


def is_forced_software_rendering() -> bool:
    """
    Should we use software rendering no matter what type of
    runtime environment we are in.

    Returns:
        bool: Should the HUD use software rendering?
    """
    is_flag_present = False

    for argument in sys.argv:
        is_flag_present |= FORCE_SOFTWARE_FLAG in argument.lower()

    return is_flag_present


def __is_x_windows__() -> bool:
    display = os.getenv('DISPLAY')

    return (display is not None) and len(display) > 0


def is_opengl_target() -> bool:
    use_opengl = not is_forced_software_rendering()
    use_opengl &= __OPEN_GL_AVAILABLE__
    use_opengl &= (not local_debug.IS_PI or __is_x_windows__())

    return use_opengl


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
        self,
        force_fullscreen: bool,
        force_software: bool
    ) -> list:
        """
        Get our target screen mode

        Args:
            force_fullscreen (bool, optional): Do we want to force fullscreen mode?. Defaults to False.

        Returns:
            int: The combined bitflags of all of our screenmodes.
        """
        screen_mode = pygame.HWACCEL | pygame.constants.DOUBLEBUF | pygame.constants.RLEACCEL
        is_fullscreen = False

        if self.__is_fullscreen_target__() or force_fullscreen:
            print("Detecting or forcing fullscreen")
            screen_mode |= pygame.FULLSCREEN
            is_fullscreen = True

        if is_opengl_target() and not force_software:
            print("Detecting or forcing software rasterization")
            screen_mode |= pygame.constants.OPENGL | pygame.constants.OPENGLBLIT

        return screen_mode, is_fullscreen

    def __get_target_screen_size__(
        self
    ) -> list:
        if pygame is not None and pygame.display is not None and pygame.display.get_init() != 0:
            return pygame.display.Info().current_w, pygame.display.Info().current_h

        return Display.__DEFAULT_SCREEN_SIZE__

    def __init__(
        self,
        force_fullscreen: bool = False,
        force_software: bool = False
    ) -> None:
        """
        Initializes PyGame to run on the current screen.

        Args:
            force_fullscreen (bool, optional): Do we want to force fullscreen mode?. Defaults to False.
            force_software (bool, optional): Do we want to force the software renderer to be user? Defaults to False.

        Returns:
            bool: Should the HUD use fullscreen?
        """

        self.is_open_gl = is_opengl_target() and not force_software
        self.size = self.__get_target_screen_size__()
        display_mode, is_fullscreen = self.__get_target_screen_mode__(
            force_fullscreen,
            force_software)

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

        # We need to do this for Linux FBCON direct
        # rendering since we do not know the size
        # of the screen until AFTER it has been initialized
        if is_fullscreen:
            self.size = self.__get_target_screen_size__()

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
