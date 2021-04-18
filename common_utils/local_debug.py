"""
Module to help with mocking/bypassing
RaspberryPi specific code to enable for
debugging on a Mac or Windows host.
"""

import platform
from sys import platform as os_platform
from sys import version_info

REQUIRED_PYTHON_VERSION = 3.5
MAXIMUM_PYTHON_VERSION = 3.8

IS_LINUX = 'linux' in os_platform
DETECTED_CPU = platform.machine()
IS_PI = "arm" in DETECTED_CPU
IS_SLOW = IS_PI and "v7l" in DETECTED_CPU
IS_MAC = "darwin" in os_platform


def validate_python_version():
    """
    Checks to make sure that the correct version of Python is being used.

    Raises:
        Exception -- If the  version of Python is not new enough.
    """

    python_version = float('{}.{}'.format(
        version_info.major,
        version_info.minor))
    error_text = 'Requires Python {}'.format(REQUIRED_PYTHON_VERSION)

    if python_version < REQUIRED_PYTHON_VERSION:
        print(error_text)
        raise Exception(error_text)

    if python_version > MAXIMUM_PYTHON_VERSION:
        print('Python version {} is newer than the maximum allowed version of {}'.format(
            python_version, MAXIMUM_PYTHON_VERSION))

        raise Exception(
            "The HUD code is not yet compatible with Python 3.9 or newer.")


def is_debug() -> bool:
    """
    returns True if this should be run as a local debug (Mac or Windows).
    """

    return (os_platform in ["win32", "darwin"]) or (IS_LINUX and not IS_PI)


validate_python_version()
