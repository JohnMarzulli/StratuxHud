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
# Program to consume the AHRS and position data from a Stratux and dispplay
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

import logging
import logging.handlers
import configuration
from lib.logger import Logger
import heads_up_display


CONFIGURATION = configuration.Configuration(configuration.DEFAULT_CONFIG_FILE)

LOG_LEVEL = logging.INFO

LOGGER = logging.getLogger("stratux_hud")
LOGGER.setLevel(LOG_LEVEL)
HANDLER = logging.handlers.RotatingFileHandler(
    CONFIGURATION.log_filename, maxBytes=1048576, backupCount=3)
HANDLER.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)-8s %(message)s'))
LOGGER.addHandler(HANDLER)

if __name__ == '__main__':
    hud = heads_up_display.HeadsUpDisplay()
    hud.run()
