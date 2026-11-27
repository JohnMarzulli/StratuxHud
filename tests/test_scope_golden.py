"""
Golden-frame tests for the top-down scopes.

Each scene renders a scope headless with a fixed clock and fixed data,
then compares it to a saved PNG in tests/golden_frames/.

To (re)generate the saved frames after an intentional visual change:

    UPDATE_GOLDEN=1 python -m pytest tests/test_scope_golden.py

Then look at the new PNGs before committing them.
"""

import os
import unittest

import pygame

from tests import scope_scenes
from common_utils import units

with scope_scenes.patch("requests.Session.get", return_value=scope_scenes.Mock(json=lambda: {})):
    from views.adsb_and_weather_scope import AdsbAndWeatherScope
    from views.adsb_top_view_scope import AdsbTopViewScope
    from views.weather_scope import WeatherTopViewScope

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_frames")
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"

# Rendering is deterministic on one machine, but font rasterizing can
# vary slightly between pygame/SDL builds. Allow a tiny number of
# pixels to differ before calling it a change.
MAX_DIFFERENT_PIXEL_FRACTION = 0.0005
CHANNEL_TOLERANCE = 8

UP = pygame.K_UP
DOWN = pygame.K_DOWN

# name -> (scope type, position, heading, steps, options)
SCENES = {
    "adsb_default": (
        AdsbTopViewScope, scope_scenes.SEATTLE, 30, [([], 0)], {},
    ),
    "adsb_heading_350": (
        AdsbTopViewScope, scope_scenes.SEATTLE, 350, [([], 0)], {},
    ),
    "adsb_zoomed_out": (
        AdsbTopViewScope, scope_scenes.SEATTLE, 30, [([UP, UP], 5.0)], {},
    ),
    "adsb_mid_zoom_pulse": (
        AdsbTopViewScope, scope_scenes.SEATTLE, 30, [([UP], 1.2)], {},
    ),
    "adsb_airports_expired": (
        # 4 seconds: past the 3 second zoom, and an even second so the
        # blinking "EXPIRED" warning is showing.
        AdsbTopViewScope, scope_scenes.SEATTLE, 30, [([UP], 4.0)],
        {"airports_valid": False},
    ),
    "weather_default": (
        WeatherTopViewScope, scope_scenes.PORTLAND, 0, [([], 0)],
        {"with_traffic": False},
    ),
    "weather_zoomed_in": (
        WeatherTopViewScope, scope_scenes.PORTLAND, 45, [([DOWN], 5.0)],
        {"with_traffic": False},
    ),
    "weather_far_with_airports": (
        WeatherTopViewScope, scope_scenes.SEATTLE, 180, [([UP, UP], 5.0)],
        {"with_traffic": False},
    ),
    "combined_default": (
        AdsbAndWeatherScope, scope_scenes.PORTLAND, 30, [([], 0)], {},
    ),
    "combined_zoomed_out": (
        AdsbAndWeatherScope, scope_scenes.PORTLAND, 30, [([UP, UP, UP], 5.0)], {},
    ),
    "combined_mid_zoom_pulse": (
        AdsbAndWeatherScope, scope_scenes.PORTLAND, 30, [([UP, UP, UP], 3.6), ([UP], 1.2)], {},
    ),
    # Distances in other units: airports, breadcrumbs, and weather
    # must line up with traffic and the ring labels.
    "adsb_knots": (
        AdsbTopViewScope, scope_scenes.SEATTLE, 30, [([UP], 4.0)],
        {"display_units": units.NAUTICAL},
    ),
    "weather_metric": (
        WeatherTopViewScope, scope_scenes.PORTLAND, 0, [([], 0)],
        {"with_traffic": False, "display_units": units.METRIC},
    ),
    "combined_knots": (
        AdsbAndWeatherScope, scope_scenes.PORTLAND, 30, [([UP, UP, UP], 5.0)],
        {"display_units": units.NAUTICAL},
    ),
}


def render_scene(name):
    scope_type, position, heading, steps, options = SCENES[name]

    return scope_scenes.render_frames(
        scope_type, position, heading, steps, **options
    )[-1]


def count_different_pixels(actual: pygame.Surface, expected: pygame.Surface) -> int:
    width, height = actual.get_size()
    different = 0

    for y in range(height):
        for x in range(width):
            a = actual.get_at((x, y))
            e = expected.get_at((x, y))

            if (
                abs(a.r - e.r) > CHANNEL_TOLERANCE
                or abs(a.g - e.g) > CHANNEL_TOLERANCE
                or abs(a.b - e.b) > CHANNEL_TOLERANCE
            ):
                different += 1

    return different


class ScopeGoldenFrameTests(unittest.TestCase):
    def check(self, name):
        actual = render_scene(name)
        path = os.path.join(GOLDEN_DIR, f"{name}.png")
        failed_path = os.path.join(GOLDEN_DIR, f"{name}.actual.png")

        # Output from an earlier failure is stale once we render again;
        # it is written back below if this run fails too.
        if os.path.exists(failed_path):
            os.remove(failed_path)

        if UPDATE or not os.path.exists(path):
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            pygame.image.save(actual, path)

            if not UPDATE:
                self.skipTest(f"Created missing golden frame {path}")

            return

        expected = pygame.image.load(path)
        self.assertEqual(actual.get_size(), expected.get_size())

        # Fast path: identical bytes.
        if pygame.image.tobytes(actual, "RGB") == pygame.image.tobytes(expected, "RGB"):
            return

        different = count_different_pixels(actual, expected)
        allowed = int(actual.get_width() * actual.get_height() * MAX_DIFFERENT_PIXEL_FRACTION)

        if different > allowed:
            pygame.image.save(actual, failed_path)
            self.fail(
                f"{name}: {different} pixels differ (allowed {allowed}). "
                f"Actual frame saved to {failed_path}"
            )


def _add_scene_test(name):
    setattr(
        ScopeGoldenFrameTests,
        f"test_{name}",
        lambda self: self.check(name),
    )


for _scene_name in SCENES:
    _add_scene_test(_scene_name)


if __name__ == "__main__":
    unittest.main()
