"""
Main entry code for Stratux HUD
"""
# !python
#
# StratuxHud
#
# Written for Python 3.5
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

import heads_up_display
from common_utils.logger import HudLogger

python_logger = logging.getLogger("stratux_hud")
python_logger.setLevel(logging.DEBUG)
LOGGER = HudLogger(python_logger)
HANDLER = logging.handlers.RotatingFileHandler(
    "stratux_hud.log", maxBytes=1048576, backupCount=10)
HANDLER.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
python_logger.addHandler(HANDLER)


if __name__ == '__main__':
    LOGGER.log_info_message("Starting HUD")
    LOGGER.log_info_message(
        "System, DateTime, Component, Instantaneous, Rolling Mean, Max")

    hud = heads_up_display.HeadsUpDisplay(LOGGER)
    hud.run()
