"""
Manages heading/target bugs.
"""


import configuration
import json


class Targets(object):

    def save(self):
        """
        Saves any targets to file.
        """

        try:
            with open(configuration.HEADING_BUGS_FILE, "w") as json_config_file:
                json_config_text = json.dumps({"bugs": self.targets})
                json_config_file.write(json_config_text)

            return True
        except:
            return False


    def clear_targets(self):
        """
        Clears any targets.
        """

        self.targets = []

    def add_target(self, latitude, longitude, altitude):
        """
        Adds the given lat/long as a target.
        
        Arguments:
            latitude {float} -- The latitude of the target.
            longitude {float} -- The longitude of the target.
            altitude {float} -- The altitude of the target.
        """

        if latitude is not None and longitude is not None:
            self.targets.append((latitude, longitude, altitude))

    def __init__(self):
        """
        Creates a new target manager.
        """

        self.targets = []

        try:
            with open(configuration.HEADING_BUGS_FILE) as json_config_file:
                json_config_text = json_config_file.read()
                json_config = json.loads(json_config_text)

                if json_config is not None and "bugs" in json_config:
                    for lat_long_altitude in json_config["bugs"]:
                        if len(lat_long_altitude) == 3:
                            self.add_target(lat_long_altitude[0], lat_long_altitude[1], lat_long_altitude[2])
        except:
            pass


if __name__ == '__main__':
    heading_bugs = Targets()

    print("Have {0} targets.".format(len(heading_bugs.targets)))

    for target in heading_bugs.targets:
        print("Target: {0}, {1}".format(target[0], target[1], target[2]))
    
    heading_bugs.save()
