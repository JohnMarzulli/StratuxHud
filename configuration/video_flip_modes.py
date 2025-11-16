from enum import IntEnum

class VideoFlipModes(IntEnum):
    """
    Ordinal values for if the video should be flipped. This is used so we can "wrap"
    the values in a cycle when using the keypad to change the configuration.
    """
    NORMAL = 0
    FLIP_HORIZONTAL = 1
    FLIP_VERTICAL = 2
    FLIP_BOTH = 3
