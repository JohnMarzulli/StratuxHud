import time

import requests
from common_utils import data_cache
from configuration import configuration

ERROR_JSON_KEY = 'error'

OFFLINE = "Offline"

CO_LEVEL_KEY = "co"
BATTERY_LEVEL_KEY = "battery"

SPO2_LEVEL_KEY = "spo2"
PULSE_KEY = "heartrate"
SIGNAL_STRENGTH_KEY = "signal"

MAX_SECONDS_BETWEEN_CO_REPORT = 120
MAX_SECONDS_BETWEEN_SPO2_REPORT = 60

SERVICE_CALL_TIMEOUT = 1.0


class Spo2Report(object):
    """
    Object to hold a safe version of the Illyrian SPO2 report
    that came from the connecting service
    """

    def __init__(
        self,
        report: dict,
        has_been_connected: bool
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
        report: dict,
        has_been_connected: bool
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

    def __init__(
        self,
        rest_address
    ):
        self.__aithre_session__ = requests.Session()
        self.rest_address = rest_address

        self.__aithre_source__ = data_cache.RestfulDataCache(
            "Aithre",
            self.__aithre_session__,
            "http://{}/aithre".format(self.rest_address),
            MAX_SECONDS_BETWEEN_CO_REPORT,
            SERVICE_CALL_TIMEOUT)

        self.__illyrian_source__ = data_cache.RestfulDataCache(
            "Illyrian",
            self.__aithre_session__,
            "http://{}/illyrians".format(self.rest_address),
            MAX_SECONDS_BETWEEN_SPO2_REPORT,
            SERVICE_CALL_TIMEOUT)

        self.__co_has_been_connected__ = False
        self.__spo2_has_been_connected__ = False

        AithreClient.INSTANCE = self

    def __get_spo_reports__(
        self
    ) -> list:
        report = self.__illyrian_source__.get()
        reports = report["reports"] if report is not None and "reports" in report else None

        self.__spo2_has_been_connected__ = self.__spo2_has_been_connected__ \
            or (reports is not None and len(reports) > 0)

        return reports

    def get_spo2_report(
        self
    ):
        reports = self.__get_spo_reports__()
        report = reports[0] if reports is not None else None
        self.__spo2_has_been_connected__ = self.__spo2_has_been_connected__ \
            or (report is not None and SPO2_LEVEL_KEY in report and report[SPO2_LEVEL_KEY] is not None)

        return Spo2Report(
            report,
            self.__spo2_has_been_connected__)

    def get_spo2_reports(
        self
    ) -> list:
        # $TODO - Make this support multiple units
        reports = self.__get_spo_reports__()

        if (reports is None) or (not self.__spo2_has_been_connected__ and len(reports) < 1):
            return []

        return [Spo2Report(
            report,
            self.__spo2_has_been_connected__) for report in reports]

    def get_co_report(
        self
    ) -> CoReport:
        report = self.__aithre_source__.get()
        self.__co_has_been_connected__ = self.__co_has_been_connected__ \
            or (report is not None and CO_LEVEL_KEY in report and report[CO_LEVEL_KEY] is not None)

        return CoReport(
            report,
            self.__co_has_been_connected__)

    def update_aithre(
        self
    ):
        """
        Calls the aithre manager and gets the current data from all devices.
        """
        try:
            self.__aithre_source__.update()
        except:
            pass

        try:
            self.__illyrian_source__.update()
        except:
            pass


AithreClient(configuration.CONFIGURATION.aithre_manager_address)

if __name__ == '__main__':
    while True:
        AithreClient.INSTANCE.update_aithre()
        time.sleep(5)
