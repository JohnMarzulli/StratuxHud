#!/usr/bin/env python

import contextlib
import json
import sys
from time import sleep

import pygame
import requests

from common_utils import local_debug, system_tools
from common_utils.logger import HudLogger
from common_utils.task_timer import RollingStats, TaskProfiler
from common_utils.tasks import IntermittentTask, RecurringTask
from configuration import configuration, configuration_server
from configuration.configuration import CONFIGURATION
from core_services import breadcrumbs, zoom_tracker
from data_sources import aithre, declination, targets
from data_sources.ahrs_data import AhrsData
from data_sources.aircraft import Aircraft
from data_sources.data_cache import HudDataCache
from data_sources.traffic import AdsbTrafficClient
from rendering import colors, display, drawing, text_renderer
# Due to the way we import the name of the class to be instantiated
# from the configuration, all of the element class names need
# to be imported EVEN if the compiler tries to tell you
# they are not needed.
from views import (adsb_on_screen_reticles, adsb_target_bugs,
                   adsb_target_bugs_only, adsb_top_view_scope,
                   adsb_traffic_listing, ahrs_not_available, altitude,
                   artificial_horizon, compass_and_heading_bottom_element,
                   gps_not_available, groundspeed, heading_target_bugs,
                   hud_elements, level_reference, roll_indicator, skid_and_gs,
                   system_info, time, traffic_not_available)

STANDARD_FONT = "../assets/fonts/LiberationMono-Bold.ttf"
LOADING_FONT = "../assets/fonts/LiberationMono-Regular.ttf"


def __send_stratux_post__(
    ending_url
):
    """
    Sends a post call to the given ending portion of the URL

    Arguments:
        ending_url {str} -- The ending portion of the url. "cageAHRS" will result in "/cageAHRS"

    Returns:
        bool -- True if the call occurred.
    """
    if ending_url is None:
        return False

    url = "http://{0}/{1}".format(
        CONFIGURATION.stratux_address(),
        ending_url)

    try:
        requests.Session().post(url, timeout=2)

        return True
    except Exception:

        return False


def __get_default_text_background_color__() -> list:
    return colors.BLACK if display.IS_OPENGL else None


