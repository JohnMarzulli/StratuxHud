import datetime
import json
import math
import random
import threading
import time

import requests

from configuration import configuration

ERROR_JSON_KEY = 'error'

OFFLINE = "Offline"

CO_LEVEL_KEY = "co"
BATTERY_LEVEL_KEY = "battery"

SPO2_LEVEL_KEY = "spo2"
PULSE_KEY = "heartrate"
SIGNAL_STRENGTH_KEY = "signal"

MAX_SECONDS_BETWEEN_CO_REPORT = 120
MAX_SECONDS_BETWEEN_SPO2_REPORT = 30


class Spo2Report(object):
    """
    Object to hold a safe version of the Illyrian SPO2 report
    that came from the connecting service
    """

    def __init__(
        self,
        report,
        has_been_connected
    ):
        self.spo2 = OFFLINE
        self.heartrate = OFFLINE
        self.signal = OFFLINE
        self.has_been_connected = has_been_connected
        self.is_connected = False

        if report is not None:
            if SPO2_LEVEL_KEY in report:
                self.spo2 = report[SPO2_LEVEL_KEY]
                self.is_connected = self.spo2 is not None

            if PULSE_KEY in report:
                self.heartrate = report[PULSE_KEY]

            if SIGNAL_STRENGTH_KEY in report:
                self.signal = report[SIGNAL_STRENGTH_KEY]


class CoReport(object):
    """
    Object to hold a safe version of the carbon monoxide report
    that came from the connecting service
    """

    def __init__(
        self,
        report,
        has_been_connected
    ):
        self.co = OFFLINE
        self.battery = OFFLINE
        self.has_been_connected = has_been_connected
        self.is_connected = False

        if report is not None:
            if CO_LEVEL_KEY in report:
                self.co = report[CO_LEVEL_KEY]
                self.is_connected = self.co is not None

            if BATTERY_LEVEL_KEY in report:
                self.battery = report[BATTERY_LEVEL_KEY]


class AithreClient(object):
    """
    Class to handle the REST calls to the Aithre service
    """

    INSTANCE = None

    def __init__(self, rest_address):
        self.__aithre_session__ = requests.Session()
        self.rest_address = rest_address

        self.__last_co_report_time__ = None
        self.__last_spo2_report_time__ = None
        self.__co_report__ = None
        self.__spo2_report__ = None
        self.__co_has_been_connected__ = False
        self.__spo2_has_been_connected__ = False

        AithreClient.INSTANCE = self

    def get_spo2_report(self):
        if self.__last_spo2_report_time__ is not None and self.__spo2_report__ is not None:
            delta_time = datetime.datetime.utcnow() - self.__last_spo2_report_time__
            available = delta_time.total_seconds() < MAX_SECONDS_BETWEEN_SPO2_REPORT

            if available:
                self.__spo2_has_been_connected__ |= (
                    SPO2_LEVEL_KEY in self.__spo2_report__ and self.__spo2_report__[SPO2_LEVEL_KEY] is not None)

                return Spo2Report(self.__spo2_report__, self.__spo2_has_been_connected__)

        return Spo2Report(None, self.__spo2_has_been_connected__)

    def get_co_report(self):
        if self.__last_co_report_time__ is not None and self.__co_report__ is not None:
            delta_time = datetime.datetime.utcnow() - self.__last_co_report_time__
            available = delta_time.total_seconds() < MAX_SECONDS_BETWEEN_CO_REPORT

            if available:
                self.__co_has_been_connected__ |= (
                    CO_LEVEL_KEY in self.__co_report__ and self.__co_report__[CO_LEVEL_KEY] is not None)
                return CoReport(self.__co_report__, self.__co_has_been_connected__)

        return CoReport(None, self.__co_has_been_connected__)

    def __handle_co_report__(self, json_package):
        try:
            if json_package is not None:
                decoded = json.loads(json_package)
                if decoded is not None and ERROR_JSON_KEY not in decoded:
                    self.__co_report__ = decoded
                    self.__last_co_report_time__ = datetime.datetime.utcnow()
        except Exception as ex:
            print(ex)

    def __handle_spo2_report__(self, json_package):
        try:
            if json_package is not None:
                decoded = json.loads(json_package)
                if decoded is not None and ERROR_JSON_KEY not in decoded:
                    self.__spo2_report__ = decoded
                    self.__last_spo2_report_time__ = datetime.datetime.utcnow()
        except Exception as ex:
            print(ex)

    def update_aithre(self):
        """
        Calls the aithre manager and gets the current data from all devices.
        """
        try:
            co_url = "http://{}/aithre".format(self.rest_address)
            spo2_url = "http://{}/illyrian".format(self.rest_address)

            self.__handle_co_report__(self.__aithre_session__.get(co_url,
                                                                  timeout=configuration.AHRS_TIMEOUT).json())

            self.__handle_spo2_report__(self.__aithre_session__.get(spo2_url,
                                                                    timeout=configuration.AHRS_TIMEOUT).json())
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception as ex:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            print('TRAFFIC.update() ex={}'.format(ex))


AithreClient(configuration.CONFIGURATION.aithre_manager_address)

if __name__ == '__main__':
    while True:
        AithreClient.INSTANCE.update_aithre()
        time.sleep(5)
