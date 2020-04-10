import sys
import time
import datetime
from sys import platform as os_platform
from aithre_task import AithreTask

IS_LINUX = 'linux' in os_platform

if IS_LINUX:
    from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate
else:
    from lib.simulated_values import SimulatedValue
    aithre_co_simulator = SimulatedValue(1, 50, 1, -25, 25)
    aithre_bat_simulator = SimulatedValue(1, 50, -1, 35, 50)

# The Aithre is always expected to have a public address
AITHRE_ADDR_TYPE = "public"

# Service UUID for the carbon monoxide reading.
# Will be a single character whose ASCII
# value is the parts per million 0 - 255 inclusive
CO_OFFSET = "BCD466FE07034D85A021AE8B771E4922"

# A single character wholes ASCII value is
# the percentage of the battert reminaing.
# The value will be 0 to 100 inclusive.
BAT_OFFSET = "24509DDEFCD711E88EB2F2801F1B9FD1"

AITHRE_DEVICE_NAME = "AITHRE"
ILLYRIAN_BEACON_SUFFIX = "696C6C70"


def get_service_value(
    addr,
    addr_type,
    offset
):
    """
    Gets the value from a Blue Tooth Low Energy device.
    Arguments:
        addr {string} -- The address to get the value from
        add_type {string} -- The type of address we are using.
        offset {string} -- The offset from the device's address to get the value from
    Returns: {int} -- The result of the fetch
    """

    # Generate fake values for debugging
    # and for the development of the visuals.
    if not IS_LINUX:
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


def get_aithre(
    mac_adr
):
    """
    Gets the current Aithre readings given a MAC for the Aithre
    Arguments:
        mac_adr {string} -- The MAC address of the Aithre to fetch from.
    Returns: {(int, int)} -- The co and battery percentage of the Aithre
    """

    co = get_service_value(mac_adr, AITHRE_ADDR_TYPE, CO_OFFSET)
    bat = get_service_value(mac_adr, AITHRE_ADDR_TYPE, BAT_OFFSET)

    return co, bat


def get_illyrian(
    mac_adr
):
    """
    Attempts to get the blood/pulse/oxygen levels from an Illyrian device
        :param mac_adr: 
    """

    # Example value:
    # '41193dff0008696c6c70'
    # '414039ff0008696c6c70'
    # '410000010008696c6c70'
    #  41[R VALUE * 100][HEART RATE] [SIGNAL STRENGTH][SERIAL NO]696C6C70
    #  [00][0001][0008]
    #  [40][39][ff]
    illyrian = get_value_by_name(ILLYRIAN_BEACON_SUFFIX)

    if illyrian is None:
        return (OFFLINE, OFFLINE, OFFLINE)

    r_value = int(illyrian[2:4], 16) / 100.0
    heartrate = int(illyrian[4:6], 16)
    signal_strength = int(illyrian[6:8], 16)
    sp02 = 109 - (31 * r_value)

    return (sp02, heartrate, signal_strength)


def get_value_by_name(
    name_to_find
):
    try:
        if not IS_LINUX:
            return None

        scanner = Scanner()
        devices = scanner.scan(2)
        for dev in devices:
            print("    {} {} {}".format(dev.addr, dev.addrType, dev.rssi))

            for (adtype, desc, value) in dev.getScanData():
                try:
                    if name_to_find.lower() in value.lower():
                        return value
                except Exception as ex:
                    print("DevScan loop - ex={}".format(ex))

    except Exception as ex:
        print("Outter loop ex={}".format(ex))

    return None


def get_mac_by_device_name(
    name_to_find
):
    """
    Attempts to find an Aithre MAC using Blue Tooth low energy.
    Arguments:
        name_to_find {string} -- The name (or partial name) to match the BLE info with.
    Returns: {string} None if a device was not found, otherwise the MAC of the Aithre
    """
    try:
        if not IS_LINUX:
            return None

        scanner = Scanner()
        devices = scanner.scan(2)
        for dev in devices:
            print("    {} {} {}".format(dev.addr, dev.addrType, dev.rssi))

            for (adtype, desc, value) in dev.getScanData():
                try:
                    if name_to_find.lower() in value.lower():
                        return dev.addr
                except Exception as ex:
                    print("DevScan loop - ex={}".format(ex))

    except Exception as ex:
        print("Outter loop ex={}".format(ex))

    return None


def get_aithre_mac():
    """
    Attempts to find the BlueTooth MAC for the
    Aithre Carbon Monoxide detector.
    """
    return get_mac_by_device_name(AITHRE_DEVICE_NAME)


def get_illyrian_mac():
    """
    Attempts to find the BlueTooth MAC for the
    Aithre Illyrian blood oxygen detector.
    """
    return get_mac_by_device_name(ILLYRIAN_BEACON_SUFFIX)


CO_SCAN_PERIOD = 15

if IS_LINUX:
    CO_SCAN_PERIOD = 1.0

OFFLINE = "OFFLINE"


class BlueToothDevice(object):
    """
    Base interface class to help define common controls
    and features of the Aithre range of products.
    """

    def log(
        self,
        text
    ):
        """
        Logs the given text if a logger is available.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_info_message(text)
        else:
            print("INFO:{}".format(text))

    def warn(
        self,
        text
    ):
        """
        Logs the given text if a logger is available AS A WARNING.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_warning_message(text)
        else:
            print("WARN:{}".format(text))

    def __init__(
        self,
        logger=None
    ):
        self.__logger__ = logger

        self.warn("Initializing new Aithre object")

        self._mac_ = None
        self._levels_ = None

        self._update_mac_()

    def is_connected(
        self
    ):
        """
        Is the BlueTooth device currently connected and usable?
        """

        return (self._mac_ is not None and self._levels_ is not None) or not IS_LINUX

    def update(
        self
    ):
        """
        Attempts to update the values collected from the device.
        """
        self._update_levels()


