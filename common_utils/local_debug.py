"""
Module to help with mocking/bypassing
RaspberryPi specific code to enable for
debugging on a Mac or Windows host.
"""

import platform
from sys import platform as os_platform
from sys import version_info

REQUIRED_PYTHON_VERSION = 3.5

IS_LINUX = 'linux' in os_platform
DETECTED_CPU = platform.machine()


def __is_raspberry_pi__() -> bool:
    # 64-bit Raspberry Pi OS (Bookworm, Trixie) reports "aarch64",
    # so check the board model before falling back to the CPU name.
    # 32-bit releases such as Buster report "armv7l" and match either way.
    try:
        with open("/proc/device-tree/model", "r") as model:
            if "raspberry pi" in model.read().lower():
                return True
    except (OSError, ValueError):
        pass

    return "arm" in DETECTED_CPU


IS_PI = __is_raspberry_pi__()
IS_SLOW = IS_PI and "v7l" in DETECTED_CPU
IS_MAC = "darwin" in os_platform


def validate_python_version():
    """
    Checks to make sure that the correct version of Python is being used.

    Raises:
        Exception -- If the  version of Python is not new enough.
    """

    print('Python = {}.{}'.format(
        version_info.major,
        version_info.minor))


def is_debug() -> bool:
    """
    returns True if this should be run as a local debug (Mac or Windows).
    """

    return (os_platform in ["win32", "darwin"]) or (IS_LINUX and not IS_PI)


validate_python_version()
