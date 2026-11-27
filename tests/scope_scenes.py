"""
Deterministic, headless renders of the top-down scopes.

Used by the golden-frame tests to prove that refactoring the scope
rendering does not change what is drawn. Only public behavior is used
(construct a scope, send key presses, render), so the scenes keep
working as the internals move around.
"""

import json
import os
import sys
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from common_utils import authoritative_time, geo_math, units  # noqa: E402
    from configuration import configuration  # noqa: E402
    from core_services import breadcrumbs  # noqa: E402
    from data_sources.ahrs_data import AhrsData  # noqa: E402
    from data_sources.airports import (  # noqa: E402
        AirportClient,
        load_example_airports,
        load_example_flight_rules,
    )
    from data_sources.data_cache import HudDataCache  # noqa: E402
    from data_sources.nexrad import NexradClient  # noqa: E402
    from data_sources.traffic import Traffic  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(REPO_ROOT, "assets", "fonts", "LiberationMono-Bold.ttf")
FRAME_SIZE = (800, 480)
START = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

SEATTLE = [47.45, -122.30]
PORTLAND = [45.40, -121.90]

REFLECTIVITY_FILES = [
    "faa_sample_reflectivity.json",
    "reflectivity_response.json",
    "large_response.json",
]

_ORIGINAL_GET_SYSTEM_TIME = authoritative_time.get_system_time


class FakeClock:
    def __init__(self):
        self.now = START

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += timedelta(seconds=seconds)


def init_pygame():
    if not pygame.get_init():
        pygame.init()

    if pygame.display.get_surface() is None:
        pygame.display.set_mode(FRAME_SIZE)

    pygame.font.init()

    return pygame.font.Font(FONT_PATH, FRAME_SIZE[1] // 12)


def _patch_clock(stack: ExitStack, clock: FakeClock):
    """
    Modules import get_system_time by name, so patch every copy of it.
    """
    for module in list(sys.modules.values()):
        if getattr(module, "get_system_time", None) is _ORIGINAL_GET_SYSTEM_TIME:
            stack.enter_context(patch.object(module, "get_system_time", clock))


def _traffic_at(identifier, origin, bearing, distance_sm, **extra):
    latitude, longitude = _offset(origin, bearing, distance_sm)
    report = {
        "displayName": identifier,
        "Lat": latitude,
        "Lng": longitude,
        "Alt": extra.pop("altitude", 3000),
        "Distance": distance_sm * units.yards_to_sm,  # raw yards
        "Bearing": bearing,
    }
    report.update(extra)

    return Traffic(identifier, report)


def _offset(origin, bearing, distance_sm):
    """
    Small-distance flat-earth offset; plenty for test fixtures.
    """
    import math

    radians = math.radians(bearing)
    miles_per_degree = 69.0
    d_lat = math.cos(radians) * distance_sm / miles_per_degree
    d_lon = (
        math.sin(radians)
        * distance_sm
        / (miles_per_degree * math.cos(math.radians(origin[0])))
    )

    return origin[0] + d_lat, origin[1] + d_lon


def _prediction(origin, start_bearing, start_distance, track, step_sm, count=4):
    points = []
    position = _offset(origin, start_bearing, start_distance)

    for index in range(count):
        point_position = _offset(list(position), track, step_sm * index)
        points.append(
            {
                "Lat": point_position[0],
                "Lng": point_position[1],
                "Alt": 3000,
                "secondsAhead": index * 30,
                "Track": track,
            }
        )

    return {"type": "straight", "points": points}


def make_traffic(origin):
    """
    A spread of traffic: ahead and behind, near and far, airborne and
    on the ground, with and without a track, with and without a
    prediction, and one just across north from a heading of 350.
    """
    return [
        _traffic_at("N100AH", origin, 20, 1.0, Track=200,
                    Prediction=_prediction(origin, 20, 1.0, 200, 0.4)),
        _traffic_at("N200BH", origin, 200, 1.5, Track=20),
        _traffic_at("N300CL", origin, 100, 0.6, Track=280, altitude=2500,
                    Prediction=_prediction(origin, 100, 0.6, 280, 0.3)),
        _traffic_at("N400GD", origin, 300, 1.8, OnGround=True),
        _traffic_at("N500FR", origin, 60, 4.0, Track=90),
        _traffic_at("N600XX", origin, 160, 12.0, Track=0),
        _traffic_at("N700NN", origin, 10, 1.7, Track=180),
    ]


def make_breadcrumb_trail(origin):
    # Flying north-east, so the trail is behind us to the south-west.
    trail = []

    for index in range(10, 0, -1):
        position = _offset(origin, 210, index * 0.3)
        trail.append([list(position), 1.0 - (index / 11.0)])

    trail.append([list(origin), 1.0])

    return trail


def load_reflectivity():
    for file_name in REFLECTIVITY_FILES:
        with open(os.path.join(REPO_ROOT, "test_data", file_name)) as data_file:
            NexradClient.inject(None, json.load(data_file))


@contextmanager
def scene(display_units: str = units.STATUTE, airports_valid: bool = True):
    """
    Pins down everything a scope render depends on: the clock, the
    display units, airports, traffic, breadcrumbs, and reflectivity.

    Yields the FakeClock so a scene can step through a zoom.
    """
    clock = FakeClock()

    with ExitStack() as stack:
        _patch_clock(stack, clock)
        stack.enter_context(
            patch.object(
                configuration.CONFIGURATION, "get_units", return_value=display_units
            )
        )
        stack.enter_context(
            patch.object(
                configuration.CONFIGURATION,
                "__get_config_value__",
                side_effect=lambda key, default=None: (
                    display_units
                    if key == configuration.Configuration.DISTANCE_UNITS_KEY
                    else default
                ),
            )
        )
        stack.enter_context(
            patch.object(
                AirportClient,
                "__EXPIRATION_DATE__",
                START + timedelta(days=365 if airports_valid else -365),
            )
        )
        stack.enter_context(patch.object(HudDataCache, "RELIABLE_TRAFFIC", []))
        stack.enter_context(
            patch.object(NexradClient, "REFLECTIVITY", {})
        )

        load_example_flight_rules()
        load_example_airports()
        load_reflectivity()

        yield clock


def make_orientation(position, heading):
    orientation = AhrsData()
    orientation.position = list(position)
    orientation.gps_heading = heading
    orientation.compass_heading = heading
    orientation.gps_online = True
    orientation.alt = 3000
    orientation.groundspeed = 0
    orientation.airspeed = 0

    return orientation


def render_frames(scope_type, position, heading, steps, with_traffic=True,
                  display_units=units.STATUTE, airports_valid=True):
    """
    Renders a scope through a list of steps and returns the frames.

    Each step is (keys_to_press, seconds_to_advance_before_render).
    """
    font = init_pygame()
    frames = []

    with scene(display_units, airports_valid) as clock:
        if with_traffic:
            HudDataCache.RELIABLE_TRAFFIC = make_traffic(position)

        trail = make_breadcrumb_trail(position)

        with patch.object(breadcrumbs.INSTANCE, "get_trail", return_value=trail):
            scope = scope_type(20, FRAME_SIZE[1] / 40, font, FRAME_SIZE)
            orientation = make_orientation(position, heading)

            for keys, seconds in steps:
                scope.handle_events(
                    [pygame.event.Event(pygame.KEYUP, key=key) for key in keys]
                )
                clock.advance(seconds)

                framebuffer = pygame.Surface(FRAME_SIZE)
                framebuffer.fill((0, 0, 0))
                scope.render(framebuffer, orientation)
                frames.append(framebuffer)

    return frames