class Illyrian(BlueToothDevice):
    def __init__(
        self,
        logger=None
    ):
        super(Illyrian, self).__init__(logger=logger)

    def _update_mac_(
        self
    ):
        """
        Updates the BlueTooth MAC that the Blood Oxygen sensor is on.
        """
        try:
            self._mac_ = get_illyrian_mac()
        except Exception as e:
            self._mac_ = None
            self.warn("Got EX={} during MAC update.".format(e))

    def _update_levels(
        self
    ):
        """
        Updates the levels of an Illyrian
            :param self: 
        An example value is '410000010008696c6c70' when searching for the MAC.
        This is so the beacon can be used simultaneously by devices.
        """
        try:
            new_levels = get_illyrian(self._mac_)
            self._levels_ = new_levels
        except:
            self.warn("Unable to get Illyrian levels")

    def get_spo2_level(
        self
    ):
        """
        Returns the oxygen saturation levels.
            :param self: 
        """

        if self._levels_ is not None:
            return self._levels_[0]

        return OFFLINE

    def get_heartrate(
        self
    ):
        """
        Returns the wearer's pulse.
            :param self: 
        """

        if self._levels_ is not None:
            return self._levels_[1]

        return OFFLINE

    def get_signal_strength(
        self
    ):
        """
        Returns the read strength from the sensor.
            :param self: 
        """

        if self._levels_ is not None:
            return self._levels_[2]

        return OFFLINE


class Aithre(BlueToothDevice):
    def __init__(
        self,
        logger=None
    ):
        super(Aithre, self).__init__(logger=logger)

    def _update_mac_(
        self
    ):
        """
        Updates the MAC that the Aithre carbon monoxide detector is found at.
        """
        try:
            self._mac_ = get_aithre_mac()
        except Exception as e:
            self._mac_ = None
            self.warn("Got EX={} during MAC update.".format(e))

    def _update_levels(
        self
    ):
        """
        Updates the battery level and carbon monoxide levels that the Aithre CO
        detector has found.
        """
        if self._mac_ is None:
            self.log("Aithre MAC is none while attempting to update levels.")
            if not IS_LINUX:
                self.log(
                    "... and this is not a Linux machine, so attempting to simulate.")
                aithre_co_simulator.simulate()
                aithre_bat_simulator.simulate()
            else:
                self.warn("Aithre MAC is none, attempting to connect.")
                self._update_mac_()

        try:
            self.log("Attempting update")
            new_levels = get_aithre(self._mac_)
            self._levels_ = new_levels
        except Exception as ex:
            # In case the read fails, we will want to
            # attempt to find the MAC of the Aithre again.

            self._mac_ = None
            self.warn(
                "Exception while attempting to update the cached levels.update() E={}".format(ex))

    def get_battery(
        self
    ):
        """
        Gets the battery level of the CO monitor device.
        """
        if self._levels_ is not None:
            return self._levels_[1]

        return OFFLINE

    def get_co_level(
        self
    ):
        """
        Gets the current carbon monoxide levels.
        """
        if self._levels_ is not None:
            return self._levels_[0]

        return OFFLINE


def update_aithre_sensor():
    """
    Attempts to update the Aithre carbon monoxide
    sensor. If the sensor can not be found or is
    not turned on, then the controlling object is
    set to None.
    """
    try:
        if AithreManager.CO_SENSOR is None:
            AithreManager.CO_SENSOR = Aithre()
    except Exception as e:
        print("Attempted to init CO sensor, got e={}".format(e))
        AithreManager.CO_SENSOR = None

    if AithreManager.CO_SENSOR is not None:
        AithreManager.CO_SENSOR.update()


def update_illyrian_sensor():
    """
    Attempts to update the Aithre Illyrian blood oxygen
    sensor. If the sensor can not be found or is
    not turned on, then the controlling object is
    set to None.
    """
    try:
        if AithreManager.SPO2_SENSOR is None:
            AithreManager.SPO2_SENSOR = Illyrian()
    except Exception as e:
        print("Attempted to init SPO2 sensor, got e={}".format(e))
        AithreManager.SPO2_SENSOR = None

    if AithreManager.SPO2_SENSOR is not None:
        AithreManager.SPO2_SENSOR.update()


class AithreManager(object):
    """
    Singleton manager class to make sure that the sensor data
    has a common store point.
    """
    CO_SENSOR = None
    SPO2_SENSOR = None

    @staticmethod
    def update_sensors():
        """
        Updates the sensors for all available BlueTooth devices.
        """
        print("Updating Aithre sensors")

        # Global singleton for all to
        # get to the Aithre
        update_aithre_sensor()
        update_illyrian_sensor()


update_task = AithreTask(
    "UpdateAithre",
    CO_SCAN_PERIOD,
    AithreManager.update_sensors,
    None,
    True)

if __name__ == '__main__':
    while True:
        try:
            if AithreManager.CO_SENSOR is not None:
                print("CO:{}PPM BAT:{}%".format(
                    AithreManager.CO_SENSOR.get_co_level(),
                    AithreManager.CO_SENSOR.get_battery()))

            if AithreManager.SPO2_SENSOR is not None:
                print("SPO2:{}%, {}BPM, SIGNAL:{}".format(
                    AithreManager.SPO2_SENSOR.get_spo2_level(),
                    AithreManager.SPO2_SENSOR.get_heartrate(),
                    AithreManager.SPO2_SENSOR.get_signal_strength()))
        except:
            print("Exception in debug loop")

        time.sleep(CO_SCAN_PERIOD)
