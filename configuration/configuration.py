import contextlib
import json
import os
from os.path import expanduser

import requests
from common_utils import tasks, units
from data_sources import receiver_capabilities, receiver_status

EARTH_RADIUS_NAUTICAL_MILES = 3440
EARTH_RADIUS_STATUTE_MILES = 3956
EARTH_RADIUS_KILOMETERS_MILES = 6371
MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT = 2
MAX_FRAMERATE = 60
TARGET_AHRS_FRAMERATE = 30
AHRS_TIMEOUT = 10.0 * (1.0 / float(TARGET_AHRS_FRAMERATE))
DEFAULT_VIEW_KEY = "default_view"

VERSION = "2.0"

########################
# Default Config Files #
########################
#
# Base, default values.
# There are two config files. One is the
# default that everything falls back to
# The other is the user saved and modified
# file that is merged in
__config_file__ = '../config.json'
__view_elements_file__ = '../elements.json'
__views_file__ = '../views.json'


#####################
# User Config Files #
#####################
#
# These are the user modified files
# that are merged in with the system
# defaults, overriding what is set.
__user_path__ = expanduser('~')
__user_views_file__ = f"{__user_path__}/hud_views.json"
__user_config_file__ = f"{__user_path__}/hud_config.json"
__heading_bugs_file__ = f"{__user_path__}/hud_heading_bugs.json"

__working_dir__ = os.path.dirname(os.path.abspath(__file__))


def get_absolute_file_path(
    relative_path: str
) -> str:
    """
    Returns the absolute file path no matter the OS.

    Arguments:
        relative_path {string} -- The relative file path.

    Returns:
        string -- The absolute filepath.
    """

    return os.path.join(__working_dir__, os.path.normpath(relative_path))


# System Default Config Files
DEFAULT_CONFIG_FILE = get_absolute_file_path(__config_file__)
VIEW_ELEMENTS_FILE = get_absolute_file_path(__view_elements_file__)
VIEWS_FILE = get_absolute_file_path(__views_file__)
HEADING_BUGS_FILE = get_absolute_file_path(__heading_bugs_file__)


class DataSourceNames(object):
    STRATUX = "stratux"
    SIMULATION = "simulation"


