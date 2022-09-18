"""
Config and utilities for our Pydantic dataclasses.

SPDX-License-Identifier: EUPL-1.2
"""

from pydantic.dataclasses import dataclass

from edea.types.from_list_expr import from_list_expr


class PydanticConfig:
    # don't allow adding arbitrary extra fields that we didn't define
    extra = "forbid"
    # validate our defaults
    validate_all = True


# this is an odd one for things like "(power)" and "(fields_autoplaced)" which
# appear with the parens, hence we make a class for it for consistency. there
# might be a less ugly solution to this.
@dataclass(config=PydanticConfig)
class IsPresent:
    from_list_expr = from_list_expr
