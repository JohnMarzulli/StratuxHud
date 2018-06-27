"""
Base class for AHRS view elements.
"""

class AhrsElement(object):
    def uses_ahrs(self):
        """
        Does this element use AHRS data to render?
               
        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True
