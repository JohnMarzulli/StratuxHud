from common_utils.logger import HudLogger
from common_utils.logging_object import LoggingObject


class StratuxStatus(LoggingObject):
    """
    Object to hold retrieved status about the ADS-B receiver
    """

    def __get_status__(
        self,
        key: str
    ) -> bool:
        if key is None:
            return False

        if self.__status_json__ is None:
            return False

        if key in self.__status_json__:
            try:
                return bool(self.__status_json__[key])
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_status__ EX={}".format(ex))
                return False

        return False

    def __init__(
        self,
        stratux_address: str,
        stratux_session,
        logger: HudLogger,
        simulation_mode: bool = False
    ):
        """
        Builds the ADS-B In receiver's status
        """

        super(StratuxStatus, self).__init__(logger)

        if stratux_address is None or simulation_mode:
            self.__status_json__ = None
            self.cpu_temp = 50.0
            self.satellites_locked = 0

        else:
            url = "http://{0}/getStatus".format(stratux_address)

            try:
                self.__status_json__ = stratux_session.get(
                    url, timeout=2).json()

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_status__ EX={}".format(ex))
                self.__status_json__ = {}

            self.cpu_temp = self.__get_status__('CPUTemp')
            self.satellites_locked = self.__get_status__(
                'GPS_satellites_locked')

            # Results of a getStatus call
            # {
            #     "Version": "v1.5b2",
            #     "Build": "8f4a52d7396c0dc20270e7644eebe5d9fc49eed9",
            #     "HardwareBuild": "",
            #     "Devices": 2,
            #     "Connected_Users": 1,
            #     "DiskBytesFree": 367050752,
            #     "UAT_messages_last_minute": 0,
            #     "UAT_messages_max": 38,
            #     "ES_messages_last_minute": 1413,
            #     "ES_messages_max": 6522,
            #     "UAT_traffic_targets_tracking": 0,
            #     "ES_traffic_targets_tracking": 5,
            #     "Ping_connected": false,
            #     "UATRadio_connected": false,
            #     "GPS_satellites_locked": 12,
            #     "GPS_satellites_seen": 13,
            #     "GPS_satellites_tracked": 19,
            #     "GPS_position_accuracy": 3,
            #     "GPS_connected": true,
            #     "GPS_solution": "GPS + SBAS (WAAS)",
            #     "GPS_detected_type": 55,
            #     "Uptime": 3261140,
            #     "UptimeClock": "0001-01-01T00:54:21.14Z",
            #     "CPUTemp": 49.925,
            #     "CPUTempMin": 44.546,
            #     "CPUTempMax": 55.843,
            #     "NetworkDataMessagesSent": 3080,
            #     "NetworkDataMessagesSentNonqueueable": 3080,
            #     "NetworkDataBytesSent": 89047,
            #     "NetworkDataBytesSentNonqueueable": 89047,
            #     "NetworkDataMessagesSentLastSec": 3,
            #     "NetworkDataMessagesSentNonqueueableLastSec": 3,
            #     "NetworkDataBytesSentLastSec": 84,
            #     "NetworkDataBytesSentNonqueueableLastSec": 84,
            #     "UAT_METAR_total": 0,
            #     "UAT_TAF_total": 0,
            #     "UAT_NEXRAD_total": 0,
            #     "UAT_SIGMET_total": 0,
            #     "UAT_PIREP_total": 0,
            #     "UAT_NOTAM_total": 0,
            #     "UAT_OTHER_total": 0,
            #     "Errors": [],
            #     "Logfile_Size": 90107,
            #     "AHRS_LogFiles_Size": 0,
            #     "BMPConnected": true,
            #     "IMUConnected": true,
            #     "NightMode": false
            # }
