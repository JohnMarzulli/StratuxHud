"""
Helpers for running the scopes on their own (python -m views.<scope>)
with example data, for development.
"""

import json

import pygame

from common_utils.tasks import IntermittentTask
from configuration import configuration
from data_sources.ahrs_data import AhrsData
from data_sources.airports import load_example_airports, load_example_flight_rules
from data_sources.nexrad import NexradClient

EXAMPLE_REFLECTIVITY_FILES = [
    "../test_data/faa_sample_reflectivity.json",
    "../test_data/reflectivity_response.json",
    "../test_data/2025-03-14_incomplete_bins.json",
    "../test_data/large_response.json",
]


def load_example_data():
    """
    Loads example airports, flight rules, and NEXRAD reflectivity.
    """
    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    for test_data_file in EXAMPLE_REFLECTIVITY_FILES:
        full_file_path = configuration.get_absolute_file_path(test_data_file)

        with open(full_file_path) as json_test_data_file:
            nexrad_client.inject(json.loads(json_test_data_file.read()))

    load_example_flight_rules()
    load_example_airports()


def auto_zooming(scope_type):
    """
    A version of the scope that alternates between zooming out and
    zooming in every 10 seconds, by sending the same key presses the
    user would.
    """

    class AutoZoomingScope(scope_type):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.__zoom_out_next__ = True
            self.__auto_zoom_task__ = IntermittentTask(
                "Debug Auto Zoom", 10.0, self.__send_zoom_command__, None
            )

        def __send_zoom_command__(self):
            key = pygame.K_UP if self.__zoom_out_next__ else pygame.K_DOWN
            print(f"Debug zoom {'out' if self.__zoom_out_next__ else 'in'}")

            self.handle_events([pygame.event.Event(pygame.KEYUP, key=key)])
            self.__zoom_out_next__ = not self.__zoom_out_next__

        def render(self, framebuffer: pygame.Surface, orientation: AhrsData):
            self.__auto_zoom_task__.run()

            super().render(framebuffer, orientation)

    AutoZoomingScope.__name__ = f"AutoZooming{scope_type.__name__}"

    return AutoZoomingScope
