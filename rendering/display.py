"""
Initializes the display, and holds common color values.
"""

import os

import pygame
from common_utils import local_debug

# The SunFounder 5" TFT
DEFAULT_SCREEN_SIZE = 800, 480  # 1600, 960


def __get_screen_size_and_mode__():
    size = DEFAULT_SCREEN_SIZE
    screen_mode = pygame.HWACCEL | pygame.constants.RLEACCEL

    if local_debug.IS_PI:
        screen_mode |= pygame.FULLSCREEN
    else:
        screen_mode |= pygame.RESIZABLE

    return (size, screen_mode)


def display_init():
    """
    Initializes PyGame to run on the current screen.
    """

    size, screen_mode = __get_screen_size_and_mode__()
    display_number = os.getenv('DISPLAY')

    if display_number:
        print("Running under X{}, flags={}".format(display_number, screen_mode))
        screen = pygame.display.set_mode(size, screen_mode)

        return screen, size

    if local_debug.IS_MAC:
        screen = pygame.display.set_mode(size)

        return screen, size

    # List of drivers:
    # https://wiki.libsdl.org/FAQUsingSDL
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

    screen = pygame.display.set_mode(size, screen_mode)

    return screen, size
