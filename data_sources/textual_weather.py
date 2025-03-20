"""
Gets any available NEXRAD imaging from the TrafficToHud service
and then helps render the images.
"""

import json
import threading
from typing import Dict, List

import requests

from common_utils import tasks
from configuration import configuration


class TextualReport:
    def __init__(self, report):
        self.report_time = report["reportTime"]
        self.station = report["station"]
        self.report_type = report["reportType"]
        self.report = report["report"]


class TextualWeatherClient:
    INSTANCE = None

    __REPORTS__: Dict[str, List[TextualReport]] = {}
    __LOCK_OBJECT__ = threading.Lock()

    def __init__(self, rest_address: str):
        self.__textual_weather_session__ = requests.Session()
        self.rest_address = rest_address
        self.__update_traffic_task__ = tasks.RecurringTask(
            "UpdateTextualWeather", 15, self.update_textual_weather
        )
        TextualWeatherClient.INSTANCE = self

    def update_textual_weather(self):
        try:
            text_reports_json = self.__textual_weather_session__.get(
                f"http://{self.rest_address}/Weather/TextReports",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            TextualWeatherClient.inject_report(text_reports_json)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    @staticmethod
    def get_metars() -> Dict[str, TextualReport]:
        return TextualWeatherClient.__get_text_report__("METAR")

    @staticmethod
    def get_tafs() -> Dict[str, TextualReport]:
        return TextualWeatherClient.__get_text_report__("TAF")

    @staticmethod
    def get_airmets() -> Dict[str, TextualReport]:
        return TextualWeatherClient.__get_text_report__("AIRMET")

    @staticmethod
    def inject_report(text_reports: Dict[str, List[TextualReport]]):
        TextualWeatherClient.__LOCK_OBJECT__.acquire()

        try:
            TextualWeatherClient.__REPORTS__ = {}

            for report_type in text_reports:
                TextualWeatherClient.__REPORTS__[report_type] = []

                for raw_report in text_reports[report_type]:
                    report = TextualReport(raw_report)
                    TextualWeatherClient.__REPORTS__[report_type].append(report)
        finally:
            TextualWeatherClient.__LOCK_OBJECT__.release()

    @staticmethod
    def __get_text_report__(report: str) -> Dict[str, TextualReport]:
        TextualWeatherClient.__LOCK_OBJECT__.acquire()

        if report is None or len(report) < 1:
            return {}

        try:
            reports = {}

            if report not in TextualWeatherClient.__REPORTS__:
                return reports

            for report in TextualWeatherClient.__REPORTS__[report]:
                reports[report.station] = report
        finally:
            TextualWeatherClient.__LOCK_OBJECT__.release()

        return reports


def load_sample_text_reports():
    full_file_path = configuration.get_absolute_file_path(
        "../test_data/example_metar_data.json"
    )

    with open(full_file_path) as json_test_data_file:
        json_config_text = json_test_data_file.read()
        test_data_json = json.loads(json_config_text)

        TextualWeatherClient.inject_report(test_data_json)


text_weather_client = TextualWeatherClient(
    configuration.CONFIGURATION.get_traffic_manager_address()
)
