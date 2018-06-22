"""
Handle loading relative imports so the view can be run in standalone modes
for development and testing.
"""


def load_imports():
    """
    Load the imports from relative directories when in local debug modes.
    """

    import sys
    import os

    parent_dir_name = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    sys.path.append(parent_dir_name)