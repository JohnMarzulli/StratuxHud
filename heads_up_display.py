#!/usr/bin/env python

import argparse
import datetime
import json
import math
import os
import sys
from time import sleep

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
import restful_host
from views import (adsb_on_screen_reticles, adsb_target_bugs,
                   adsb_traffic_listing, ahrs_not_available, altitude,
                   artificial_horizon, compass_and_heading_bottom_element,
                   groundspeed, heading_target_bugs,
                   level_reference, roll_indicator, skid_and_gs,
                   system_info,
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
            CONFIGURATION.stratux_address())

        try:
            requests.Session().post(url, timeout=2)
        except:
            pass

    def __shutdown_stratux__(self):
        """
        Sends the command to the Stratux to shutdown.
        """

        url = "http://{0}/shutdown".format(
            CONFIGURATION.stratux_address())

        try:
            requests.Session().post(url, timeout=2)
        except:
            pass

    def run(self):
        """
        Runs the update/render logic loop.
        """

        # Make sure that the disclaimer is visible for long enough.
        sleep(5)

        clock = pygame.time.Clock()

        try:
            while self.tick(clock):
                pass
        finally:
            self.__connection_manager__.shutdown()
            pygame.display.quit()

        return 0

    def __render_view_title__(self, text):
        try:
            texture = hud_elements.HudDataCache.get_cached_text_texture(
                text,
                self.__detail_font__,
                display.BLUE,
                display.BLACK,
                False)

            left_border = 0
            top_border = 0
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

            self.__backpage_framebuffer__.fill(display.BLACK)

            self.render_perf.start()

            view_name, view, view_uses_ahrs = self.__hud_views__[
                self.__view_index__]
            self.__render_view_title__(view_name)

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

                    render_times = [self.__render_view_element__(
                        hud_element, orientation) for hud_element in view]

                    now = datetime.datetime.utcnow()

                    if (self.__last_perf_render__ is None) or (now - self.__last_perf_render__).total_seconds() > 60:
                        self.__last_perf_render__ = now

                        self.log("---- VIEW ELEMENT RENDER TIMES ----")

                        for element_times in render_times:
                            self.log('RENDER, {}, {}'.format(
                                now, element_times))

                        self.log('CACHE, {}, Textures, {}, {}, {}'.format(
                            now,
                            hud_elements.HudDataCache.get_texture_cache_size(),
                            hud_elements.HudDataCache.get_texture_cache_miss_count(),
                            hud_elements.HudDataCache.get_texture_cache_purge_count()))
                        
                        self.log('CONNECTION MANAGER, {}, ConnectionManager, {}, {}, {}'.format(
                            now,
                            self.__connection_manager__.CONNECT_ATTEMPTS,
                            self.__connection_manager__.SHUTDOWNS,
                            self.__connection_manager__.SILENT_TIMEOUTS))

                        self.log("-----------------------------------")
            except Exception as e:
                self.warn("LOOP:" + str(e))

            self.render_perf.stop()

            if self.__should_render_perf__:
                debug_status_left = int(self.__width__ >> 1)
                debug_status_top = int(self.__height__ * 0.2)
                render_perf_text = self.render_perf.to_string()
                cache_perf_text = self.cache_perf.to_string()
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
                debug_status_top += int(self.__font__.get_height() * 1.1)
                self.__render_text__(cache_perf_text, display.BLACK,
                                     debug_status_left, debug_status_top, 0, display.YELLOW)
        finally:
            # Change the frame buffer
            flipped = pygame.transform.flip(
                self.__backpage_framebuffer__, CONFIGURATION.flip_horizontal, CONFIGURATION.flip_vertical)
            self.__backpage_framebuffer__.blit(flipped, [0, 0])
            pygame.display.flip()
            clock.tick(MAX_FRAMERATE)

        return True

    def __render_view_element__(self, hud_element, orientation):
        element_name = str(hud_element)

        try:
            if element_name not in self.__view_element_timers:
                self.__view_element_timers[element_name] = TaskTimer(
                    element_name)

            timer = self.__view_element_timers[element_name]
            timer.start()
            try:
                hud_element.render(
                    self.__backpage_framebuffer__, orientation)
            except Exception as e:
                self.warn('ELEMENT EX:{}'.format(e))
            timer.stop()
            timer_string = timer.to_string()

            return timer_string
        except Exception as ex:
            self.warn('__render_view_element__ EX:{}'.format(ex))

            return 'Element View Timer Error:{}'.format(ex)

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
            self.warn("Unable to build element {0}:{1}".format(
                hud_element_class, e))
            return None

    def __load_view_elements(self):
        """
        Loads the list of available view elements from the configuration
        file. Returns it as a map of the element name (Human/kind) to
        the Python object that instantiates it, and if it uses the
        "detail" (aka Large) font or not.

        Returns:
            map -- Keyed by element name, elements are tuples of object name / boolean
        """

        view_elements = {}
        with open(VIEW_ELEMENTS_FILE) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)

            for view_element_name in json_config:
                namespace = json_config[view_element_name]['class'].split('.')
                file_module = getattr(sys.modules['views'], namespace[0])
                class_name = getattr(file_module, namespace[1])
                view_elements[view_element_name] = (
                    class_name, json_config[view_element_name]['detail_font'])

        return view_elements

    def __load_views(self, view_elements):
        """
        Returns a list of views that can be used by the HUD

        Arguments:
            view_elements {map} -- Dictionary keyed by element name containing the info to instantiate the element.

        Returns:
            array -- Array of tuples. Each element is a tuple of the name of the view and an array of the elements that make the view. 
        """

        hud_views = []

        with open(VIEWS_FILE) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)

            for view in json_config['views']:
                try:
                    view_name = view['name']
                    element_names = view['elements']
                    new_view_elements = []

                    for element_name in element_names:
                        element_config = view_elements[element_name]
                        new_view_elements.append(self.__build_ahrs_hud_element(
                            element_config[0], element_config[1]))

                    is_ahrs_view = self.__is_ahrs_view__(new_view_elements)
                    hud_views.append(
                        (view_name, new_view_elements, is_ahrs_view))
                except Exception as ex:
                    self.log(
                        "While attempting to load view={}, EX:{}".format(view, ex))

        return hud_views

    def __build_hud_views(self):
        """
        Returns the built object of the views.

        Returns:
            array -- Array of tuples. Each element is a tuple of the name of the view and an array of the elements that make the view. 
        """

        view_elements = self.__load_view_elements()
        return self.__load_views(view_elements)

    def __purge_old_reports__(self):
        self.cache_perf.start()
        hud_elements.HudDataCache.purge_old_traffic_reports()
        self.cache_perf.stop()

    def __update_traffic_reports__(self):
        hud_elements.HudDataCache.update_traffic_reports()

    def __init__(self, logger):
        """
        Initialize and create a new HUD.
        """

        self.__last_perf_render__ = None
        self.__logger__ = logger
        self.__view_element_timers = {}

        self.render_perf = TaskTimer("Render")
        self.orient_perf = TaskTimer("Orient")
        self.cache_perf = TaskTimer("Cache")

        adsb_traffic_address = "ws://{0}/traffic".format(
            CONFIGURATION.stratux_address())
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

        self.__hud_views__ = self.__build_hud_views()

        self.__view_index__ = 0

        logger = None

        if self.__logger__ is not None:
            logger = self.__logger__.logger

        web_server = restful_host.HudServer()
        RecurringTask("rest_host", 0.1, web_server.run, start_immediate=False)
        RecurringTask("purge_old_traffic", 10.0,
                      self.__purge_old_reports__, start_immediate=False)
        RecurringTask("update_traffic", 0.1,
                      self.__update_traffic_reports__, start_immediate=True)

    def __show_boot_screen__(self):
        """
        Renders a BOOTING screen.
        """

        disclaimer_text = ['Not intended as',
                           'a primary collision evasion',
                           'or flight instrument system.',
                           'For advisiory only.']

        texture = self.__loading_font__.render("BOOTING", True, display.RED)
        text_width, text_height = texture.get_size()

        self.__backpage_framebuffer__.blit(texture, ((
            self.__width__ >> 1) - (text_width >> 1), self.__detail_font__.get_height()))

        y = (self.__height__ >> 2) + (self.__height__ >> 3)
        for text in disclaimer_text:
            texture = self.__detail_font__.render(text, True, display.YELLOW)
            text_width, text_height = texture.get_size()
            self.__backpage_framebuffer__.blit(
                texture, ((self.__width__ >> 1) - (text_width >> 1), y))
            y += text_height + (text_height >> 3)

        texture = self.__detail_font__.render(
            'Version {}'.format(VERSION), True, display.GREEN)
        text_width, text_height = texture.get_size()
        self.__backpage_framebuffer__.blit(texture, ((
            self.__width__ >> 1) - (text_width >> 1), self.__height__ - text_height))

        flipped = pygame.transform.flip(
            self.__backpage_framebuffer__, CONFIGURATION.flip_horizontal, CONFIGURATION.flip_vertical)
        self.__backpage_framebuffer__.blit(flipped, [0, 0])
        pygame.display.flip()

    def __handle_input__(self):
        """
        Top level handler for keyboard input.

        Returns:
            bool -- True if the loop should continue, False if it should quit.
        """

        events = pygame.event.get()
        event_handling_repsonses = map(self.__handle_key_event__, events)

        if False in event_handling_repsonses:
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
            self.cache_perf.reset()

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
