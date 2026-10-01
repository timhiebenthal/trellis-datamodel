"""Decide which side of a relationship holds the foreign key.

The FK normally sits on the "many" side:
- one_to_many, one_to_zero_or_many, zero_or_one_to_many, zero_or_many_to_many:
  FK on the target.
- many_to_one, zero_or_many_to_one: FK on the source.
- one_to_one: FK on the source (FK holder -> referenced table, per spec).
- many_to_many: FK on the source.
- Unknown types fall back to FK on the target.

Note (existing behaviour, preserved as-is): many_to_many puts the FK on the
source while zero_or_many_to_many puts it on the target.
"""

from dataclasses import dataclass

_FK_ON_TARGET = frozenset(
    {
        "one_to_many",
        "one_to_zero_or_many",
        "zero_or_one_to_many",
        "zero_or_many_to_many",
    }
)
_FK_ON_SOURCE = frozenset(
    {"many_to_one", "many_to_many", "zero_or_many_to_one", "one_to_one"}
)


@dataclass(frozen=True)
class FkPlacement:
    fk_entity: str
    fk_field: str
    ref_entity: str
    ref_field: str


def place_foreign_key(
    rel_type: str,
    source_id: str,
    source_field: str,
    target_id: str,
    target_field: str,
) -> FkPlacement:
    """Return which entity/field holds the FK and which one it references."""
    if rel_type in _FK_ON_SOURCE:
        return FkPlacement(source_id, source_field, target_id, target_field)
    return FkPlacement(target_id, target_field, source_id, source_field)
