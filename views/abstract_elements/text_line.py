from typing import List


class TextLine(object):
    """
    Holds information need to render a METAR
    on the screen.

    This split helps with pagination and grouping.
    """

    def __init__(self, color: List[int], text: str):
        self.color = color
        self.text = text
