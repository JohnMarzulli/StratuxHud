import sys
import time
import datetime
import lib.local_debug as local_debug

if not local_debug.is_debug():
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
    # Generate fake values for debugging
    # and for the development of the visuals.
    if local_debug.is_debug():
        if offset in CO_OFFSET:
            return int(aithre_co_simulator.get_value())
        else:
            return int(aithre_bat_simulator.get_value())

    # print("get_name({})".format(addr))
    try:
        # print("   Peripheral()")
        p = Peripheral(addr, addr_type)  # bluepy.btle.ADDR_TYPE_PUBLIC)
        # print("   p.getChar()")
        ch_all = p.getCharacteristics(uuid=offset)
        # print(ch_all)

        if ch_all[0].supportsRead():
            # print("ch[0].read()=")
            res = ch_all[0].read()
            # print("Raw={}".format(res))
            # print("Ord={}".format(ord(res)))
            # print("done with read")

        p.disconnect()

        return ord(res)
    except Exception as ex:
        print("   ex in get_name={}".format(ex))
        pass

    return None


def get_aithre(mac_adr):
    co = get_service_value(mac_adr, AITHRE_ADDR_TYPE, CO_OFFSET)
    bat = get_service_value(mac_adr, AITHRE_ADDR_TYPE, BAT_OFFSET)

    return co, bat


def get_aithre_mac():
    print("get_aithre_mac()")
    try:
        if local_debug.is_debug():
            return None

        scanner = Scanner()
        devices = scanner.scan(2)
        for dev in devices:
            print("    {} {} {}".format(dev.addr, dev.addrType, dev.rssi))

            for (adtype, desc, value) in dev.getScanData():
                try:
                    # print("     - {} {}={}".format(adtype, desc, value))

                    if "AITH" in value:
                        print("FOUND at {}!".format(dev.addr))
                        return dev.addr
                except Exception as ex:
                    print("DevScan loop - ex={}".format(ex))

    except Exception as ex:
        print("Outter loop ex={}".format(ex))

    return None


CO_SCAN_PERIOD = 15

if local_debug.is_debug():
    CO_SCAN_PERIOD = 1.0

OFFLINE = "OFFLINE"


class Aithre(object):
    def __init__(self):
        self._mac_ = None
        self._levels = None

        self._update_mac_()

    def is_connected(self):
        return (self._mac_ is not None and self._levels_ is not None) or local_debug.is_debug()

    def update(self):
        self._update_levels()

    def _update_mac_(self):
        try:
            self._mac_ = get_aithre_mac()
        except:
            self._mac_ = None

    def _update_levels(self):
        if self._mac_ is None:
            print("mac is none")

            if local_debug.is_debug():
                aithre_co_simulator.simulate()
                aithre_bat_simulator.simulate()
            else:
                return

        try:
            print("Attempting update")
            self._levels_ = get_aithre(self._mac_)
        except Exception as ex:
            # In case the read fails, we will want to
            # attempt to find the MAC of the Aithre again.

            self._mac_ = None
            print("update() ex={}".format(ex))

    def get_battery(self):
        if self._levels_ is not None:
            return self._levels_[1]

        return OFFLINE

    def get_co_level(self):
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
