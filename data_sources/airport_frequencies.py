class AirportFrequency:
    """
    Holds frequency data as pulled from the TrafficToHud service
    """
    def __init__(self, report):
        self.coordinates = [
            report["coordinates"]["latitude"],
            report["coordinates"]["longitude"],
        ]
        self.facilityId = report["facilityId"]
        self.facilityName = report["facilityName"]
        self.facilityType = report["facilityType"]
        self.artcOrFssId = report["artcOrFssId"]
        self.serviceSiteType = report["serviceSiteType"]
        self.towerOrComFreq = report["towerOrComFreq"]
        self.approachFreq = report["approachFreq"]
        self.frequency = report["frequency"]

        # LCL/P local control tower / primary
        # LCL/S local control tower / secondary
        # GND/P ground / primary
        # GND/S ground / secondary
        # CD/P clearance delivery / primary
        self.frequencyName = report["frequencyName"]
        self.remarks = report["remarks"]
