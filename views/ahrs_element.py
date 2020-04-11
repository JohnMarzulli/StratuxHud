"""
Base class for AHRS view elements.
"""


class AhrsElement(object):
    GPS_UNAVAILABLE_TEXT = "NO GPS"
    INOPERATIVE_TEXT = "INOP"

    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True
