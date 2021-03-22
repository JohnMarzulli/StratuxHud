"""
Module to handle rendering text throught the rendering abstraction layer.
"""

import pygame
from common_utils import generic_data_cache

from rendering import colors
from rendering.drawing import renderer

__TEXT_CACHE__ = generic_data_cache.GenericDataCache()


def __get_text_texture_key__(
    font: pygame.font,
    text: str,
    color: list,
    bg_color: list = colors.BLACK,
    scale: float = 1.0,
    rotation: float = 0.0,
    use_alpha: bool = False
) -> str:
    return "{}{}{}{}{}{}{}".format(
        hash(font),
        text,
        color,
        bg_color,
        scale,
        rotation,
        use_alpha)


def __get_text_texture__(
    font,
    text: str,
    text_color: list = colors.BLACK,
    background_color: list = colors.YELLOW,
    scale: float = 1.0,
    rotation: float = 0.0,
    use_alpha: bool = False
) -> list:

    use_alpha |= background_color is None

    texture = font.render(
        text,
        True,
        text_color,
        background_color)

    texture = pygame.transform.rotozoom(
        texture,
        rotation,
        scale)

    size = texture.get_size()

    if use_alpha:
        texture.set_colorkey([0, 0, 0])
        texture = texture.convert_alpha()
        texture.set_colorkey([0, 0, 0])
    else:
        texture = texture.convert()

    return texture, size


def get_or_create_text_texture(
    font: pygame.font,
    text: str,
    color: list,
    bg_color: list = colors.BLACK,
    use_alpha: bool = False,
    scale: float = 1.0,
    rotation: float = 0.0
) -> list:
    """
    Used to generate, but not yet draw text.
    This is normally used when the size of the texture
    is used in the calculation of the draw position.

    Args:
        font (pygame.font): The font to display the text with.
        text (str): The text to draw
        color (list): The color of the text
        bg_color (list, optional): The background color of the text. Defaults to colors.BLACK.
        use_alpha (bool, optional): Do we want to use alpha with the text? Defaults to False.
        scale (float, optional): The scale of the text. Defaults to 1.0.
        rotation (float, optional): Any rotation to apply to the text. Defaults to 0.

    Returns:
        list: [description]
    """
    key = __get_text_texture_key__(
        font,
        text,
        color,
        bg_color,
        scale,
        rotation,
        use_alpha)

    texture, size = __TEXT_CACHE__.get_or_create_data(
        key,
        lambda: __get_text_texture__(font, text, color, bg_color, scale, rotation, use_alpha))

    return key, texture, size


def render_cached_texture(
    framebuffer,
    cache_key: str,
    position: list
) -> None:
    """
    Draws a texture that has a known cache key.
    This is normally used when the size of the texture
    is used in the calculation of the draw position.

    Args:
        framebuffer: The texture being rendered to.
        cache_key (str): The key to the stored texture.
        position (list): The UL position to start drawing the texture.
    """
    texture, size = __TEXT_CACHE__.get_data(cache_key)

    if texture is not None:
        renderer.draw_sprite(
            framebuffer,
            position,
            texture)


def render_text(
    framebuffer,
    font: pygame.font,
    text: str,
    position: list,
    color: list,
    bg_color: list = colors.BLACK,
    use_alpha: bool = False,
    scale: float = 1.0,
    rotation: float = 0.0
) -> list:
    """
    Render text to the screen (2d)

    Args:
        framebuffer: The texture being rendered to.
        font (pygame.font): The font to display the text with.
        text (str): The text to draw
        position (list): The Upper Left hand corner to position the text at.
        color (list): The color of the text
        bg_color (list, optional): The background color of the text. Defaults to colors.BLACK.
        use_alpha (bool, optional): Do we want to use alpha with the text? Defaults to False.
        scale (float, optional): The scale of the text. Defaults to 1.0.
        rotation (float, optional): Any rotation to apply to the text. Defaults to 0.

    Returns:
        list: [description]
    """

    key, texture, size = get_or_create_text_texture(
        font,
        text,
        color,
        bg_color,
        use_alpha,
        scale,
        rotation)

    if texture is not None:
        renderer.draw_sprite(
            framebuffer,
            position,
            texture)

        return size