class Configuration(object):
    ###############################
    # Hardcoded Config Fall Backs #
    ###############################
    #
    # These are here in case the user does something
    # bad to the default config files.
    #
    DEFAULT_NETWORK_IP = "192.168.10.1"
    DEFAULT_AVIONICS_ADDRESS = "localhost:8180"

    DEFAULT_TRAFFIC_MANAGER_ADDRESS = "localhost:8000"
    DEFAULT_AITHRE_MANAGER_ADDRESS = "localhost:8081"
    STRATUX_ADDRESS_KEY = "stratux_address"
    AVIONICS_ADDRESS_KEY = "avionics_address"
    DATA_SOURCE_KEY = "data_source"
    FLIP_HORIZONTAL_KEY = "flip_horizontal"
    FLIP_VERTICAL_KEY = "flip_vertical"
    OWNSHIP_KEY = "ownship"
    MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY = "traffic_report_removal_minutes"
    DISTANCE_UNITS_KEY = "distance_units"
    ENABLE_DECLINATION_KEY = "enable_declination"
    DECLINATION_KEY = "declination"
    DEGREES_OF_PITCH_KEY = 'degrees_of_pitch'
    PITCH_DEGREES_DISPLAY_SCALER_KEY = 'pitch_degrees_scaler'
    AITHRE_KEY = 'aithre'
    TRAFFIC_MANAGER_KEY = 'traffic_manager'
    AITHRE_MANAGER_KEY = 'aithre_manager'

    DEFAULT_DEGREES_OF_PITCH = 90
    DEFAULT_PITCH_DEGREES_DISPLAY_SCALER = 2.0

    def get_elements_list(
        self
    ):
        """
        Returns the list of elements available for the views.
        """

        return self.__load_config_from_json_file__(VIEW_ELEMENTS_FILE)

    def __load_views_from_file__(
        self,
        file_name: str
    ) -> dict:
        views_key = 'views'

        with contextlib.suppress(Exception):
            full_views_contents = self.__load_config_from_json_file__(
                file_name)

            if full_views_contents is not None and len(full_views_contents) > 0:
                return full_views_contents[views_key] if views_key in full_views_contents else full_views_contents

        return None

    def get_views_list(
        self
    ) -> list:
        """
        Loads the view configuration file.
        First looks for a user configuration file.
        If there is one, and the file is valid, then
        returns those contents.

        If there is an issue with the user file,
        then returns the system level default.

        Returns:
            array -- Array of dictionary. Each element contains the name of the view and a list of elements it is made from.
        """
        try:
            if self.__hud_views__ is None:
                self.__hud_views__ = self.__load_views_from_file__(
                    __user_views_file__)

            if self.__hud_views__ is None:
                self.__hud_views__ = self.__load_views_from_file__(VIEWS_FILE)

            if self.__hud_views__ is not None and any(self.__hud_views__):
                return self.__hud_views__

            return []
        except Exception:
            return []

    def write_views_list(
        self,
        view_config
    ):
        """
        Writes the view configuration to the user's version of the file.
        """

        try:
            with open(__user_views_file__, 'w') as configfile:
                configfile.write(view_config)
        except Exception:
            print("ERROR trying to write user views file.")

    def get_json_from_text(
        self,
        text: str
    ) -> dict:
        """
        Takes raw text and imports it into JSON.
        """

        return json.loads(text)

    def get_json_from_config(
        self
    ) -> dict:
        """
        Returns the current config as JSON text.

        REMARK: Returns everything back as a string...
                That is probably safer, but not nearly
                as convenient as I want
        """
        config_dictionary = {
            Configuration.STRATUX_ADDRESS_KEY: self.stratux_address(),
            Configuration.DATA_SOURCE_KEY: self.data_source(),
            Configuration.FLIP_HORIZONTAL_KEY: self.flip_horizontal,
            Configuration.FLIP_VERTICAL_KEY: self.flip_vertical,
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY: self.max_minutes_before_removal,
            Configuration.DISTANCE_UNITS_KEY: self.get_units(),
            Configuration.ENABLE_DECLINATION_KEY: self.__is_declination_enabled__,
            Configuration.DEGREES_OF_PITCH_KEY: self.get_degrees_of_pitch(),
            Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY: self.get_pitch_degrees_display_scaler(),
            Configuration.AITHRE_KEY: self.aithre_enabled,
            Configuration.TRAFFIC_MANAGER_KEY: self.get_traffic_manager_address(),
            DEFAULT_VIEW_KEY: self.__view_index__
        }

        return json.dumps(config_dictionary, indent=4, sort_keys=True)

    def write_config(
        self
    ):
        """
        Writes the config file to the user's file.

        """

        try:
            config_to_write = self.get_json_from_config()

            with open(__user_config_file__, 'w') as configfile:
                configfile.write(config_to_write)
        except Exception:
            print("ERROR trying to write user config file.")

    def set_from_json(
        self,
        json_config: dict
    ):
        """
        Takes a JSON package and sets the config using the JSON
        """

        if json_config is None:
            return

        set_from_maps = [Configuration.STRATUX_ADDRESS_KEY,
                         Configuration.DATA_SOURCE_KEY]

        for key in set_from_maps:
            if key in json_config:
                self.__configuration__[key] = json_config[key]

        if Configuration.AITHRE_KEY in json_config:
            self.aithre_enabled = bool(json_config[Configuration.AITHRE_KEY])
            self.__configuration__[Configuration.AITHRE_KEY] = \
                self.aithre_enabled

        if Configuration.FLIP_HORIZONTAL_KEY in json_config:
            self.flip_horizontal = \
                bool(json_config[Configuration.FLIP_HORIZONTAL_KEY])
            self.__configuration__[Configuration.FLIP_HORIZONTAL_KEY] = \
                self.flip_horizontal

        if Configuration.FLIP_VERTICAL_KEY in json_config:
            self.flip_vertical = \
                bool(json_config[Configuration.FLIP_VERTICAL_KEY])
            self.__configuration__[Configuration.FLIP_VERTICAL_KEY] = \
                self.flip_vertical

        if Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY in json_config:
            self.max_minutes_before_removal = float(
                json_config[Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY])
            self.__configuration__[
                Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY] = self.max_minutes_before_removal

        if Configuration.DISTANCE_UNITS_KEY in json_config:
            self.units = json_config[Configuration.DISTANCE_UNITS_KEY]
            self.__configuration__[
                Configuration.DISTANCE_UNITS_KEY] = self.units

        if Configuration.ENABLE_DECLINATION_KEY in json_config:
            self.__is_declination_enabled__ = bool(json_config[Configuration.ENABLE_DECLINATION_KEY])
            self.__configuration__[Configuration.ENABLE_DECLINATION_KEY] = self.__is_declination_enabled__

        if Configuration.DEGREES_OF_PITCH_KEY in json_config:
            self.degrees_of_pitch = int(
                json_config[Configuration.DEGREES_OF_PITCH_KEY])
            self.__configuration__[
                Configuration.DEGREES_OF_PITCH_KEY] = self.degrees_of_pitch

        if Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY in json_config:
            self.pitch_degrees_display_scaler = float(
                json_config[Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY])
            self.__configuration__[
                Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY] = self.pitch_degrees_display_scaler

        if Configuration.TRAFFIC_MANAGER_KEY in json_config:
            self.traffic_manager_address = json_config[Configuration.TRAFFIC_MANAGER_KEY]
            self.__configuration__[
                Configuration.TRAFFIC_MANAGER_KEY] = self.traffic_manager_address

    def __get_config_value__(
        self,
        key: str,
        default_value
    ):
        """
        Returns a configuration value, default if not found.
        """

        if self.__configuration__ is not None and key in self.__configuration__:
            return self.__configuration__[key]

        return default_value

    def get_degrees_of_pitch(
        self
    ) -> int:
        """
        Returns the number of degrees of pitch for the AH ladder.

        Returns:
            float -- Returns the number of degrees of pitch for the AH ladder.
        """

        return self.degrees_of_pitch

    def get_pitch_degrees_display_scaler(
        self
    ) -> float:
        """
        Returns the amount of adjustment to the pitch ladder

        Returns:
            [type] -- [description]
        """

        return self.pitch_degrees_display_scaler

    def is_declination_enabled(
        self
    ) -> bool:
        """
        Returns TRUE if declination calculations should be enabled
        to headings and things.

        Returns:
            bool: True if declination calculations should be enabled.
        """

        return self.__is_declination_enabled__

    def set_declination_enabled(
        self,
        is_enabled: bool
    ):
        """
        Set if declination calculations are enabled or not.

        Args:
            is_enabled (bool): True if declination calculations are enabled.
        """

        self.__is_declination_enabled__ = is_enabled

    def get_traffic_manager_address(
        self
    ) -> str:
        """
        Returns the address we should use for the traffic manager
        """

        return self.traffic_manager_address

    def get_aithre_manager_address(
        self
    ) -> str:
        """
        Returns the address of the REST service that is providing
        Aithre connectivity.
        """
        return self.aithre_manager_address

    def get_units(
        self
    ) -> str:
        """
        Returns the units that the display should use.

        Returns:
            string -- The type of units.
        """

        return self.__get_config_value__(self.DISTANCE_UNITS_KEY, units.STATUTE)

    def data_source(
        self
    ) -> str:
        """
        Returns the data source to use.
        """

        return self.__get_config_value__(Configuration.DATA_SOURCE_KEY, DataSourceNames.STRATUX)

    def avionics_address(
        self
    ) -> str:
        """
        Returns the address for the avionics adapter.
        """
        return self.__get_config_value__(Configuration.AVIONICS_ADDRESS_KEY, Configuration.DEFAULT_AVIONICS_ADDRESS)

    def stratux_address(
        self
    ) -> str:
        """
        Returns the stratux address.
        """

        return self.__get_config_value__(Configuration.STRATUX_ADDRESS_KEY, Configuration.DEFAULT_NETWORK_IP)

    def get_view_index(
        self
    ) -> int:
        """
        Returns the current index of the view
        that should be displayed.

        The index is relative (index 0) to the views
        configuration that is loaded from the views.json file.
        """
        return self.__view_index__

    def next_view(
        self,
        hud_views: list
    ):
        """
        Changes to the next view.

        Wraps around to the first view if we try to go past the last view.
        """
        self.__view_index__ = self.__clamp_view__(
            hud_views,
            self.__view_index__ + 1)

        self.__save_view__()

    def previous_view(
        self,
        hud_views: list
    ):
        """
        Changes to the previous view.

        Wraps around to the last view if we try to "go previous"
        of the first view.
        """
        self.__view_index__ = self.__clamp_view__(
            hud_views,
            self.__view_index__ - 1)

        self.__save_view__()

    def get_default_view_index(
        self
    ):
        with contextlib.suppress(Exception):
            return self.__configuration__[DEFAULT_VIEW_KEY]

        return 0

    def __save_view__(
        self
    ):
        self.__configuration__[DEFAULT_VIEW_KEY] = self.__view_index__
        self.write_config()

    def __clamp_view__(
        self,
        hud_views: list,
        new_index: int
    ) -> int:
        """
        Makes sure that the view index is within bounds.
        """

        num_views = len(hud_views)

        if new_index >= num_views:
            return 0

        if new_index < 0:
            return num_views - 1

        return new_index

    def update_configuration(
        self,
        json_config: dict
    ) -> dict:
        """
        Given a new piece of configuration, update it gracefully.

        Arguments:
            json_config {dict} -- The new configuration... partial or whole.

        Returns:
            dict -- The updated configuration.
        """

        if json_config is None:
            return self.__configuration__.copy()

        self.__configuration__.update(json_config)
        self.set_from_json(self.__configuration__)
        self.write_config()

        return self.__configuration__.copy()

    def unescape_json_config_contents(
        self,
        unescaped_contents: str
    ) -> str:
        """
        Takes a piece of JSON loaded from file and then makes sure that the file
        is unescaped to remove any prefix/suffix quotation marks and fix any line
        ending issues before it is decoded into an object.
        """

        if unescaped_contents is None:
            return ''

        quotation_mark = '"'

        escaped_contents = unescaped_contents.decode('string_escape')

        escaped_contents = escaped_contents[escaped_contents.startswith(
            quotation_mark) and len(quotation_mark):]

        if escaped_contents.endswith(quotation_mark):
            escaped_contents = escaped_contents[:-len(quotation_mark)]

        escaped_contents = escaped_contents.strip()

        return escaped_contents

    def __load_config_from_json_file__(
        self,
        json_config_file: str
    ) -> dict:
        """
        Loads the complete configuration into the system.
        Uses the default values as a base, then puts the
        user's configuration overtop.
        """
        try:
            with open(json_config_file) as json_config_file:
                json_config_text = json_config_file.read()
                return json.loads(json_config_text)
        except Exception:
            return {}

    def __load_configuration__(
        self,
        default_config_file: str,
        user_config_file: str
    ) -> dict:
        """
        Loads the configuration.
        """

        config = self.__load_config_from_json_file__(default_config_file)
        user_config = self.__load_config_from_json_file__(user_config_file)

        if user_config is not None:
            config.update(user_config)

        return config

    def __update_capabilities__(
        self
    ):
        """
        Check occasionally to see if the settings
        for the Stratux have been changed that would
        affect what we should show and what is actually
        available.
        """
        self.capabilities = receiver_capabilities.StratuxCapabilities(
            self.stratux_address(), self.__stratux_session__, None)
        self.stratux_status = receiver_status.StratuxStatus(
            self.stratux_address(), self.__stratux_session__, None)

    def __init__(
        self,
        default_config_file: str,
        user_config_file: str
    ):
        self.__view_index__ = 0
        self.__hud_views__ = None
        self.get_views_list()
        self.degrees_of_pitch = Configuration.DEFAULT_DEGREES_OF_PITCH
        self.pitch_degrees_display_scaler = Configuration.DEFAULT_PITCH_DEGREES_DISPLAY_SCALER
        self.__configuration__ = self.__load_configuration__(
            default_config_file,
            user_config_file)
        self.max_minutes_before_removal = self.__get_config_value__(
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY,
            MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT)
        self.log_filename = "stratux_hud.log"

        self.flip_horizontal = self.__get_config_value__(
            Configuration.FLIP_HORIZONTAL_KEY,
            False)
        self.flip_vertical = self.__get_config_value__(
            Configuration.FLIP_VERTICAL_KEY,
            False)
        self.__is_declination_enabled__ = self.__get_config_value__(
            Configuration.ENABLE_DECLINATION_KEY,
            False)
        self.aithre_enabled = self.__get_config_value__(
            Configuration.AITHRE_KEY,
            True)
        self.traffic_manager_address = self.__get_config_value__(
            Configuration.TRAFFIC_MANAGER_KEY,
            Configuration.DEFAULT_TRAFFIC_MANAGER_ADDRESS)
        self.aithre_manager_address = self.__get_config_value__(
            Configuration.AITHRE_MANAGER_KEY,
            Configuration.DEFAULT_AITHRE_MANAGER_ADDRESS)
        self.__stratux_session__ = requests.Session()

        self.stratux_status = receiver_status.StratuxStatus(
            self.stratux_address(),
            self.__stratux_session__, None)
        self.capabilities = receiver_capabilities.StratuxCapabilities(
            self.stratux_address(),
            self.__stratux_session__, None)
        tasks.RecurringTask(
            'UpdateCapabilities',
            15,
            self.__update_capabilities__)

        self.__view_index__ = self.get_default_view_index()

        self.set_from_json(self.__configuration__)

        # Example config
        # "stratux_address": "192.168.10.1",
        #   "distance_units": "statute",
        #   "traffic_report_removal_minutes": 1,
        #   "flip_horizontal": false,
        #   "flip_vertical": false,
        #   "ownship": "N701GV",
        #   "data_source": "stratux",
        #   "declination_enabled": true,
        #   "declination": 0.0


CONFIGURATION = Configuration(DEFAULT_CONFIG_FILE, __user_config_file__)

if __name__ == '__main__':
    from_config = CONFIGURATION.get_json_from_config()
    CONFIGURATION.write_config()
