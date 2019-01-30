"""
Main entry code for Stratux HUD
"""
# !python
#
#
# Author: John Marzulli
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You can view the GNU General Public License at <http://www.gnu.org/licenses/>
#
# Written for Python 2.7
#
# Includes provisions for the basic logic to be run
# for development\testing under Windows or Mac
#
#
# Program to consume the AHRS and position data from a Stratux and display
# it as a HUD style display.
#
# This code does not have to run on the Stratux hardware, but it can.
# Assumes a 5" TFT display from SunFounder and a "HUD" reflector
# from Amazon.
#
# Heavily inspired by https://github.com/kdknigga/pyahrs
#
# Required packages
#
# pip install pygame
# pip install requests
# pip instal ws4py
#
# Powershell to extract CSV perf data from logs:
# ```
# (((((get-content stratux_hud.log) -replace "^.* - INFO - ", "") -replace "\<.*?\..*?\.", "") -replace " object.*\>", "") -replace "---.*-", "") | Where {$_ -ne ""}
# ```


import logging
import logging.handlers

import heads_up_display
from lib.logger import Logger

python_logger = logging.getLogger("stratux_hud")
python_logger.setLevel(logging.DEBUG)
LOGGER = Logger(python_logger)
HANDLER = logging.handlers.RotatingFileHandler(
    "stratux_hud.log", maxBytes=1048576, backupCount=10)
HANDLER.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
python_logger.addHandler(HANDLER)


if __name__ == '__main__':
    LOGGER.log_info_message("Starting HUD")
    LOGGER.log_info_message("System, DateTime, Component, Instantaneous, Rolling Mean, Max")

    hud = heads_up_display.HeadsUpDisplay(LOGGER)
    hud.run()
