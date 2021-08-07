"""
Module to abstract and centralize rendering code.
"""

from common_utils.local_debug import IS_SLOW

from rendering import display

if display.is_opengl_target():
    import rendering.opengl as renderer
else:
    import rendering.software as renderer


class HollowCircle:
    """
    Holds the information to draw an hollow (unfilled) circle
    """

    def __init__(
        self,
        center: list,
        radius: int,
        color: list,
        width: int = 1,
        is_antialiased: bool = not IS_SLOW
    ) -> None:
        """
        Create the circle to be drawn

        Args:
            center (list): The center of the circle (screen space)
            radius (int): The radius of the circle.
            color (list): The color of the circle.
            width (int, optional): The width of the circle. Defaults to 1
            is_antialiased (bool, optional): Should the circle be antialiased? Defaults to True.
        """

        super().__init__()

        self.__center__ = center
        self.__radius__ = radius
        self.__width__ = width
        self.__color__ = color
        self.__is_antialiased__ = is_antialiased

    def render(
        self,
        framebuffer
    ) -> None:
        """
        Draws the circle to the framebuffer

        Args:
            framebuffer: The framebuffer to draw to.
        """
        renderer.circle(
            framebuffer,
            self.__color__,
            self.__center__,
            self.__radius__,
            self.__width__,
            self.__is_antialiased__)


class FilledCircle:
    """
    Holds the information to draw an solid (filled) circle
    """

    def __init__(
        self,
        center: list,
        radius: int,
        color: list,
        is_antialiased: bool = not IS_SLOW
    ) -> None:
        """
        Create the circle to be drawn

        Args:
            center (list): The center of the circle (screen space)
            radius (int): The radius of the circle.
            color (list): The color of the circle.
            is_antialiased (bool, optional): Should the circle be antialiased? Defaults to True.
        """

        super().__init__()

        self.__center__ = center
        self.__radius__ = radius
        self.__color__ = color
        self.__is_antialiased__ = is_antialiased

    def render(
        self,
        framebuffer
    ) -> None:
        """
        Draws the circle to the framebuffer

        Args:
            framebuffer: The framebuffer to draw to.
        """

        renderer.filled_circle(
            framebuffer,
            self.__color__,
            self.__center__,
            self.__radius__,
            self.__is_antialiased__)


class Segment:
    """
    Holds the information for a line segment.
    """

    def __init__(
        self,
        start: list,
        end: list,
        color: list,
        width: int = 1,
        is_antialiased: bool = not IS_SLOW
    ) -> None:
        """
        Create the segment to be drawn.

        Args:
            start (list): The starting position of the segment (screen space)
            end (list): The ending position of the segment (screen space)
            color (list): The color of the segment
            width (int, optional): The width of the segment. Defaults to 1.
            is_antialiased (bool, optional): Is this antialiased? Defaults to True.
        """
        super().__init__()

        self.__start__ = start
        self.__end__ = end
        self.__color__ = color
        self.__width__ = width
        self.__is_anti_aliased__ = is_antialiased

    def render(
        self,
        framebuffer
    ) -> None:
        """
        Renders the segment.

        Args:
            framebuffer: The framebuffer to draw to.
        """
        renderer.segment(
            framebuffer,
            self.__color__,
            self.__start__,
            self.__end__,
            self.__width__,
            self.__is_anti_aliased__)


class Segments:
    """
    Holds the information for a set of connected line segment.
    These segments do not connect the final point back to the start.
    """

    def __init__(
        self,
        points: list,
        color: list,
        width: int = 1,
        is_antialiased: bool = not IS_SLOW
    ) -> None:
        """
        Create the segments to be drawn.

        Args:
            points (list): The starting to ending points of the segment sets (screen space)
            color (list): The color of the segment
            width (int, optional): The width of the segment. Defaults to 1.
            is_antialiased (bool, optional): Is this antialiased? Defaults to True.
        """

        super().__init__()

        self.__points__ = points
        self.__color__ = color
        self.__width__ = width
        self.__is_anti_aliased__ = is_antialiased

    def render(
        self,
        framebuffer
    ) -> None:
        """
        Render the segments to the framebuffer

        Args:
            framebuffer: The framebuffer to draw to.
        """

        renderer.segments(
            framebuffer,
            self.__color__,
            False,
            self.__points__,
            self.__width__,
            self.__is_anti_aliased__)


class HollowPolygon:
    """
    Stores the info for a hollow (unfilled) polylon.
    """

    def __init__(
        self,
        points: list,
        color: list,
        width: int,
        is_antialiased: bool = not IS_SLOW
    ) -> None:
        """
        Create the polygon to be drawn. This is unfilled

        Args:
            points (list): The points of the segment that define the polygon (screen space)
            color (list): The color of the polygon's outline
            width (int, optional): The width of the polygon's outline. Defaults to 1.
            is_antialiased (bool, optional): Is this antialiased? Defaults to True.
        """

        super().__init__()

        self.__points__ = points
        self.__color__ = color
        self.__width__ = width
        self.__is_anti_aliased__ = is_antialiased

    def render(
        self,
        framebuffer
    ) -> None:
        """
        Renders the polygon.

        Args:
            framebuffer: The framebuffer to draw to.
        """
        renderer.segments(
            framebuffer,
            self.__color__,
            True,
            self.__points__,
            self.__width__,
            self.__is_anti_aliased__)


class FilledPolygon:
    """
    Stores the info for a solid (filled) polylon.
    """

    def __init__(
        self,
        points: list,
        color: list,
        is_antialiased: bool = not IS_SLOW
    ) -> None:
        """
        Create the polygon to be drawn. This is solid/filled

        Args:
            points (list): The points of the segment that define the polygon (screen space)
            color (list): The color of the polygon
            is_antialiased (bool, optional): Is this antialiased? Defaults to True.
        """

        super().__init__()

        self.__points__ = points
        self.__color__ = color
        self.__is_anti_aliased__ = is_antialiased

    def render(
        self,
        framebuffer
    ) -> None:
        """
        Renders the polygon.

        Args:
            framebuffer: The framebuffer to draw to.
        """
        renderer.polygon(
            framebuffer,
            self.__color__,
            self.__points__,
            self.__is_anti_aliased__)
