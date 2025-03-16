"""
Gets any available NEXRAD imaging from the TrafficToHud service
and then helps render the images.
"""

import time

import requests

from common_utils import tasks
from configuration import configuration

# Example response:
# [
#   {
#     "reportTime": 1738533874860,
#     "reportType": "AIRMET",
#     "station": "KSFO",
#     "report": "010414 SFOS WA 010413 AMD\nAIRMET SIERRA UPDT 1 FOR IFR AND MTN OBSCN VALID UNTIL 010900\nAIRMET MTN OBSCN...WA OR CA\nFROM 80WSW YXC TO 20WSW DNJ TO 20SE REO TO 50SSE LKV TO 60E RBL\nTO RBL TO 30ENE ENI TO 30SW ENI TO 20SSW FOT TO ONP TO HQM TO\nTOU TO HUH TO 80WSW YXC\nMTNS OBSC BY CLDS/PCPN/BR. CONDS CONTG BYD 09Z THRU 15Z."
#   },
#   {
#     "reportTime": 1738533875061,
#     "reportType": "METAR",
#     "station": "KPLU",
#     "report": "010555Z AUTO 00000KT 10SM 04/04 A3002 RMK AO2="
#   },
#   {
#     "reportTime": 1738533875064,
#     "reportType": "METAR",
#     "station": "K4S2",
#     "report": "010555Z AUTO 00000KT 5SM RA SCT006 OVC017 01/01 A3011 RMK AO2="
#   },
#   {
#     "reportTime": 1738533875065,
#     "reportType": "METAR",
#     "station": "KS39",
#     "report": "010535Z AUTO 13007KT 8SM BKN030 BKN036 OVC110 01/M02 A3004 RMK AO2="
#   },
#   {
#     "reportTime": 1738533875066,
#     "reportType": "METAR",
#     "station": "KBVS",
#     "report": "010555Z AUTO 10005KT 10SM SCT029 BKN034 OVC049 05/01 A3007 RMK A01="
#   },
#   {
#     "reportTime": 1738533875066,
#     "reportType": "METAR",
#     "station": "KSZT",
#     "report": "010530Z AUTO 00000KT 10SM BKN032 BKN038 OVC060 00/M01 A3013 RMK AO2="
#   },
#   {
#     "reportTime": 1738533875067,
#     "reportType": "METAR",
#     "station": "K0S9",
#     "report": "010555Z AUTO 13007G13KT 10SM BKN046 BKN055 OVC075 05/02 A3002 RMK AO2="
#   },
#   {
#     "reportTime": 1738533875069,
#     "reportType": "METAR",
#     "station": "K6S2",
#     "report": "010555Z AUTO 00000KT 1 1/2SM -RA BR SCT003 SCT009 OVC019 06/06 A3005 RMK AO2 P0004="
#   },
#   {
#     "reportTime": 1738533875071,
#     "reportType": "METAR",
#     "station": "KS33",
#     "report": "010535Z AUTO 22003KT 10SM OVC065 00/M02 A3004 RMK AO2="
#   },
#   {
#     "reportTime": 1738533875072,
#     "reportType": "METAR",
#     "station": "K63S",
#     "report": "010535Z AUTO 00000KT 5SM BR OVC023 M02/M03 A3013 RMK A01Y4A"
#   }
# ]

class TextualReport:
    def __init__(self, report):
        self.report_time = report["reportTime"]
        self.station = report["station"]
        self.report_type = report["reportType"]
        self.report = report["report"]

class TextualWeatherClient:
    INSTANCE = None
    REPORTS = []

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

            TextualWeatherClient.REPORTS = []

            for raw_report in text_reports_json:
                report = TextualReport(raw_report)
                TextualWeatherClient.REPORTS.append(report)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

if __name__ == "__main__":
    import time

    textual_report_client = TextualWeatherClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    while True:
        time.sleep(5)

        for report in TextualWeatherClient.REPORTS:
            print(
                "    {0} - {1} - {2}".format(
                    report.station,
                    report.report_type,
                    report.report,
                )
            )
