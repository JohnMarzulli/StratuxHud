#!/usr/bin/env python

import argparse
import datetime
import json
import math
import os
import sys

import pygame
import requests

import lib.display as display
import lib.local_debug as local_debug
import lib.utilities as utilities
import traffic
from aircraft import Aircraft
from configuration import *
from lib.recurring_task import RecurringTask
from lib.task_timer import TaskTimer
import hud_elements
import targets
from views import (adsb_on_screen_reticles, adsb_target_bugs,
                   adsb_traffic_listing, ahrs_not_available, altitude,
                   artificial_horizon, compass_and_heading_bottom_element,
                   groundspeed, heading_target_bugs,
                   level_reference, roll_indicator, skid_and_gs,
                   target_count, time)

# TODO - Add the G-Meter
# TODO - Disable functionality based on the enabled StratuxCapabilities
# TODO - Check for the key existence anyway... cross update the capabilities
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
        """
        Sends the command to the Stratux to level the AHRS.
        """

        url = "http://{0}/cageAHRS".format(
            self.__configuration__.stratux_address())

        try:
            requests.Session().post(url, timeout=2)
        except:
            pass

    def __shutdown_stratux__(self):
        """
        Sends the command to the Stratux to shutdown.
        """

        url = "http://{0}/shutdown".format(
            self.__configuration__.stratux_address())

        try:
            requests.Session().post(url, timeout=2)
        except:
            pass

    def run(self):
        """
        Runs the update/render logic loop.
        """

        clock = pygame.time.Clock()

        try:
            while self.tick(clock):
                pass
        finally:
            self.__connection_manager__.shutdown()
            pygame.display.quit()

        sys.exit()

    def __render_view_title__(self, text):
        try:
            texture = hud_elements.HudDataCache.get_cached_text_texture(
                text,
                self.__detail_font__,
                display.BLUE,
                display.BLACK,
                True)
            # text_width, text_height = texture.get_size()
            left_border = 0  # int(self.__width__ * 0.1)
            top_border = 0  # text_height
            position = (left_border, top_border)

            self.__backpage_framebuffer__.blit(
                texture, position)
        except:
            pass

    def __is_ahrs_view__(self, view):
        """
        Does any element in this view use AHRS?

        Arguments:
            view {AhrsElement[] or AdsbElement[]} -- The collection of view elements.

        Returns:
            bool -- True is any element uses ADSB.
        """

        if view is None or len(view) < 1:
            return False

        is_ahrs_view = False

        for hud_element in view:
            is_ahrs_view = is_ahrs_view or hud_element.uses_ahrs()

        return is_ahrs_view

    def tick(self, clock):
        """
        Run for a single frame.

        Arguments:
            clock {pygame.time.Clock} -- game/frame clock

        Returns:
            bool -- True if the code should run for another tick.
        """

        try:
            if not self.__handle_input__():
                return False

            self.orient_perf.start()
            orientation = self.__aircraft__.get_orientation()
            self.orient_perf.stop()

            hud_elements.HudDataCache.update_traffic_reports()

            self.__backpage_framebuffer__.fill(display.BLACK)

            self.render_perf.start()

            view_name, view = self.__hud_views__[self.__view_index__]
            self.__render_view_title__(view_name)

            view_uses_ahrs = self.__is_ahrs_view__(view)

            try:
                if view_uses_ahrs and not self.__aircraft__.is_ahrs_available():
                    self.__ahrs_not_available_element__.render(
                        self.__backpage_framebuffer__, orientation)
                else:
                    # Order of drawing is important
                    # The pitch lines are drawn before the other
                    # reference information so they will be pushed to the
                    # background.
                    # The reference text is also intentionally
                    # drawn with a black background
                    # to overdraw the pitch lines
                    # and improve readability
                    for hud_element in view:
                        try:
                            hud_element.render(
                                self.__backpage_framebuffer__, orientation)
                        except Exception as e:
                            self.warn("ELEMENT:" + str(e))
            except Exception as e:
                self.warn("LOOP:" + str(e))

            self.render_perf.stop()

            if self.__should_render_perf__:
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

                self.__render_text__(render_perf_text, display.BLACK,
                                     debug_status_left, debug_status_top, 0, display.YELLOW)
                debug_status_top += int(self.__font__.get_height() * 1.1)
                self.__render_text__(orient_perf_text, display.BLACK,
                                     debug_status_left, debug_status_top, 0, display.YELLOW)
        finally:
            # Change the frame buffer
            flipped = pygame.transform.flip(
                self.__backpage_framebuffer__, self.__configuration__.flip_horizontal, self.__configuration__.flip_vertical)
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

    def log(self, text):
        """
        Logs the given text if a logger is available.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_info_message(text)
        else:
            print(text)

    def warn(self, text):
        """
        Logs the given text if a logger is available AS A WARNING.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_warning_message(text)
        else:
            print(text)

    def __build_ahrs_hud_element(self, hud_element_class, use_detail_font=False):
        """
        Builds a generic AHRS HUD element.

        Arguments:
            hud_element_class {class} -- The object type to build.

        Keyword Arguments:
            use_detail_font {bool} -- Should the smaller detail font be used. (default: {False})

        Returns:
            hud_element -- A HUD element ready for rendering.
        """

        try:
            if hud_element_class is None:
                return None

            font = self.__font__

            if use_detail_font:
                font = self.__detail_font__

            return hud_element_class(HeadsUpDisplay.DEGREES_OF_PITCH,
                                     self.__pixels_per_degree_y__, font, (self.__width__, self.__height__))
        except Exception as e:
            self.warn("Unable to build element:" + str(e))
            return None

    def __init__(self, logger):
        """
        Initialize and create a new HUD.
        """

        self.__logger__ = logger

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
        self.__should_render_perf__ = False

        font_name = "consolas,monaco,courier,arial,helvetica"

        font_size_std = int(self.__height__ / 10.0)
        font_size_detail = int(self.__height__ / 12.0)
        font_size_loading = int(self.__height__ / 4.0)

        self.__font__ = pygame.font.Font(
            get_absolute_file_path("./assets/fonts/LiberationMono-Bold.ttf"), font_size_std)
        self.__detail_font__ = pygame.font.Font(
            get_absolute_file_path("./assets/fonts/LiberationMono-Bold.ttf"), font_size_detail)
        self.__loading_font__ = pygame.font.SysFont(
            font_name, font_size_loading, True, False)
        self.__show_boot_screen__()

        self.__aircraft__ = Aircraft()

        self.__pixels_per_degree_y__ = (
            self.__height__ / HeadsUpDisplay.DEGREES_OF_PITCH) * HeadsUpDisplay.PITCH_DEGREES_DISPLAY_SCALER

        self.__ahrs_not_available_element__ = self.__build_ahrs_hud_element(
            ahrs_not_available.AhrsNotAvailable)

        bottom_compass_element = self.__build_ahrs_hud_element(
            compass_and_heading_bottom_element.CompassAndHeadingBottomElement, True)
        adsb_target_bug_element = adsb_target_bugs.AdsbTargetBugs(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__,
                                                                  (self.__width__, self.__height__), self.__configuration__)
        adsb_onscreen_reticle_element = adsb_on_screen_reticles.AdsbOnScreenReticles(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__,
                                                                                     self.__font__, (self.__width__, self.__height__), self.__configuration__)
        altitude_element = self.__build_ahrs_hud_element(
            altitude.Altitude, True)
        time_element = self.__build_ahrs_hud_element(time.Time, True)
        groundspeed_element = self.__build_ahrs_hud_element(
            groundspeed.Groundspeed, True)

        traffic_only_view = [
            bottom_compass_element,
            adsb_target_bug_element,
            adsb_onscreen_reticle_element
        ]

        traffic_listing_view = [
            adsb_traffic_listing.AdsbTrafficListing(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__detail_font__,
                                                    (self.__width__, self.__height__), self.__configuration__)
        ]

        norden_view = [
            bottom_compass_element,
            heading_target_bugs.HeadingTargetBugs(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__detail_font__,
                                                  (self.__width__, self.__height__), self.__configuration__),
            # Draw the ground speed and altitude last so they
            # will appear "on top".
            self.__build_ahrs_hud_element(target_count.TargetCount, True),
            groundspeed_element,
            altitude_element
        ]

        ahrs_view = [
            self.__build_ahrs_hud_element(
                level_reference.LevelReference, True),
            self.__build_ahrs_hud_element(
                artificial_horizon.ArtificialHorizon, True),
            bottom_compass_element,
            altitude_element,
            self.__build_ahrs_hud_element(skid_and_gs.SkidAndGs, True),
            self.__build_ahrs_hud_element(roll_indicator.RollIndicator, True),
            groundspeed_element
        ]

        # Yes... I know. It is the "blank" view... but has something...
        blank_view = [time_element]

        self.__hud_views__ = [
            ("Traffic", traffic_only_view),
            ("AHRS", ahrs_view),
            ("ADSB List", traffic_listing_view),
            ("Norden", norden_view),
            ("Time", blank_view),
            ("", [])
        ]

        self.__view_index__ = 0

        logger = None

        if self.__logger__ is not None:
            logger = self.__logger__.logger

    def __show_boot_screen__(self):
        """
        Renders a BOOTING screen.
        """

        texture = self.__loading_font__.render("BOOTING", True, display.RED)
        text_width, text_height = texture.get_size()
        self.__backpage_framebuffer__.blit(texture, ((
            self.__width__ >> 1) - (text_width >> 1), (self.__height__ >> 1) - (text_height >> 1)))
        flipped = pygame.transform.flip(
            self.__backpage_framebuffer__, self.__configuration__.flip_horizontal, self.__configuration__.flip_vertical)
        self.__backpage_framebuffer__.blit(flipped, [0, 0])
        pygame.display.flip()

    def __handle_input__(self):
        """
        Top level handler for keyboard input.

        Returns:
            bool -- True if the loop should continue, False if it should quit.
        """

        for event in pygame.event.get():
            if not self.__handle_key_event__(event):
                return False

        self.__clamp_view__()

        return True

    def __handle_key_event__(self, event):
        """
        Handles a keyboard/keypad press event.

        Arguments:
            event {pygame.event} -- The event from the keyboard.

        Returns:
            bool -- True if the loop should continue, False if it should quit.
        """

        if event.type == pygame.QUIT:
            utilities.shutdown()
            return False

        if event.type != pygame.KEYUP:
            return True

        if event.key in [pygame.K_ESCAPE]:
            utilities.shutdown(0)
            if not local_debug.is_debug():
                self.__shutdown_stratux__()

            return False

        # Quit to terminal only.
        if event.key in [pygame.K_q]:
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

        if event.key in [pygame.K_DELETE, pygame.K_PERIOD, pygame.K_KP_PERIOD]:
            targets.TARGET_MANAGER.clear_targets()

        if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
            orientation = self.__aircraft__.get_orientation()
            targets.TARGET_MANAGER.add_target(
                orientation.position[0], orientation.position[1], orientation.alt)
            targets.TARGET_MANAGER.save()

        if event.key in [pygame.K_EQUALS, pygame.K_KP_EQUALS]:
            self.__should_render_perf__ = not self.__should_render_perf__

        return True

    def __clamp_view__(self):
        """
        Makes sure that the view index is within bounds.
        """

        if self.__view_index__ >= (len(self.__hud_views__)):
            self.__view_index__ = 0

        if self.__view_index__ < 0:
            self.__view_index__ = (len(self.__hud_views__) - 1)


if __name__ == '__main__':
    hud = HeadsUpDisplay(None)
    sys.exit(hud.run())