class HeadsUpDisplay(object):
    """
    Class to handle the HUD work...
    """

    def __level_ahrs__(
        self
    ):
        """
        Sends the command to the Stratux to level the AHRS.
        """

        __send_stratux_post__("cageAHRS")

    def __reset_traffic_manager__(
        self
    ):
        """
        Resets the traffic manager to essentially reset the receiver unit.
        """
        with contextlib.suppress(Exception):
            AdsbTrafficClient.INSTANCE.reset_traffic_manager()

    def __shutdown_stratux__(
        self
    ):
        """
        Sends the command to the Stratux to shutdown.
        """

        __send_stratux_post__("shutdown")

    def run(
        self
    ):
        """
        Runs the update/render logic loop.
        """

        self.log(f'Initialized scresen size to {self.__width__}x{self.__height__}')

        # Make sure that the disclaimer is visible for long enough.
        sleep(5)

        clock = pygame.time.Clock()

        try:
            while self.tick(clock):
                pass
        finally:
            pygame.display.quit()

        return 0

    def __render_view_title__(
        self,
        text: str,
        surface
    ):
        text_renderer.render_text(
            surface,
            self.__detail_font__,
            text,
            [0, 0],
            colors.BLUE,
            colors.BLACK,
            False,
            0.5)

    def __is_ahrs_view__(
        self,
        view
    ):
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

    def get_hud_views(
        self
    ) -> list:
        """
        Get the set of current HUD views.

        Returns:
            list -- The list of views currently loaded.
        """
        return self.__hud_views__

    def tick(
        self,
        clock
    ):
        """
        Run for a single frame.

        Arguments:
            clock {pygame.time.Clock} -- game/frame clock

        Returns:
            bool -- True if the code should run for another tick.
        """

        current_fps = 0  # initialize up front avoids exception

        try:
            if not self.__handle_input__():
                return False

            orientation = self.__aircraft__.get_orientation()
            self.__update_declination_task__.run()

            view_name, view, view_uses_ahrs = self.__hud_views__[
                CONFIGURATION.get_view_index()]
            show_unavailable = view_uses_ahrs and not self.__aircraft__.is_ahrs_available()

            current_fps = int(clock.get_fps())

            surface = self.__display__.get_framebuffer()
            self.__display__.clear()

            self.__render_view_title__(view_name, surface)

            # Order of drawing is important
            # The pitch lines are drawn before the other
            # reference information so they will be pushed to the
            # background.
            # The reference text is also intentionally
            # drawn with a black background
            # to overdraw the pitch lines
            # and improve readability
            with TaskProfiler("Render::AllElements"):
                try:
                    [self.__render_view_element__(hud_element, orientation) for hud_element in view]
                except Exception as e:
                    self.warn(f"LOOP:{e}")
                if show_unavailable:
                    self.__ahrs_not_available_element__.render(surface, orientation)

            if self.__should_render_perf__:
                debug_status_left = int(self.__width__ * 0.9)
                debug_status_top = int(self.__height__ * 0.1)
                render_perf_text = f'{current_fps}fps'

                self.__render_text__(
                    render_perf_text,
                    colors.BLACK,
                    [debug_status_left, debug_status_top],
                    colors.YELLOW)

            self.__render_perf_task__.run()
        finally:
            # Change the frame buffer
            if CONFIGURATION.flip_horizontal or CONFIGURATION.flip_vertical:
                flipped = pygame.transform.flip(
                    surface,
                    CONFIGURATION.flip_horizontal,
                    CONFIGURATION.flip_vertical)
                surface.blit(flipped, [0, 0])

            self.__display__.flip()
            self.__fps__.push(current_fps)

            clock.tick(configuration.MAX_FRAMERATE)

        return True

    def __render_view_element__(
        self,
        hud_element,
        orientation: AhrsData
    ):
        element_name = str(hud_element)
        element_name = element_name.split(" object")[0]
        element_name = element_name.split('<')[-1]

        with TaskProfiler(element_name):
            surface = pygame.display.get_surface()
            try:
                hud_element.render(surface, orientation)
            except Exception as e:
                self.warn(f'ELEMENT {element_name} EX:{e}')

    def __render_text__(
        self,
        text: str,
        color: list,
        position: list,
        background_color: list = __get_default_text_background_color__()
    ) -> list:
        """
        Renders the text with the results centered on the given
        position.
        """
        return text_renderer.render_text(
            pygame.display.get_surface(),
            self.__detail_font__,
            text,
            position,
            color,
            background_color)

    def log(
        self,
        text: str
    ):
        """
        Logs the given text if a logger is available.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_info_message(text)
        else:
            print(text)

    def warn(
        self,
        text: str
    ):
        """
        Logs the given text if a logger is available AS A WARNING.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_warning_message(text)
        else:
            print(text)

    def __build_ahrs_hud_element__(
        self,
        hud_element_class,
        use_detail_font: bool = False,
        reduced_visuals: bool = False
    ):
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

            font = self.__detail_font__ if use_detail_font else self.__font__

            return hud_element_class(
                CONFIGURATION.get_degrees_of_pitch(),
                self.__pixels_per_degree_y__,
                font,
                (self.__width__, self.__height__),
                reduced_visuals)
        except Exception as e:
            self.warn("Unable to build element {0}:{1}".format(hud_element_class, e))
            return None

    def __load_view_elements__(
        self
    ) -> str:
        """
        Loads the list of available view elements from the configuration
        file. Returns it as a map of the element name (Human/kind) to
        the Python object that instantiates it, and if it uses the
        "detail" (aka Large) font or not.

        Returns:
            map -- Keyed by element name, elements are tuples of object name / boolean
        """

        view_elements = {}
        with open(configuration.VIEW_ELEMENTS_FILE) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)

            for view_element_name in json_config:
                namespace = json_config[view_element_name]['class'].split('.')
                file_module = getattr(sys.modules['views'], namespace[0])
                class_name = getattr(file_module, namespace[1])
                view_elements[view_element_name] = (class_name, json_config[view_element_name]['detail_font'])

        return view_elements

    def __load_views__(
        self,
        view_elements: list,
        reduced_visuals: bool = False
    ) -> list:
        """
        Returns a list of views that can be used by the HUD

        Arguments:
            view_elements {map} -- Dictionary keyed by element name containing the info to instantiate the element.

        Returns:
            array -- Array of tuples. Each element is a tuple of the name of the view and an array of the elements that make the view.
        """

        hud_views = []
        existing_elements = {}
        elements_requested = 0

        with open(configuration.VIEWS_FILE) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)

            for view in json_config['views']:
                try:
                    view_name = view['name']
                    element_names = view['elements']
                    new_view_elements = []

                    for element_name in element_names:
                        elements_requested += 1
                        element_config = view_elements[element_name]
                        element_hash_name = f"{element_config[0]}{element_config[1]}"

                        # Instantiating multiple elements of the same type/font
                        # REALLY chews up memory.. and there is no
                        # good reason to use new instances anyway.
                        if element_hash_name not in existing_elements:
                            new_element = self.__build_ahrs_hud_element__(
                                element_config[0],
                                element_config[1],
                                reduced_visuals)
                            existing_elements[element_hash_name] = new_element

                        new_view_elements.append(
                            existing_elements[element_hash_name])

                    is_ahrs_view = self.__is_ahrs_view__(new_view_elements)
                    hud_views.append((view_name, new_view_elements, is_ahrs_view))
                except Exception as ex:
                    self.log(f"While attempting to load view={view}, EX:{ex}")
        self.log(f"While loading, {elements_requested} elements were requested, with {len(existing_elements.keys())} unique being created.")

        return hud_views

    def __build_hud_views__(
        self,
        reduced_visuals: bool = False
    ) -> list:
        """
        Returns the built object of the views.

        Returns:
            array -- Array of tuples. Each element is a tuple of the name of the view and an array of the elements that make the view.
        """

        view_elements = self.__load_view_elements__()
        return self.__load_views__(view_elements, reduced_visuals)

    def __update_traffic_reports__(
        self
    ):
        HudDataCache.update_traffic_reports()
        HudDataCache.update_nearby_traffic_reports()

    def __update_aithre__(
        self
    ):
        if not CONFIGURATION.aithre_enabled:
            return

        if aithre.AithreClient.INSTANCE is not None:
            try:
                aithre.AithreClient.INSTANCE.update_aithre()

            except Exception:
                self.warn("Error attempting to update Aithre sensor values")

    def __update_zoom__(
        self
    ):
        orientation = self.__aircraft__.get_orientation()

        zoom_tracker.INSTANCE.update(orientation)

    def __update_groundtrack__(
        self
    ):
        orientation = self.__aircraft__.get_orientation()

        breadcrumbs.INSTANCE.update(orientation)

    def __update_declination__(
        self
    ):
        updated_declination = None
        orientation = self.__aircraft__.get_orientation()

        if orientation is not None \
                and orientation.gps_online \
                and orientation.position is not None \
                and orientation.position[0] is not None \
                and orientation.position[1] is not None:

            updated_declination = declination.Declination.get_declination(
                orientation.position[0],
                orientation.position[1])

        HudDataCache.DECLINATION = updated_declination

    def __render_perf__(
        self
    ):
        TaskProfiler.log(self.__logger__)
        self.__perf_log_count = self.__perf_log_count + 1

        if self.__perf_log_count >= 3:
            TaskProfiler.reset()
            self.__perf_log_count = 0

    def __init__(
        self,
        logger: HudLogger,
        force_fullscreen: bool = False,
        force_software: bool = False,
        reduced_visuals: bool = False
    ):
        """
        Initialize and create a new HUD.

        Args:
            logger (HudLogger): The logger for the HUD
            force_fullscreen (bool, optional): Do we want to force fullscreen mode?. Defaults to False.
            force_software (bool, optional): Do we want to force the software renderer to be user? Defaults to False.
        """

        self.__update_declination_task__ = IntermittentTask(
            "Update Declination",
            60.0,
            self.__update_declination__,
            logger)

        self.__render_perf_task__ = IntermittentTask(
            "Render Performance Data",
            15.0,
            self.__render_perf__,
            logger)

        self.__logger__ = logger
        self.__fps__ = RollingStats('FPS')
        self.__texture_cache_size__ = RollingStats('TextureCacheSize')
        self.__texture_cache_misses__ = RollingStats('TextureCacheMisses')
        self.__texture_cache_purges__ = RollingStats('TextureCachePurges')

        self.__fps__.push(0)

        self.__display__ = display.Display(
            force_fullscreen,
            force_software)
        pygame.display.set_caption(f"StratuxHUD ({drawing.renderer.RENDERER_NAME})")
        self.__width__, self.__height__ = self.__display__.size

        pygame.mouse.set_visible(False)

        pygame.font.init()
        self.__should_render_perf__ = False

        font_size_std = int(self.__height__ / 10.0)
        font_size_detail = int(self.__height__ / 12.0)
        font_size_loading = int(self.__height__ / 4.0)

        self.__font__ = pygame.font.Font(
            configuration.get_absolute_file_path(STANDARD_FONT),
            font_size_std)
        self.__detail_font__ = pygame.font.Font(
            configuration.get_absolute_file_path(STANDARD_FONT),
            font_size_detail)
        self.__loading_font__ = pygame.font.Font(
            configuration.get_absolute_file_path(LOADING_FONT),
            font_size_loading)
        self.__show_boot_screen__()

        self.__aircraft__ = Aircraft(self.__logger__)

        self.__pixels_per_degree_y__ = int((self.__height__ / CONFIGURATION.get_degrees_of_pitch()) * CONFIGURATION.get_pitch_degrees_display_scaler())

        self.__ahrs_not_available_element__ = self.__build_ahrs_hud_element__(
            ahrs_not_available.AhrsNotAvailable)

        self.__hud_views__ = self.__build_hud_views__(reduced_visuals)

        self.__perf_log_count = 0

        try:
            self.web_server = configuration_server.HudServer()
        except Exception as ex:
            logger.get_logger().info(f"Unable to start the remote control server: {ex}")
            self.web_server = None

        if self.web_server is not None:
            RecurringTask(
                "rest_host",
                0.1,
                self.web_server.run,
                logger.get_logger())

        RecurringTask(
            "update_traffic",
            0.1,
            self.__update_traffic_reports__,
            logger.get_logger())

        RecurringTask(
            "update_aithre",
            5.0,
            self.__update_aithre__,
            logger.get_logger())

        RecurringTask(
            "update_zoom",
            1.0,
            self.__update_zoom__,
            logger.get_logger())

        RecurringTask(
            "update_groundtrack",
            breadcrumbs.MAXIMUM_POSITION_SAMPLE_RATE,
            self.__update_groundtrack__,
            logger.get_logger())

    def __show_boot_screen__(
        self
    ):
        """
        Renders a BOOTING screen.
        """

        disclaimer_text = [
            'Not intended as',
            'a primary collision evasion',
            'or flight instrument system.',
            'For advisory only.']

        surface = pygame.display.get_surface()

        key, texture, size = text_renderer.get_or_create_text_texture(
            self.__loading_font__,
            "LOADING",
            colors.RED,
            colors.BLACK)

        text_renderer.render_cached_texture(
            surface,
            key,
            [(self.__width__ >> 1) - (size[0] >> 1), self.__detail_font__.get_height()])

        y_pos = (self.__height__ >> 2) + (self.__height__ >> 3)
        for text in disclaimer_text:
            key, texture, size = text_renderer.get_or_create_text_texture(
                self.__detail_font__,
                text,
                colors.YELLOW,
                colors.BLACK)

            text_width, text_height = size

            text_renderer.render_cached_texture(
                surface,
                key,
                [(self.__width__ >> 1) - (text_width >> 1), y_pos])

            y_pos += text_height + (text_height >> 3)

        key, texture, size = text_renderer.get_or_create_text_texture(
            self.__detail_font__,
            f'Version {configuration.VERSION}',
            colors.GREEN,
            colors.BLACK)

        text_width, text_height = size

        text_renderer.render_cached_texture(
            surface,
            key,
            [(self.__width__ >> 1) - (text_width >> 1), self.__height__ - text_height])

        flipped = pygame.transform.flip(
            surface,
            CONFIGURATION.flip_horizontal,
            CONFIGURATION.flip_vertical)
        surface.blit(flipped, [0, 0])
        pygame.display.flip()

    def __handle_input__(
        self
    ) -> bool:
        """
        Top level handler for keyboard input.

        Returns:
            bool -- True if the loop should continue, False if it should quit.
        """

        events = pygame.event.get()
        event_handling_responses = map(self.__handle_key_event__, events)

        return False not in event_handling_responses

    def __handle_key_event__(
        self,
        event
    ) -> bool:
        """
        Handles a keyboard/keypad press event.

        Arguments:
            event {pygame.event} -- The event from the keyboard.

        Returns:
            bool -- True if the loop should continue, False if it should quit.
        """

        if event.type == pygame.QUIT:
            system_tools.shutdown()
            return False

        if event.type != pygame.KEYUP:
            return True

        if event.key in [pygame.K_ESCAPE]:
            system_tools.shutdown(0)
            if local_debug.IS_PI:
                self.__shutdown_stratux__()

            return False

        # Quit to terminal only.
        if event.key in [pygame.K_q]:
            return False

        if event.key in [pygame.K_KP_PLUS, pygame.K_PLUS, pygame.K_UP]:
            CONFIGURATION.next_view(self.__hud_views__)

        if event.key in [pygame.K_KP_MINUS, pygame.K_MINUS, pygame.K_DOWN]:
            CONFIGURATION.previous_view(self.__hud_views__)

        if event.key in [pygame.K_BACKSPACE]:
            self.__level_ahrs__()

        if event.key in [pygame.K_DELETE, pygame.K_PERIOD, pygame.K_KP_PERIOD]:
            targets.TARGET_MANAGER.clear_targets()

        if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
            orientation = self.__aircraft__.get_orientation()
            targets.TARGET_MANAGER.add_target(
                orientation.position[0],
                orientation.position[1],
                orientation.alt)
            targets.TARGET_MANAGER.save()

        if event.key in [pygame.K_EQUALS, pygame.K_KP_EQUALS]:
            self.__should_render_perf__ = not self.__should_render_perf__

        if event.key in [pygame.K_KP0, pygame.K_0, pygame.K_INSERT]:
            self.__reset_traffic_manager__()

        return True


if __name__ == '__main__':
    hud = HeadsUpDisplay(None)
    sys.exit(hud.run())
