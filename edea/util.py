"""
Miscellaneous utility methods that don't fit anywhere else.

SPDX-License-Identifier: EUPL-1.2
"""

import re

# from https://stackoverflow.com/a/1176023
def to_snake_case(name):
    """
    Converts from CamelCase to snake_case.
    """
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    name = re.sub("__([A-Z])", r"_\1", name)
    name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower()


def get_all_subclasses(cls):
    all_subclasses = []

    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses
