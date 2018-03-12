#!/usr/bin/env python

import math
import json
import os
import sys
import random
import argparse
import datetime
import pygame
import display
import traffic
from configuration import *
from aircraft import Aircraft
import hud_elements
from lib.task_timer import TaskTimer

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

    def run(self):
        clock = pygame.time.Clock()

        try:
            while self.tick(clock):
                pass
        finally:
            self.__connection_manager__.shutdown()
            pygame.display.quit()
            
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

        clock.tick(MAX_FRAMERATE)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        keys_pressed = pygame.key.get_pressed()
        if keys_pressed[pygame.K_q] or keys_pressed[pygame.K_ESCAPE]:
            return False
        
        if keys_pressed[pygame.K_r]:
            self.render_perf.reset()
            self.orient_perf.reset()
            
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
                self.__level_reference_hud_element__.render(self.__backpage_framebuffer__, orientation) # 2, 1ms
                self.__pitch_hud_element__.render(self.__backpage_framebuffer__, orientation) # 24, 6ms
                self.__compass_element__.render(self.__backpage_framebuffer__, orientation) # 18ms, 16ms, 12ms
                self.__altitude_element__.render(self.__backpage_framebuffer__, orientation) # 1ms, 1ms (better quality)
                self.__skid_and_g_element__.render(self.__backpage_framebuffer__, orientation) # 1ms, 1ms (better quality)
                self.__roll_element__.render(self.__backpage_framebuffer__, orientation) # 1ms, 1ms (better quality) 
                self.__adsb_traffic_text_element__.render(self.__backpage_framebuffer__, orientation) #1.5ms/plane
                self.__adsb_onscreen_targets_elements__.render(self.__backpage_framebuffer__, orientation)

                # print '--------------'
                # print self.__level_reference_hud_element__.task_timer.to_string()
                # print self.__pitch_hud_element__.task_timer.to_string()
                # print self.__compass_element__.task_timer.to_string()
                # print self.__altitude_element__.task_timer.to_string()
                # print self.__skid_and_g_element__.task_timer.to_string()
                # print self.__roll_element__.task_timer.to_string()
                # print self.__adsb_traffic_text_element__.task_timer.to_string()
                # print self.__adsb_onscreen_targets_elements__.task_timer.to_string()
            except:
                pass
        else:
            # Should do this if the signal is lost...
            self.__ahrs_not_available_element__.render(self.__backpage_framebuffer__, orientation) # 1ms

        self.render_perf.stop()

        debug_status_left = int(self.__width__ >> 1)
        debug_status_top = int(self.__height__ * 0.8)
        self.__render_text__(self.render_perf.to_string(), display.BLACK, debug_status_left, debug_status_top, 0, display.YELLOW)
        debug_status_top += int(self.__font__.get_height() * 1.5)
        self.__render_text__(self.orient_perf.to_string(), display.BLACK, debug_status_left, debug_status_top, 0, display.YELLOW)

        # Change the frame buffer
        flipped = pygame.transform.flip(
            self.__backpage_framebuffer__, self.__configuration__.flip_horizonal, self.__configuration__.flip_vertical)
        self.__backpage_framebuffer__.blit(flipped, [0, 0])
        pygame.display.flip()

        return True

    def __render_text__(self, text, color, position_x, position_y, roll, background_color=None):
        """
        Renders the text with the results centered on the given
        position.
        """

        rendered_text = self.__font__.render(
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
        self.__connection_manager__ = traffic.ConnectionManager(adsb_traffic_address)

        self.__backpage_framebuffer__, screen_size = display.display_init()  # args.debug)
        self.__width__, self.__height__ = screen_size
        pygame.mouse.set_visible(False)

        pygame.font.init()

        font_name = "consolas,arial,helvetica"

        self.__font__ = pygame.font.SysFont(font_name, int(self.__height__ / 20.0), True, False)
        self.__detail_font__ = pygame.font.SysFont(font_name, int(self.__height__ / 20.0), False, False)

        self.__aircraft__ = Aircraft()

        self.__pixels_per_degree_y__ = (self.__height__ / HeadsUpDisplay.DEGREES_OF_PITCH) * HeadsUpDisplay.PITCH_DEGREES_DISPLAY_SCALER

        self.__ahrs_not_available_element__ = hud_elements.AhrsNotAvailable(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__level_reference_hud_element__ = hud_elements.LevelReference(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__pitch_hud_element__ = hud_elements.ArtificialHorizon(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__compass_element__ = hud_elements.CompassAndHeading(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__altitude_element__ = hud_elements.Altitude(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__skid_and_g_element__ = hud_elements.SkidAndGs(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__roll_element__ = hud_elements.RollIndicator(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__))
        self.__adsb_traffic_text_element__ = hud_elements.AdsbListing(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__), self.__configuration__)
        self.__adsb_onscreen_targets_elements__ = hud_elements.AdsbOnScreenReticles(HeadsUpDisplay.DEGREES_OF_PITCH, self.__pixels_per_degree_y__, self.__font__, (self.__width__, self.__height__), self.__configuration__)
        

if __name__ == '__main__':
    hud = HeadsUpDisplay()
    sys.exit(hud.run())
