"""
Initializes the display, and holds common color values.
"""

import os
import sys

import pygame

from common_utils import local_debug

# The SunFounder 5" TFT
DEFAULT_SCREEN_SIZE = 800, 480


def __get_screen_size_and_mode__():
    size = DEFAULT_SCREEN_SIZE
    screen_mode = pygame.HWACCEL

    if local_debug.IS_PI:
        screen_mode |= pygame.FULLSCREEN
        size = pygame.display.Info().current_w, pygame.display.Info().current_h
    else:
        screen_mode |= pygame.RESIZABLE

    return (size, screen_mode)


def display_init():
    """
    Initializes PyGame to run on the current screen.
    """

    size = DEFAULT_SCREEN_SIZE
    display_number = os.getenv('DISPLAY')
    if display_number:
        screen_mode = (
            pygame.FULLSCREEN if local_debug.IS_PI else pygame.RESIZABLE) | pygame.HWACCEL
        print("Running under X{}, flags={}".format(display_number, screen_mode))
        screen = pygame.display.set_mode(size, screen_mode)
    else:
        # List of drivers:
        # https://wiki.libsdl.org/FAQUsingSDL
        drivers = ['fbcon', 'directfb', 'svgalib', 'directx', 'windib']
        found = False
        for driver in drivers:
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)

            try:
                pygame.display.init()
            except pygame.error:
                print('Driver: {0} failed.'.format(driver))
                continue

            found = True
            break

        if not found:
            raise Exception('No suitable video driver found!')

        (size, screen_mode) = __get_screen_size_and_mode__()

        screen = pygame.display.set_mode(size, screen_mode)

    return screen, size
