"""
Base class for AHRS view elements.
"""


class HudElement(object):
    def __init__(
        self,
        font,
        framebuffer_size
    ) -> None:
        super().__init__()

        border_margin = 0.01

        self.__font__ = font
        
        self.__framebuffer_size__ = framebuffer_size
        self.__center__ = (framebuffer_size[0] >> 1, framebuffer_size[1] >> 1)

        self.__width__ = framebuffer_size[0]
        self.__height__ = framebuffer_size[1]

        self.__right_border__ = int((1.0 - border_margin) * framebuffer_size[0])
        self.__left_border__ = int(framebuffer_size[0] * border_margin)

        self.__top_border__ = int(self.__height__ * border_margin)
        self.__bottom_border__ = self.__height__ - self.__top_border__

        self.__center_x__ = framebuffer_size[0] >> 1
        self.__center_y__ = framebuffer_size[1] >> 1

        self.__font_height__ =  int(font.get_height())
        self.__font_half_height__ = int(self.__font_height__ >> 1)

    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return False

class AhrsElement(HudElement):
    GPS_UNAVAILABLE_TEXT = "NO GPS"
    INOPERATIVE_TEXT = "INOP"

    def __init__(
        self,
        font,
        framebuffer_size
    ) -> None:
        super().__init__(font, framebuffer_size)
    
    def uses_ahrs(
        self
    ) -> bool:
        """
        Does this element use AHRS data to render?

        Returns:
            bool -- True if the element uses AHRS data.
        """

        return True
