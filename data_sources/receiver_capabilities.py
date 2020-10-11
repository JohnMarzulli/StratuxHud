from common_utils.logger import HudLogger
from common_utils.logging_object import LoggingObject


class StratuxCapabilities(LoggingObject):
    """
    Get the capabilities of the Stratux, so we know what can be used
    in the HUD.
    """

    def __get_value__(
        self,
        key: str
    ):
        """
        Gets the string value from the JSON, or None if it can't be found.
        """
        if key is None:
            return None

        if self.__capabilities_json__ is None:
            return None

        if key in self.__capabilities_json__:
            try:
                return self.__capabilities_json__[key]
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_capability__ EX={}".format(ex))
                return None

        return None

    def __get_capability__(
        self,
        key: str
    ) -> bool:
        """
        Returns a boolean from the json.
        """
        if key is None:
            return False

        if self.__capabilities_json__ is None:
            return False

        if key in self.__capabilities_json__:
            try:
                return bool(self.__capabilities_json__[key])
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_capability__ EX={}".format(ex))
                return False

        return False

    def __init__(
        self,
        stratux_address: str,
        stratux_session,
        logger: HudLogger = None,
        simulation_mode: bool = False
    ):
        """
        Builds a list of Capabilities of the stratux.
        """

        super(StratuxCapabilities, self).__init__(logger)

        if stratux_address is None or simulation_mode:
            self.__capabilities_json__ = None
            self.traffic_enabled = False
            self.gps_enabled = False
            self.barometric_enabled = True
            self.ahrs_enabled = True
            self.ownship_mode_s = None
        else:
            url = "http://{0}/getSettings".format(stratux_address)

            try:
                self.__capabilities_json__ = stratux_session.get(
                    url, timeout=2).json()

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.__capabilities_json__ = {}
                self.warn("EX in __init__ ex={}".format(ex))

            self.traffic_enabled = self.__get_capability__('UAT_Enabled')
            self.gps_enabled = self.__get_capability__('GPS_Enabled')
            self.barometric_enabled = self.__get_capability__(
                'BMP_Sensor_Enabled')
            self.ahrs_enabled = self.__get_capability__('IMU_Sensor_Enabled')
            self.ownship_mode_s = self.__get_value__('OwnshipModeS')

            try:
                # Ownship is in Hex... traffic reports come in int...
                self.ownship_icao = int(
                    self.ownship_mode_s, 16) if self.ownship_mode_s is not None else 0
            except:
                self.ownship_icao = 0
            # http://192.168.10.1/getSettings - get device settings. Example output:
            #
            # {
            #     "UAT_Enabled": true,
            #     "ES_Enabled": true,
            #     "Ping_Enabled": false,
            #     "GPS_Enabled": true,
            #     "BMP_Sensor_Enabled": true,
            #     "IMU_Sensor_Enabled": true,
            #     "NetworkOutputs": [
            #         {
            #             "Conn": null,
            #             "Ip": "",
            #             "Port": 4000,
            #             "Capability": 5,
            #             "MessageQueueLen": 0,
            #             "LastUnreachable": "0001-01-01T00:00:00Z",
            #             "SleepFlag": false,
            #             "FFCrippled": false
            #         }
            #     ],
            #     "SerialOutputs": null,
            #     "DisplayTrafficSource": false,
            #     "DEBUG": false,
            #     "ReplayLog": false,
            #     "AHRSLog": false,
            #     "IMUMapping": [
            #         2,
            #         0
            #     ],
            #     "SensorQuaternion": [
            #         0.017336041263077348,
            #         0.7071029888451218,
            #         0.7068942365539764,
            #         -0.0023158510746434354
            #     ],
            #     "C": [
            #         -0.02794518875698111,
            #         0.021365398113956116,
            #         -1.0051649525437176
            #     ],
            #     "D": [
            #         -0.43015839106418047,
            #         -0.0019837031159398175,
            #         -1.2866603595080415
            #     ],
            #     "PPM": 0,
            #     "OwnshipModeS": "F00000",
            #     "WatchList": "",
            #     "DeveloperMode": false,
            #     "GLimits": "",
            #     "StaticIps": [],
            #     "WiFiSSID": "stratux",
            #     "WiFiChannel": 1,
            #     "WiFiSecurityEnabled": false,
            #     "WiFiPassphrase": ""
            # }
