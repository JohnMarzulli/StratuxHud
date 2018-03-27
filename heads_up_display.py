#!/usr/bin/env python

import math
import json
import os
import sys
import random
import argparse
import datetime
import requests
import pygame
import display
import traffic
import lib.utilities as utilities
import lib.local_debug as local_debug
from configuration import *
from aircraft import Aircraft
import hud_elements
from lib.task_timer import TaskTimer
from lib.recurring_task import RecurringTask

# TODO - Add the G-Meter
# TODO - Disable functionality based on the enabled StratuxCapabilities
# TODO - Check for the key existance anyway... cross update the capabilties
# TODO - Add roll indicator

# Traffic description in https://github.com/cyoung/stratux/blob/master/notes/app-vendor-integration.md
# WebSockets docs at https://ws4py.readthedocs.io/en/latest/
# pip install ws4py
# pip install requests


class HeadsUpDisplay(object):
    """
    Class to handle the HUD work...
    """

    DEGREES_OF_PITCH = 90
    PITCH_DEGREES_DISPLAY_SCALER = 2.0

    def __level_ahrs__(self):
        url = "http://{0}/cageAHRS".format(
            self.__configuration__.stratux_address())

        try:
            requests.Session().post(url, timeout=2)
        except:
            pass
    
    def __shutdown_stratux__(self):
        url = "http://{0}/shutdown".format(
            self.__configuration__.stratux_address())

        try:
            requests.Session().post(url, timeout=2)
        except:
            pass

    def run(self):
        clock = pygame.time.Clock()

        try:
            while self.tick(clock):
                pass
        finally:
            self.__connection_manager__.shutdown()
            pygame.display.quit()
            self.__render_perf__()
            # pygame.quit()

        sys.exit()

    def tick(self, clock):
        """
        Run for a single frame.

        Arguments:
            clock {pygame.time.Clock} -- game/frame clock

        Returns:
            bool -- True if the code should run for another tick.
        """

        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    utilities.shutdown()
                    return False
                if event.type == pygame.KEYUP:
                    if event.key in [pygame.K_q, pygame.K_ESCAPE]:
                        utilities.shutdown(0)
                        if not local_debug.is_debug():
                            self.__shutdown_stratux__()
                        return False
                    
                    if event.key in [pygame.K_KP_PLUS, pygame.K_PLUS]:
                        self.__view_index__ += 1
                    
                    if event.key in [pygame.K_KP_MINUS, pygame.K_MINUS]:
                        self.__view_index__ -= 1

                    if event.key in [pygame.K_r]:
                        self.render_perf.reset()
                        self.orient_perf.reset()
                    
                    if event.key in [pygame.K_BACKSPACE]:
                        self.__level_ahrs__()
                    
                    if event.key in [pygame.K_EQUALS, pygame.K_KP_EQUALS]:
                        self.__render_perf__ = not self.__render_perf__

            if self.__view_index__ >= (len(self.__hud__views__)):
                self.__view_index__ = 0

            if self.__view_index__ < 0:
                self.__view_index__ = (len(self.__hud__views__) - 1)

            self.orient_perf.start()
            orientation = self.__aircraft__.get_orientation()
            self.orient_perf.stop()

            self.__backpage_framebuffer__.fill(display.BLACK)

            self.render_perf.start()

            if self.__aircraft__.is_ahrs_available():
                # Order of drawing is important
                # The pitch lines are drawn before the other
                # referenence information so they will be pushed to the
                # background.
                # The reference text is also intentionally
                # drawn with a black background
                # to overdraw the pitch lines
                # and improve readability
                try:
                    hud_elements.HudDataCache.update_traffic_reports()

                    for hud_element in self.__hud__views__[self.__view_index__]:
                        try:
                            hud_element.render(
                                self.__backpage_framebuffer__, orientation)
                        except:
                            pass
                except:
                    pass
            else:
                # Should do this if the signal is lost...
                self.__ahrs_not_available_element__.render(
                    self.__backpage_framebuffer__, orientation)  # 1ms

            self.render_perf.stop()

            if self.__render_perf__ or len(self.__hud__views__[self.__view_index__]) == 0:
                debug_status_left = int(self.__width__ >> 1)
                debug_status_top = int(self.__height__ * 0.2)
                render_perf_text = self.render_perf.to_string()
                orient_perf_text = self.orient_perf.to_string()

                perf_len = len(render_perf_text)
                orient_len = len(orient_perf_text)

                if perf_len > orient_len:
                    orient_perf_text = orient_perf_text.ljust(perf_len)
                else:
                    render_perf_text = render_perf_text.ljust(orient_len)

                self.__render_text__(render_perf_text, display.BLACK, debug_status_left, debug_status_top, 0, display.YELLOW)
                debug_status_top += int(self.__font__.get_height() * 1.1)
                self.__render_text__(orient_perf_text, display.BLACK, debug_status_left, debug_status_top, 0, display.YELLOW)
        finally:
            # Change the frame buffer
            flipped = pygame.transform.flip(
                self.__backpage_framebuffer__, self.__configuration__.flip_horizonal, self.__configuration__.flip_vertical)
            self.__backpage_framebuffer__.blit(flipped, [0, 0])
            pygame.display.flip()
            clock.tick(MAX_FRAMERATE)

        return True

    def __render_text__(self, text, color, position_x, position_y, roll, background_color=None):
        """
        Renders the text with the results centered on the given
        position.
        """

        rendered_text = self.__detail_font__.render(
            text, True, color, background_color)
        text_width, text_height = rendered_text.get_size()

        text = pygame.transform.rotate(rendered_text, roll)

        self.__backpage_framebuffer__.blit(
            text, (position_x - (text_width >> 1), position_y - (text_height >> 1)))

        return text_width, text_height

    def __init__(self):
        """
        Initialize and create a new HUD.
        """

        self.render_perf = TaskTimer("Render")
        self.orient_perf = TaskTimer("Orient")

        self.__configuration__ = Configuration(DEFAULT_CONFIG_FILE)

        adsb_traffic_address = "ws://{0}/traffic".format(
            self.__configuration__.stratux_address())
        self.__connection_manager__ = traffic.ConnectionManager(
            adsb_traffic_address)

        self.__backpage_framebuffer__, screen_size = display.display_init()  # args.debug)
        self.__width__, self.__height__ = screen_size
        pygame.mouse.set_visible(False)

        pygame.font.init()
        self.__render_perf__ = False

        # ",,"
        font_name = "consolas,monaco,courier,arial,helvetica"

        font_size_std = int(self.__height__ / 10.0)
        font_size_detail = int(self.__height__ / 12.0)
        font_size_loading = int(self.__height__ / 4.0)

        self.__font__ = pygame.font.Font(
            "./assets/fonts/LiberationMono-Bold.ttf", font_size_std)
        self.__detail_font__ = pygame.font.Font(
            "./assets/fonts/LiberationMono-Bold.ttf", font_size_detail)
        self.__loading_font__ = pygame.font.SysFont(
            font_name, font_size_loading, True, False)
        self.__show_boot_screen__()

        self.__aircraft__ = Aircraft()

        self.__pixels_per_degree_y__ = (
            self.__height__ / HeadsUpDisplay.DEGREES_OF_PITCH) * HeadsUpDisplay.PITCH_DEGREES_DISPLAY_SCALER

        self.__ahrs_not_available_element__ = hud_elements.AhrsNotAvailable(
            HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))


        bottom_compass_element = hud_elements.CompassAndHeadingBottomElement(
                HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__detail_font__, (self.__width__, self.__height__))
        adsb_target_bug_element = hud_elements.AdsbTargetBugs(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__,
                                     (self.__width__, self.__height__), self.__configuration__)
        adsb_onscreen_reticle_element = hud_elements.AdsbOnScreenReticles(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__,
                                              self.__font__, (self.__width__, self.__height__), self.__configuration__)
        
        traffic_only_view = [
            bottom_compass_element,
            adsb_target_bug_element,
            adsb_onscreen_reticle_element
        ]

        traffic_listing_view = [
            hud_elements.AdsbTrafficListing(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__detail_font__,
                                     (self.__width__, self.__height__), self.__configuration__)
        ]

        ahrs_view = [
            hud_elements.LevelReference(
                HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__detail_font__, (self.__width__, self.__height__)),
            hud_elements.ArtificialHorizon(
                HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__detail_font__, (self.__width__, self.__height__)),
            bottom_compass_element,
            hud_elements.Altitude(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__,
                                  self.__detail_font__, (self.__width__, self.__height__)),
            hud_elements.SkidAndGs(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__,
                                   self.__detail_font__, (self.__width__, self.__height__)),
            hud_elements.RollIndicator(
                HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__)),
        ]

        blank_view = []

        self.__hud__views__ = [
            traffic_only_view,
            ahrs_view,
            traffic_listing_view,
            blank_view
        ]

        self.__view_index__ = 0

        self.__perf_task__ = RecurringTask("PerfData", 5, self.__render_perf__)

    def __show_boot_screen__(self):
        texture = self.__loading_font__.render("BOOTING", True, display.RED)
        text_width, text_height = texture.get_size()
        self.__backpage_framebuffer__.blit(texture, ((
            self.__width__ >> 1) - (text_width >> 1), (self.__height__ >> 1) - (text_height >> 1)))
        flipped = pygame.transform.flip(
            self.__backpage_framebuffer__, self.__configuration__.flip_horizonal, self.__configuration__.flip_vertical)
        self.__backpage_framebuffer__.blit(flipped, [0, 0])
        pygame.display.flip()

    def __render_perf__(self):
        print '--------------'
        for element in self.__hud__views__[self.__view_index__]:
            print element.task_timer.to_string()


if __name__ == '__main__':
    hud = HeadsUpDisplay()
    sys.exit(hud.run())
