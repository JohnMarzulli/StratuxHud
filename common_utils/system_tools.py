import subprocess

from common_utils import local_debug

DEFAULT_POWER_CYCLE_DELAY = 2  # Time to allow for responses to be sent


def restart():
    """
    Restarts down the Pi.
    """

    if not local_debug.IS_PI:
        return

    subprocess.Popen(
        ["sudo shutdown -r 30"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)


def shutdown(
    seconds: int = 30
):
    """
    Shuts down the Pi.
    """

    if not local_debug.IS_PI:
        return

    subprocess.Popen(
        ["sudo shutdown -h {0}".format(int(seconds))],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
