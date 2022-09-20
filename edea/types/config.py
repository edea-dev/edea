"""
Config for EDeA Pydantic dataclasses.

SPDX-License-Identifier: EUPL-1.2
"""
class PydanticConfig:
    # don't allow adding arbitrary extra fields that we didn't define
    extra = "forbid"
    # validate our defaults
    validate_all = True
