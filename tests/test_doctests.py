"""
Runs the doctests written in module docstrings as part of the test
suite. Each module can still be checked on its own:

    python -m common_utils.geo_math -v
"""

import doctest
import importlib
import unittest
from unittest.mock import Mock, patch

MODULES_WITH_DOCTESTS = [
    "common_utils.fast_math",
    "common_utils.geo_math",
    "common_utils.text_tools",
    "common_utils.units",
    "core_services.weather_report_classification",
    "rendering.colors",
]


class DoctestTests(unittest.TestCase):
    def test_module_doctests(self):
        for module_name in MODULES_WITH_DOCTESTS:
            with self.subTest(module_name):
                with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
                    module = importlib.import_module(module_name)

                results = doctest.testmod(module)

                self.assertGreater(results.attempted, 0, f"{module_name} has no doctests")
                self.assertEqual(results.failed, 0, f"{module_name} doctests failed")


if __name__ == "__main__":
    unittest.main()
