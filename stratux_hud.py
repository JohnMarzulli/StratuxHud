"""
Main entry code for Stratux HUD
"""
# !python
#
# StratuxHud
#
# Written for Python 3.8
# This code may be run on the Stratux hardware,
# or on a stand-alone Raspberry Pi.
#
# Heavily inspired by https://github.com/kdknigga/pyahrs
#
# Powershell to extract CSV perf data from logs:
# ```
# (((((get-content stratux_hud.log) -replace "^.* - INFO - ", "") -replace "\<.*?\..*?\.", "") -replace " object.*\>", "") -replace "---.*-", "") | Where {$_ -ne ""}
# ```
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Covered by the GPL V3
# You can view the GNU General Public License at <http://www.gnu.org/licenses/>
# The license is also available in LICENSE in this directory


import logging
import logging.handlers
import sys

from rendering import display

import heads_up_display
from common_utils.logger import HudLogger

__PYTHON_LOGGGER__ = logging.getLogger("stratux_hud")
__PYTHON_LOGGGER__.setLevel(logging.DEBUG)
__LOGGER__ = HudLogger(__PYTHON_LOGGGER__)
__HANDLER__ = logging.handlers.RotatingFileHandler(
    "stratux_hud.log",
    maxBytes=1048576,
    backupCount=10)
__HANDLER__.setFormatter(
    logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
__PYTHON_LOGGGER__.addHandler(__HANDLER__)


__USE_FULLSCREEN_FLAG__ = "fullscreen"


def __is_flag_present__(
    flag_name: str
) -> bool:
    """
    Should we use fullscreen no matter what type of
    runtime environment we are in.

    Returns:
        bool: Should the HUD use fullscreen?
    """
    is_flag_present = False

    for argument in sys.argv:
        is_flag_present |= flag_name.lower() in argument.lower()

    return is_flag_present


if __name__ == '__main__':
    __LOGGER__.log_info_message("Starting HUD")
    __LOGGER__.log_info_message("System, DateTime, Component, Instantaneous, Rolling Mean, Max")

    hud = heads_up_display.HeadsUpDisplay(
        __LOGGER__,
        __is_flag_present__(__USE_FULLSCREEN_FLAG__),
        __is_flag_present__(display.FORCE_SOFTWARE_FLAG))
    hud.run()
