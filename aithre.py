import sys
import time
import datetime
from configuration import CONFIGURATION
import lib.local_debug as local_debug

if local_debug.IS_LINUX:
    from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate
else:
    from lib.simulated_values import SimulatedValue
    aithre_co_simulator = SimulatedValue(1, 50, 1, -25, 25)
    aithre_bat_simulator = SimulatedValue(1, 50, -1, 35, 50)

# The Aithre is always expected to have a public address
AITHRE_ADDR_TYPE = "public"

# Service UUID for the carbon monoxide reading.
# Will be a single character whose ASCII
# value is the parts per milloion 0 - 255 inclusive
CO_OFFSET = "BCD466FE07034D85A021AE8B771E4922"

# A single character wholes ASCII value is
# the percentage of the battert reminaing.
# The value will be 0 to 100 inclusive.
BAT_OFFSET = "24509DDEFCD711E88EB2F2801F1B9FD1"

CO_SAFE = 10
CO_WARNING = 49

BATTERY_SAFE = 75
BATTERY_WARNING = 25


def get_service_value(addr, addr_type, offset):
    """
    Gets the value from a Blue Tooth Low Energy device.
    Arguments:
        addr {string} -- The address to get the value from
        add_type {string} -- The type of address we are using.
        offset {string} -- The offset from the device's address to get the value from
    Returns: {int} -- The result of the fetch
    """
    if not CONFIGURATION.aithre_enabled:
        return None

    # Generate fake values for debugging
    # and for the development of the visuals.
    if not local_debug.IS_LINUX:
        if offset in CO_OFFSET:
            return int(aithre_co_simulator.get_value())
        else:
            return int(aithre_bat_simulator.get_value())

    try:
        p = Peripheral(addr, addr_type)  # bluepy.btle.ADDR_TYPE_PUBLIC)
        ch_all = p.getCharacteristics(uuid=offset)

        if ch_all[0].supportsRead():
            res = ch_all[0].read()

        p.disconnect()

        return ord(res)
    except Exception as ex:
        print("   ex in get_name={}".format(ex))

    return None


def get_aithre(mac_adr):
    """
    Gets the current Aithre readings given a MAC for the Aithre
    Arguments:
        mac_adr {string} -- The MAC address of the Aithre to fetch from.
    Returns: {(int, int)} -- The co and battery percentage of the Aithre
    """
    if not CONFIGURATION.aithre_enabled:
        return None, None

    co = get_service_value(mac_adr, AITHRE_ADDR_TYPE, CO_OFFSET)
    bat = get_service_value(mac_adr, AITHRE_ADDR_TYPE, BAT_OFFSET)

    return co, bat


def get_aithre_mac():
    """
    Attempts to find an Aithre MAC using Blue Tooth low energy.
    Returns: {string} None if a device was not found, otherwise the MAC of the Aithre
    """
    if not CONFIGURATION.aithre_enabled:
        return None

    try:
        if not local_debug.IS_LINUX:
            return None

        scanner = Scanner()
        devices = scanner.scan(2)
        for dev in devices:
            print("    {} {} {}".format(dev.addr, dev.addrType, dev.rssi))

            for (adtype, desc, value) in dev.getScanData():
                try:
                    if "AITH" in value:
                        return dev.addr
                except Exception as ex:
                    print("DevScan loop - ex={}".format(ex))

    except Exception as ex:
        print("Outter loop ex={}".format(ex))

    return None


CO_SCAN_PERIOD = 15

if local_debug.IS_LINUX:
    CO_SCAN_PERIOD = 1.0

OFFLINE = "OFFLINE"


class Aithre(object):
    def log(self, text):
        """
        Logs the given text if a logger is available.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_info_message(text)
        else:
            print("INFO:{}".format(text))

    def warn(self, text):
        """
        Logs the given text if a logger is available AS A WARNING.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_warning_message(text)
        else:
            print("WARN:{}".format(text))

    def __init__(self, logger = None):
        self.__logger__ = logger

        self.warn("Initializing new Aithre object")

        self._mac_ = None
        self._levels_ = None

        self._update_mac_()

    def is_connected(self):
        return (self._mac_ is not None and self._levels_ is not None) or not local_debug.IS_LINUX

    def update(self):
        self._update_levels()

    def _update_mac_(self):
        if not CONFIGURATION.aithre_enabled:
            return

        try:
            self._mac_ = get_aithre_mac()
        except Exception as e:
            self._mac_ = None
            self.warn("Got EX={} during MAC update.".format(e))

    def _update_levels(self):
        if not CONFIGURATION.aithre_enabled:
            return

        if self._mac_ is None:
            self.log("Aithre MAC is none while attempting to update levels.")
            if not local_debug.IS_LINUX:
                self.log("... and this is not a Linux machine, so attempting to simulate.")
                aithre_co_simulator.simulate()
                aithre_bat_simulator.simulate()
            else:
                self.warn("Aithre MAC is none, attempting to connect.")
                self._update_mac_()

        try:
            self.log("Attempting update")
            self._levels_ = get_aithre(self._mac_)
        except Exception as ex:
            # In case the read fails, we will want to
            # attempt to find the MAC of the Aithre again.

            self._mac_ = None
            self.warn("Exception while attempting to update the cached levels.update() E={}".format(ex))

    def get_battery(self):
        if not CONFIGURATION.aithre_enabled:
            return None

        if self._levels_ is not None:
            return self._levels_[1]

        return OFFLINE

    def get_co_level(self):
        if not CONFIGURATION.aithre_enabled:
            return None

        if self._levels_ is not None:
            return self._levels_[0]

        return OFFLINE


# Global singleton for all to
# get to the Aithre
try:
    sensor = Aithre()
except:
    sensor = None

if __name__ == '__main__':
    while True:
        sensor.update()
        print("CO:{} BAT{}".format(sensor.get_co_level(), sensor.get_battery()))
        time.sleep(CO_SCAN_PERIOD)
