"""Classification contracts; group keys never authorize or constrain execution."""

from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints


def normalize_group_key(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


GroupKey = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=100),
    AfterValidator(normalize_group_key),
]
GroupFilter = Annotated[
    str | None,
    Field(max_length=100, description="Exact group key; omit/null for all groups, empty string for ungrouped work"),
]
